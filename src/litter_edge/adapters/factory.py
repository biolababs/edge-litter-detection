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
) -> Detector:
    normalized = backend.strip().lower()
    resolved_device = resolve_torch_device(device)
    if normalized == "rfdetr":
        from .rfdetr import RFDETRDetector

        return RFDETRDetector(
            model_reference=model,
            class_names=class_names,
            confidence=confidence,
            device=resolved_device,
            optimize=optimize,
        )
    raise ValueError(f"Unsupported backend '{backend}'. Expected 'rfdetr'.")
