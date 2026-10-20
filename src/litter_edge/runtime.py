from __future__ import annotations

import argparse
import json
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit

from .adapters import create_detector
from .classes import load_class_names
from .common import environment_manifest, utc_now, write_json
from .pipeline import LitterPipeline
from .schema import FrameOutcome
from .settings import ProjectSettings, load_settings
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
    parser.add_argument("--backend", choices=("rfdetr",))
    parser.add_argument("--model")
    parser.add_argument("--class-names")
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
    parser.add_argument("--max-frames", type=int, default=0)
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
        color = (40, 180, 40) if detection.confirmed else (0, 165, 255)
        label = f"{detection.class_name} {detection.confidence:.2f}"
        if detection.track_id is not None:
            label += f" id={detection.track_id}"
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
    return annotated


def run(args: argparse.Namespace) -> dict[str, Any]:
    settings = load_settings(args.config)
    backend = args.backend or settings.backend
    model_reference = args.model or settings.model
    class_names_path = args.class_names or str(settings.class_names_file)
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
        class_names=load_class_names(class_names_path),
        confidence=confidence,
        device=device,
        optimize=args.optimize,
    )
    pipeline = LitterPipeline(
        detector=detector,
        tracker=_make_tracker(settings, tracking_enabled, single_image),
    )

    events_path = Path(args.events_output)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    annotated_path = Path(args.annotated_output) if args.annotated_output else None
    if annotated_path:
        annotated_path.parent.mkdir(parents=True, exist_ok=True)

    writer = None
    run_id = str(uuid.uuid4())
    frame_count = 0
    peak_visible: Counter[str] = Counter()
    final_unique: dict[str, int] = {}
    inference_times: list[float] = []
    interrupted = False
    started_at = utc_now()
    started = time.perf_counter()
    try:
        with events_path.open("w", encoding="utf-8") as events:
            for frame, timestamp, source_fps in _frames(source):
                frame_count += 1
                outcome = pipeline.process(frame, frame_count, timestamp)
                inference_times.append(outcome.inference_ms)
                final_unique = outcome.unique_session_counts
                for name, count in outcome.visible_counts.items():
                    peak_visible[name] = max(peak_visible[name], count)
                event = outcome.to_dict()
                event["run_id"] = run_id
                event["source"] = source_label
                events.write(json.dumps(event, sort_keys=True) + "\n")
                if frame_count % 30 == 0:
                    events.flush()

                if annotated_path or args.display:
                    import cv2

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
                if args.max_frames and frame_count >= args.max_frames:
                    break
    except KeyboardInterrupt:
        interrupted = True
    finally:
        if writer is not None:
            writer.release()
        if args.display:
            import cv2

            cv2.destroyAllWindows()

    wall_seconds = time.perf_counter() - started
    if frame_count == 0:
        raise RuntimeError(f"No frames were processed from: {source_label}")
    summary = environment_manifest(Path.cwd())
    summary.update(
        {
            "operation": "detect_classify_count",
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": utc_now(),
            "backend": backend,
            "model": model_reference,
            "class_names": class_names_path,
            "source": source_label,
            "device": device,
            "tracking_enabled": tracking_enabled,
            "count_semantics": {
                "visible_counts": "detections present in the current frame",
                "unique_session_counts": (
                    "confirmed track IDs counted once per run; not a lifetime "
                    "site inventory"
                ),
            },
            "frames": frame_count,
            "interrupted": interrupted,
            "wall_seconds": wall_seconds,
            "source_to_result_fps": (
                frame_count / wall_seconds if wall_seconds > 0 else None
            ),
            "mean_detector_call_ms": (
                sum(inference_times) / len(inference_times)
                if inference_times
                else None
            ),
            "peak_visible_counts": dict(sorted(peak_visible.items())),
            "unique_session_counts": final_unique,
            "events_output": str(events_path),
            "annotated_output": str(annotated_path) if annotated_path else None,
        }
    )
    output = write_json(args.output, summary)
    print(json.dumps({"summary": str(output), **final_unique}, sort_keys=True))
    return summary


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
