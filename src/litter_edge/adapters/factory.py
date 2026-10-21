from __future__ import annotations

from ..device import resolve_torch_device
from ..pipeline import Detector


def create_detector(
    backend: str,
    model: str,
    class_names: dict[int, str],
    confidence: float,
    device: str,
    optimize: bool = True,
    class_prompts: dict[int, str] | None = None,
    iou: float = 0.6,
    max_detections: int = 100,
) -> Detector:
    normalized = backend.strip().lower()
    resolved_device = resolve_torch_device(device)
    if normalized in {"grounding_dino", "grounding-dino"}:
        from .grounding_dino import GroundingDINODetector

        return GroundingDINODetector(
            model_reference=model,
            class_names=class_names,
            class_prompts=class_prompts,
            confidence=confidence,
            device=resolved_device,
            optimize=optimize,
            nms_iou=iou,
            max_detections=max_detections,
        )
    if normalized in {"omdet_turbo", "omdet-turbo", "omdet"}:
        from .omdet_turbo import OmDetTurboDetector

        return OmDetTurboDetector(
            model_reference=model,
            class_names=class_names,
            class_prompts=class_prompts,
            confidence=confidence,
            device=resolved_device,
            optimize=optimize,
            nms_iou=iou,
            max_detections=max_detections,
        )
    if normalized == "rfdetr":
        from .rfdetr import RFDETRDetector

        return RFDETRDetector(
            model_reference=model,
            class_names=class_names,
            confidence=confidence,
            device=resolved_device,
            optimize=optimize,
        )
    raise ValueError(
        f"Unsupported backend '{backend}'. Expected 'grounding_dino', "
        "'omdet_turbo', or 'rfdetr'."
    )
