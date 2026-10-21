from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any


@dataclass(frozen=True)
class Detection:
    """Hardware- and framework-neutral object detection."""

    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int
    class_name: str
    track_id: int | None = None
    confirmed: bool = False
    separation_destination: str | None = None
    review_required: bool = False

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return self.x1, self.y1, self.x2, self.y2

    def with_tracking(
        self,
        track_id: int,
        class_id: int,
        class_name: str,
        confirmed: bool,
    ) -> "Detection":
        return replace(
            self,
            track_id=track_id,
            class_id=class_id,
            class_name=class_name,
            confirmed=confirmed,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["bbox_xyxy"] = [
            payload.pop("x1"),
            payload.pop("y1"),
            payload.pop("x2"),
            payload.pop("y2"),
        ]
        return payload


@dataclass(frozen=True)
class FrameOutcome:
    frame_index: int
    timestamp_seconds: float | None
    detections: tuple[Detection, ...]
    visible_counts: dict[str, int]
    confirmed_visible_counts: dict[str, int]
    unique_session_counts: dict[str, int]
    newly_confirmed_track_ids: tuple[int, ...]
    inference_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "timestamp_seconds": self.timestamp_seconds,
            "inference_ms": self.inference_ms,
            "visible_counts": self.visible_counts,
            "confirmed_visible_counts": self.confirmed_visible_counts,
            "unique_session_counts": self.unique_session_counts,
            "newly_confirmed_track_ids": list(self.newly_confirmed_track_ids),
            "detections": [detection.to_dict() for detection in self.detections],
        }
