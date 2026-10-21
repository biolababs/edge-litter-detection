from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit

from .adapters import create_detector
from .classes import load_class_names, load_class_prompts
from .common import environment_manifest, utc_now, write_json
from .metrics import summarize_samples
from .pipeline import LitterPipeline
from .schema import FrameOutcome
from .settings import (
    ProjectSettings,
    load_settings,
    normalize_backend,
    resolve_model_reference,
)
from .sorting import load_separation_policy
from .storage import SQLiteObservationStore
from .tracking import ClassStabilizedIoUTracker


IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Detect, classify, track, and count litter in an image, video, "
            "camera, or stream."
        )
    )
    parser.add_argument("--config", default="config/project.yaml")
    parser.add_argument(
        "--backend",
        choices=("grounding_dino", "omdet_turbo", "rfdetr"),
    )
    parser.add_argument("--model")
    parser.add_argument("--class-names")
    parser.add_argument("--separation-config")
    parser.add_argument("--source", required=True, help="Image/video path, camera index, or URL")
    parser.add_argument("--device", default=None, help="auto, cpu, cuda, cuda:0, etc.")
    parser.add_argument("--confidence", type=float)
    parser.add_argument("--track", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--optimize", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--annotated-output")
    parser.add_argument(
        "--events-output",
        default="reports/generated/latest_events.jsonl",
        help="Streaming JSON Lines evidence.",
    )
    parser.add_argument(
        "--output",
        default="reports/generated/latest_summary.json",
        help="End-of-run JSON summary.",
    )
    parser.add_argument(
        "--database",
        default=os.environ.get("LITTER_DATABASE"),
        help="SQLite observation database.",
    )
    parser.add_argument(
        "--no-database",
        action="store_true",
        help="Disable SQLite persistence for this run.",
    )
    parser.add_argument("--database-flush-frames", type=int)
    parser.add_argument(
        "--persist-detections",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Store every detection row in SQLite; counts are always stored.",
    )
    parser.add_argument(
        "--edge-device-id",
        default=os.environ.get("LITTER_EDGE_DEVICE_ID", "edge-node"),
    )
    parser.add_argument("--vehicle-id", default=os.environ.get("LITTER_VEHICLE_ID"))
    parser.add_argument("--route-id", default=os.environ.get("LITTER_ROUTE_ID"))
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument(
        "--profile-timing",
        action="store_true",
        help=(
            "Synchronize supported accelerators and report capture, detector, "
            "tracking, persistence, and rendering latency components."
        ),
    )
    parser.add_argument(
        "--warmup-calls",
        type=int,
        default=0,
        help=(
            "Run this many zero-frame detector calls before opening the source "
            "and starting measured output."
        ),
    )
    return parser


def _source_value(value: str) -> str | int:
    return int(value) if value.isdigit() else value


def _safe_source_label(source: str | int) -> str:
    if isinstance(source, int):
        return str(source)
    if "://" not in source:
        return source
    parsed = urlsplit(source)
    hostname = parsed.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    authority = f"{hostname}:{parsed.port}" if parsed.port else hostname
    return f"{parsed.scheme}://{authority}{parsed.path}"


def _is_image_source(source: str | int) -> bool:
    return isinstance(source, str) and Path(source).suffix.lower() in IMAGE_SUFFIXES


def _make_tracker(
    settings: ProjectSettings,
    enabled: bool,
    single_image: bool,
) -> ClassStabilizedIoUTracker | None:
    if not enabled:
        return None
    return ClassStabilizedIoUTracker(
        iou_threshold=settings.tracking_iou_threshold,
        max_missed_frames=settings.tracking_max_missed_frames,
        min_confirmed_hits=1 if single_image else settings.tracking_min_confirmed_hits,
        class_mismatch_penalty=settings.tracking_class_mismatch_penalty,
    )


def _frames(source: str | int) -> Iterator[tuple[Any, float | None, float]]:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "OpenCV is required for media input. Install the 'runtime' optional "
            "dependency."
        ) from exc

    if _is_image_source(source):
        frame = cv2.imread(str(source))
        if frame is None:
            raise FileNotFoundError(f"Unable to read image: {source}")
        yield frame, None, 0.0
        return

    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open media source: {_safe_source_label(source)}")
    source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            timestamp = float(capture.get(cv2.CAP_PROP_POS_MSEC)) / 1000.0
            yield frame, timestamp, source_fps
    finally:
        capture.release()


