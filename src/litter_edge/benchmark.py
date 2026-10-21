from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path
from typing import Any, Iterator

from .adapters import create_detector
from .classes import load_class_names, load_class_prompts
from .common import environment_manifest, memory_snapshot, write_json
from .device import resolve_torch_device
from .runtime import _frames, _is_image_source, _safe_source_label, _source_value
from .settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark a model on frozen test media.")
    parser.add_argument("--config", default="config/project.yaml")
    parser.add_argument(
        "--backend",
        choices=("grounding_dino", "omdet_turbo", "rfdetr"),
    )
    parser.add_argument("--model")
    parser.add_argument("--class-names")
    parser.add_argument("--source", required=True)
    parser.add_argument("--device")
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument(
        "--image-repeats",
        type=int,
        default=1,
        help="Repeat a static image for stable latency evidence.",
    )
    parser.add_argument("--output", required=True)
    return parser


def _summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "p95": None, "min": None, "max": None}
    ordered = sorted(values)
    p95_index = min(len(ordered) - 1, max(0, round(0.95 * len(ordered) - 1)))
    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p95": ordered[p95_index],
        "min": min(values),
        "max": max(values),
    }


def _memory_evidence(
    samples: list[dict[str, Any]],
    preferred_incremental_gib: float,
    maximum_incremental_gib: float,
    minimum_remaining_gib: float,
) -> dict[str, Any]:
    available = [
        value
        for sample in samples
        if (value := sample["system_available_gib"]) is not None
    ]
    process_rss = [
        value
        for sample in samples
        if (value := sample["process_rss_gib"]) is not None
    ]
    baseline_available = samples[0]["system_available_gib"]
    baseline_rss = samples[0]["process_rss_gib"]
    minimum_available = min(available) if available else None
    maximum_rss = max(process_rss) if process_rss else None
    system_incremental = (
        max(0.0, baseline_available - minimum_available)
        if baseline_available is not None and minimum_available is not None
        else None
    )
    process_incremental = (
        max(0.0, maximum_rss - baseline_rss)
        if baseline_rss is not None and maximum_rss is not None
        else None
    )

    if system_incremental is None or minimum_available is None:
        gate_status = "not_evaluated"
        preferred_status = "not_evaluated"
    else:
        gate_status = (
            "pass"
            if system_incremental <= maximum_incremental_gib
            and minimum_available >= minimum_remaining_gib
            else "fail"
        )
        preferred_status = (
            "pass" if system_incremental <= preferred_incremental_gib else "exceeded"
        )

    return {
        "samples": samples,
        "minimum_system_available_gib": minimum_available,
        "maximum_process_rss_gib": maximum_rss,
        "observed_system_incremental_gib": system_incremental,
        "observed_process_incremental_gib": process_incremental,
        "preferred_incremental_gib": preferred_incremental_gib,
        "maximum_incremental_gib": maximum_incremental_gib,
        "minimum_remaining_available_gib": minimum_remaining_gib,
        "preferred_status": preferred_status,
        "hard_gate_status": gate_status,
        "note": (
            "System incremental memory is conservative and can include changes "
            "from co-resident services. Correlate it with tegrastats."
        ),
    }


def _accelerator_memory_snapshot(device: str) -> dict[str, Any]:
    empty = {
        "accelerator": None,
        "accelerator_allocated_gib": None,
        "accelerator_reserved_gib": None,
        "accelerator_peak_allocated_gib": None,
        "accelerator_peak_reserved_gib": None,
        "accelerator_free_gib": None,
        "accelerator_total_gib": None,
    }
    if not device.startswith("cuda"):
        return empty
    try:
        import torch

        if not torch.cuda.is_available():
            return empty
        gib = 1024**3
        free_bytes, total_bytes = torch.cuda.mem_get_info(device)
        return {
            "accelerator": torch.cuda.get_device_name(device),
            "accelerator_allocated_gib": torch.cuda.memory_allocated(device) / gib,
            "accelerator_reserved_gib": torch.cuda.memory_reserved(device) / gib,
            "accelerator_peak_allocated_gib": (
                torch.cuda.max_memory_allocated(device) / gib
            ),
            "accelerator_peak_reserved_gib": (
                torch.cuda.max_memory_reserved(device) / gib
            ),
            "accelerator_free_gib": free_bytes / gib,
            "accelerator_total_gib": total_bytes / gib,
        }
    except (ImportError, RuntimeError, AssertionError):
        return empty


def _accelerator_memory_evidence(samples: list[dict[str, Any]]) -> dict[str, Any]:
    accelerator_samples = [
        sample for sample in samples if sample.get("accelerator") is not None
    ]
    if not accelerator_samples:
        return {
            "status": "not_available",
            "device": None,
            "maximum_allocated_gib": None,
            "maximum_reserved_gib": None,
            "peak_allocated_gib": None,
            "peak_reserved_gib": None,
            "minimum_free_gib": None,
            "total_gib": None,
        }

    def maximum(key: str) -> float | None:
        values = [
            float(sample[key])
            for sample in accelerator_samples
            if sample.get(key) is not None
        ]
        return max(values) if values else None

    free_values = [
        float(sample["accelerator_free_gib"])
        for sample in accelerator_samples
        if sample.get("accelerator_free_gib") is not None
    ]
    total_values = [
        float(sample["accelerator_total_gib"])
        for sample in accelerator_samples
        if sample.get("accelerator_total_gib") is not None
    ]
    return {
        "status": "measured",
        "device": accelerator_samples[-1]["accelerator"],
        "maximum_allocated_gib": maximum("accelerator_allocated_gib"),
        "maximum_reserved_gib": maximum("accelerator_reserved_gib"),
        "peak_allocated_gib": maximum("accelerator_peak_allocated_gib"),
        "peak_reserved_gib": maximum("accelerator_peak_reserved_gib"),
        "minimum_free_gib": min(free_values) if free_values else None,
        "total_gib": max(total_values) if total_values else None,
    }


