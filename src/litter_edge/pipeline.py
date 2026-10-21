from __future__ import annotations

import time
from collections import Counter
from typing import Any, Protocol

from .schema import Detection, FrameOutcome
from .sorting import SeparationPolicy
from .tracking import ClassStabilizedIoUTracker, SessionCounter


class Detector(Protocol):
    backend_name: str

    def predict(self, frame_bgr: Any) -> list[Detection]:
        ...


class LitterPipeline:
    def __init__(
        self,
        detector: Detector,
        tracker: ClassStabilizedIoUTracker | None,
        separation_policy: SeparationPolicy | None = None,
    ) -> None:
        self.detector = detector
        self.tracker = tracker
        self.separation_policy = separation_policy
        self.counter = SessionCounter()

    def process(
        self,
        frame_bgr: Any,
        frame_index: int,
        timestamp_seconds: float | None = None,
    ) -> FrameOutcome:
        started = time.perf_counter()
        detections = self.detector.predict(frame_bgr)
        inference_ms = (time.perf_counter() - started) * 1000.0
        tracked = self.tracker.update(detections) if self.tracker else detections
        if self.separation_policy is not None:
            tracked = [
                self.separation_policy.apply(detection) for detection in tracked
            ]

        visible = Counter(detection.class_name for detection in tracked)
        confirmed_visible = Counter(
            detection.class_name for detection in tracked if detection.confirmed
        )
        unique, newly_confirmed = self.counter.update(tracked)
        return FrameOutcome(
            frame_index=frame_index,
            timestamp_seconds=timestamp_seconds,
            detections=tuple(tracked),
            visible_counts=dict(sorted(visible.items())),
            confirmed_visible_counts=dict(sorted(confirmed_visible.items())),
            unique_session_counts=unique,
            newly_confirmed_track_ids=newly_confirmed,
            inference_ms=inference_ms,
        )