def _annotate(frame: Any, outcome: FrameOutcome) -> Any:
    import cv2

    annotated = frame.copy()
    for detection in outcome.detections:
        x1, y1, x2, y2 = (round(value) for value in detection.bbox)
        if detection.review_required:
            color = (0, 0, 255)
        else:
            color = (40, 180, 40) if detection.confirmed else (0, 165, 255)
        label = f"{detection.class_name} {detection.confidence:.2f}"
        if detection.track_id is not None:
            label += f" id={detection.track_id}"
        if detection.separation_destination:
            label += f" -> {detection.separation_destination}"
        if detection.review_required:
            label += " REVIEW"
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            annotated,
            label,
            (x1, max(20, y1 - 7)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
            cv2.LINE_AA,
        )
    counts = ", ".join(
        f"{name}:{count}" for name, count in outcome.unique_session_counts.items()
    )
    cv2.putText(
        annotated,
        f"unique session count: {counts or 'none'}",
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    destination_counts = Counter(
        detection.separation_destination
        for detection in outcome.detections
        if detection.separation_destination
    )
    destinations = ", ".join(
        f"{name}:{count}" for name, count in sorted(destination_counts.items())
    )
    cv2.putText(
        annotated,
        f"visible separation: {destinations or 'none'}",
        (12, 54),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    review_count = sum(
        1 for detection in outcome.detections if detection.review_required
    )
    if review_count:
        cv2.putText(
            annotated,
            f"human review required: {review_count}",
            (12, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )
    return annotated


def _timing_profile(
    samples: dict[str, list[float]],
    wall_seconds: float,
) -> dict[str, Any]:
    components = {
        name: {
            **summarize_samples(values),
            "total_ms": sum(values),
        }
        for name, values in sorted(samples.items())
    }
    detector_phases = {
        "detector_preprocess",
        "model_forward",
        "detector_postprocess",
    }
    exclusive_names = {
        "source_open_and_first_decode",
        "capture_or_decode",
        "tracking_policy_and_counting",
        "event_serialization_and_write",
        "sqlite_persistence",
        "annotation_render_and_output",
    }
    if detector_phases.issubset(samples):
        exclusive_names.update(detector_phases)
    else:
        exclusive_names.add("detector_call")
    wall_ms = wall_seconds * 1000.0
    shares = {
        name: sum(samples[name]) / wall_ms * 100.0
        for name in sorted(exclusive_names)
        if name in samples and wall_ms > 0
    }
    accounted = sum(shares.values())
    return {
        "enabled": True,
        "accelerator_synchronization": (
            "enabled when supported by the selected detector"
        ),
        "components_ms": components,
        "exclusive_wall_share_percent": {
            **shares,
            "unattributed_loop_and_finalization": max(0.0, 100.0 - accounted),
        },
        "interpretation": (
            "detector phases are contained in detector_call, which is contained "
            "in pipeline_total. exclusive_wall_share_percent uses detector "
            "phases when available and does not also count their inclusive "
            "parents. The first source open/decode is reported separately."
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    profile_timing = bool(getattr(args, "profile_timing", False))
    warmup_calls = int(getattr(args, "warmup_calls", 0))
    if warmup_calls < 0:
        raise ValueError("warmup-calls cannot be negative.")
    settings = load_settings(args.config)
    backend = normalize_backend(args.backend or settings.backend)
    model_reference = resolve_model_reference(
        backend,
        explicit_model=args.model,
        configured_backend=settings.backend,
        configured_model=settings.model,
    )
    class_names_path = args.class_names or str(settings.class_names_file)
    class_names = load_class_names(class_names_path)
    class_prompts = load_class_prompts(
        class_names_path,
        class_names,
        profile=backend,
    )
    separation_config = (
        args.separation_config or str(settings.separation_policy_file)
    )
    separation_policy = load_separation_policy(
        separation_config,
        class_names=class_names,
    )
    confidence = settings.confidence if args.confidence is None else args.confidence
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1.")
    if args.max_frames < 0:
        raise ValueError("max_frames cannot be negative.")
    device = args.device or str(settings.device)
    tracking_enabled = (
        settings.tracking_enabled if args.track is None else bool(args.track)
    )
    source = _source_value(args.source)
    source_label = _safe_source_label(source)
    single_image = _is_image_source(source)
    detector = create_detector(
        backend=backend,
        model=model_reference,
        class_names=class_names,
        confidence=confidence,
        device=device,
        optimize=args.optimize,
        class_prompts=class_prompts,
        iou=settings.iou,
        max_detections=settings.max_detections,
    )
    if profile_timing:
        enable_profiling = getattr(detector, "enable_profiling", None)
        if callable(enable_profiling):
            enable_profiling()
    pipeline = LitterPipeline(
        detector=detector,
        tracker=_make_tracker(settings, tracking_enabled, single_image),
        separation_policy=separation_policy,
    )
    if warmup_calls:
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "Install a runtime optional dependency before using warm-up calls."
            ) from exc
        warmup_frame = np.zeros(
            (settings.image_size, settings.image_size, 3),
            dtype=np.uint8,
        )
        for _ in range(warmup_calls):
            detector.predict(warmup_frame)

    events_path = Path(args.events_output)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    annotated_path = Path(args.annotated_output) if args.annotated_output else None
    if annotated_path:
        annotated_path.parent.mkdir(parents=True, exist_ok=True)

    writer = None
    run_id = str(uuid.uuid4())
    edge_device_id = str(args.edge_device_id).strip()
    if not edge_device_id:
        raise ValueError("edge-device-id cannot be empty.")
    vehicle_id = str(args.vehicle_id).strip() if args.vehicle_id else None
    route_id = str(args.route_id).strip() if args.route_id else None
    database_path = Path(args.database or settings.storage_database)
    database_flush_frames = (
        args.database_flush_frames
        if args.database_flush_frames is not None
        else settings.storage_flush_frames
    )
    if database_flush_frames <= 0:
        raise ValueError("database-flush-frames must be positive.")
    persist_detections = (
        settings.storage_persist_detections
        if args.persist_detections is None
        else bool(args.persist_detections)
    )
    observation_store = (
        None
        if args.no_database
        else SQLiteObservationStore(
            database_path,
            flush_frames=database_flush_frames,
            persist_detections=persist_detections,
        )
    )
    frame_count = 0
    peak_visible: Counter[str] = Counter()
    final_unique: dict[str, int] = {}
    inference_times: list[float] = []
    timing_samples: dict[str, list[float]] = {}

    def record_timing(name: str, elapsed_ms: float) -> None:
        if profile_timing:
            timing_samples.setdefault(name, []).append(elapsed_ms)

    interrupted = False
    started_at = utc_now()
    started = time.perf_counter()
    if observation_store is not None:
        observation_store.start_run(
            run_id=run_id,
            started_at=started_at,
            source=source_label,
            backend=backend,
            model=model_reference,
            compute_device=device,
            edge_device_id=edge_device_id,
            vehicle_id=vehicle_id,
            route_id=route_id,
            events_output=str(events_path),
            summary_output=str(args.output),
            annotated_output=str(annotated_path) if annotated_path else None,
        )
    try:
        with events_path.open("w", encoding="utf-8") as events:
            frame_iterator = iter(_frames(source))
            while True:
                capture_started = time.perf_counter()
                try:
                    frame, timestamp, source_fps = next(frame_iterator)
                except StopIteration:
                    break
                record_timing(
                    (
                        "source_open_and_first_decode"
                        if frame_count == 0
                        else "capture_or_decode"
                    ),
                    (time.perf_counter() - capture_started) * 1000.0,
                )
                frame_count += 1
                pipeline_started = time.perf_counter()
                outcome = pipeline.process(frame, frame_count, timestamp)
                pipeline_ms = (time.perf_counter() - pipeline_started) * 1000.0
                record_timing("pipeline_total", pipeline_ms)
                for name, elapsed_ms in pipeline.last_timing_ms.items():
                    record_timing(name, elapsed_ms)
                detector_timing = getattr(detector, "last_timing_ms", {})
                if profile_timing and isinstance(detector_timing, dict):
                    for name, elapsed_ms in detector_timing.items():
                        record_timing(name, float(elapsed_ms))
                inference_times.append(outcome.inference_ms)
                final_unique = outcome.unique_session_counts
                for name, count in outcome.visible_counts.items():
                    peak_visible[name] = max(peak_visible[name], count)
                event_started = time.perf_counter()
                event = outcome.to_dict()
                event["run_id"] = run_id
                event["source"] = source_label
                event["edge_device_id"] = edge_device_id
                event["vehicle_id"] = vehicle_id
                event["route_id"] = route_id
                events.write(json.dumps(event, sort_keys=True) + "\n")
                record_timing(
                    "event_serialization_and_write",
                    (time.perf_counter() - event_started) * 1000.0,
                )
                if observation_store is not None:
                    database_started = time.perf_counter()
                    observation_store.record_frame(run_id, outcome)
                    record_timing(
                        "sqlite_persistence",
                        (time.perf_counter() - database_started) * 1000.0,
                    )
                if frame_count % 30 == 0:
                    events.flush()

                if annotated_path or args.display:
                    import cv2

                    rendering_started = time.perf_counter()
                    annotated = _annotate(frame, outcome)
                    if annotated_path:
                        if single_image:
                            if not cv2.imwrite(str(annotated_path), annotated):
                                raise RuntimeError(
                                    f"Unable to write image: {annotated_path}"
                                )
                        else:
                            if writer is None:
                                height, width = annotated.shape[:2]
                                fps = source_fps if source_fps > 0 else 15.0
                                writer = cv2.VideoWriter(
                                    str(annotated_path),
                                    cv2.VideoWriter_fourcc(*"mp4v"),
                                    fps,
                                    (width, height),
                                )
                                if not writer.isOpened():
                                    raise RuntimeError(
                                        f"Unable to create video: {annotated_path}"
                                    )
                            writer.write(annotated)
                    if args.display:
                        cv2.imshow("litter-edge", annotated)
                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            break
                    record_timing(
                        "annotation_render_and_output",
                        (time.perf_counter() - rendering_started) * 1000.0,
                    )
                if args.max_frames and frame_count >= args.max_frames:
                    break
    except KeyboardInterrupt:
        interrupted = True
    except Exception as exc:
        if observation_store is not None:
            observation_store.fail_run(run_id, str(exc))
            observation_store.close()
            observation_store = None
        raise
    finally:
        if writer is not None:
            writer.release()
        if args.display:
            import cv2

            cv2.destroyAllWindows()

    wall_seconds = time.perf_counter() - started
    if frame_count == 0:
        if observation_store is not None:
            observation_store.fail_run(run_id, "No frames were processed.")
            observation_store.close()
        raise RuntimeError(f"No frames were processed from: {source_label}")
    completed_at = utc_now()
    source_to_result_fps = frame_count / wall_seconds if wall_seconds > 0 else None
    mean_detector_call_ms = (
        sum(inference_times) / len(inference_times) if inference_times else None
    )
    summary = environment_manifest(Path.cwd())
    summary.update(
        {
            "operation": "detect_classify_count",
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "backend": backend,
            "model": model_reference,
            "class_names": class_names_path,
            "separation_config": separation_config,
            "source": source_label,
            "device": device,
            "edge_device_id": edge_device_id,
            "vehicle_id": vehicle_id,
            "route_id": route_id,
            "tracking_enabled": tracking_enabled,
            "warmup_calls": warmup_calls,
            "count_semantics": {
                "visible_counts": "detections present in the current frame",
                "unique_session_counts": (
                    "confirmed track IDs counted once per run; not a lifetime "
                    "site inventory"
                ),
                "collection_status": (
                    "observed litter only; collection requires an independent "
                    "human or equipment confirmation"
                ),
            },
            "frames": frame_count,
            "interrupted": interrupted,
            "wall_seconds": wall_seconds,
            "source_to_result_fps": source_to_result_fps,
            "mean_detector_call_ms": mean_detector_call_ms,
            "timing_profile": (
                _timing_profile(timing_samples, wall_seconds)
                if profile_timing
                else {"enabled": False}
            ),
            "peak_visible_counts": dict(sorted(peak_visible.items())),
            "unique_session_counts": final_unique,
            "events_output": str(events_path),
            "annotated_output": str(annotated_path) if annotated_path else None,
            "database": str(database_path) if observation_store is not None else None,
            "persist_detections": (
                persist_detections if observation_store is not None else False
            ),
        }
    )
    try:
        output = write_json(args.output, summary)
        if observation_store is not None:
            observation_store.finish_run(
                run_id=run_id,
                completed_at=completed_at,
                status="interrupted" if interrupted else "completed",
                frames=frame_count,
                wall_seconds=wall_seconds,
                source_to_result_fps=source_to_result_fps,
                mean_detector_call_ms=mean_detector_call_ms,
                peak_visible_counts=dict(peak_visible),
                unique_detected_counts=final_unique,
            )
    except Exception as exc:
        if observation_store is not None:
            observation_store.fail_run(run_id, str(exc))
        raise
    finally:
        if observation_store is not None:
            observation_store.close()
    print(json.dumps({"summary": str(output), **final_unique}, sort_keys=True))
    return summary


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