def _benchmark_frames(
    source: str | int,
    image_repeats: int,
) -> Iterator[tuple[Any, float | None, float]]:
    if not _is_image_source(source):
        yield from _frames(source)
        return
    frame, timestamp, source_fps = next(_frames(source))
    for _ in range(image_repeats):
        yield frame, timestamp, source_fps


def main() -> None:
    args = build_parser().parse_args()
    if args.warmup < 0:
        raise ValueError("warmup cannot be negative.")
    if args.max_samples < 0:
        raise ValueError("max_samples cannot be negative.")
    if args.image_repeats <= 0:
        raise ValueError("image_repeats must be positive.")
    settings = load_settings(args.config)
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "Install the 'runtime' optional dependency before benchmarking."
        ) from exc

    backend = args.backend or settings.backend
    model_reference = args.model or settings.model
    class_names = args.class_names or str(settings.class_names_file)
    device = resolve_torch_device(args.device or str(settings.device))
    memory_samples = [
        {
            "phase": "before_model",
            **memory_snapshot(),
            **_accelerator_memory_snapshot(device),
        }
    ]
    loaded_class_names = load_class_names(class_names)
    detector = create_detector(
        backend=backend,
        model=model_reference,
        class_names=loaded_class_names,
        confidence=settings.confidence,
        device=device,
        optimize=True,
        class_prompts=load_class_prompts(
            class_names,
            loaded_class_names,
            profile=backend,
        ),
        iou=settings.iou,
        max_detections=settings.max_detections,
    )
    memory_samples.append(
        {
            "phase": "after_model_load",
            **memory_snapshot(),
            **_accelerator_memory_snapshot(device),
        }
    )
    warmup_frame = np.zeros(
        (settings.image_size, settings.image_size, 3),
        dtype=np.uint8,
    )
    for _ in range(args.warmup):
        detector.predict(warmup_frame)
    memory_samples.append(
        {
            "phase": "after_warmup",
            **memory_snapshot(),
            **_accelerator_memory_snapshot(device),
        }
    )
    if device.startswith("cuda"):
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats(device)
        except (ImportError, RuntimeError, AssertionError):
            pass

    source = _source_value(args.source)
    source_label = _safe_source_label(source)
    inference_ms: list[float] = []
    end_to_end_ms: list[float] = []
    detections: list[int] = []
    started = time.perf_counter()
    for index, (frame, _, _) in enumerate(
        _benchmark_frames(source, args.image_repeats), start=1
    ):
        frame_started = time.perf_counter()
        result = detector.predict(frame)
        elapsed_ms = (time.perf_counter() - frame_started) * 1000.0
        inference_ms.append(elapsed_ms)
        end_to_end_ms.append(elapsed_ms)
        detections.append(len(result))
        memory_samples.append(
            {
                "phase": f"sample_{index}",
                **memory_snapshot(),
                **_accelerator_memory_snapshot(device),
            }
        )
        if args.max_samples and index >= args.max_samples:
            break
    wall_seconds = time.perf_counter() - started
    if not inference_ms:
        raise RuntimeError(f"No frames were processed from: {source_label}")
    memory_samples.append(
        {
            "phase": "after_benchmark",
            **memory_snapshot(),
            **_accelerator_memory_snapshot(device),
        }
    )

    payload: dict[str, Any] = environment_manifest(Path.cwd())
    payload.update(
        {
            "operation": "benchmark",
            "backend": backend,
            "model": model_reference,
            "source": source_label,
            "device": device,
            "image_size": settings.image_size,
            "warmup": args.warmup,
            "image_repeats": args.image_repeats if _is_image_source(source) else None,
            "samples": len(inference_ms),
            "wall_seconds": wall_seconds,
            "observed_throughput_fps": len(inference_ms) / wall_seconds if wall_seconds else None,
            "inference_ms": _summary(inference_ms),
            "detector_call_ms": _summary(end_to_end_ms),
            "detections_per_sample": _summary([float(value) for value in detections]),
            "memory": _memory_evidence(
                memory_samples,
                settings.preferred_incremental_memory_gb,
                settings.maximum_incremental_memory_gb,
                settings.minimum_remaining_available_memory_gb,
            ),
            "accelerator_memory": _accelerator_memory_evidence(memory_samples),
            "note": (
                "Add tegrastats power, memory, temperature, clocks, and any "
                "co-resident service impact for the same run."
            ),
        }
    )
    output = write_json(args.output, payload)
    print(f"Benchmark evidence: {output}")


if __name__ == "__main__":
    main()

