from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .schema import Detection


def intersection_over_union(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    x1 = max(left[0], right[0])
    y1 = max(left[1], right[1])
    x2 = min(left[2], right[2])
    y2 = min(left[3], right[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    right_area = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


@dataclass
class _Track:
    track_id: int
    bbox: tuple[float, float, float, float]
    confidence: float
    missed_frames: int = 0
    hits: int = 1
    class_votes: Counter[tuple[int, str]] = field(default_factory=Counter)

    @property
    def stable_class(self) -> tuple[int, str]:
        return self.class_votes.most_common(1)[0][0]


class ClassStabilizedIoUTracker:
    """Small dependency-free tracker suited to stationary-camera litter scenes."""

    def __init__(
        self,
        iou_threshold: float = 0.3,
        max_missed_frames: int = 30,
        min_confirmed_hits: int = 2,
        class_mismatch_penalty: float = 0.75,
    ) -> None:
        if not 0.0 <= iou_threshold <= 1.0:
            raise ValueError("iou_threshold must be between 0 and 1.")
        if max_missed_frames < 0:
            raise ValueError("max_missed_frames cannot be negative.")
        if min_confirmed_hits <= 0:
            raise ValueError("min_confirmed_hits must be positive.")
        if not 0.0 < class_mismatch_penalty <= 1.0:
            raise ValueError("class_mismatch_penalty must be in (0, 1].")
        self.iou_threshold = iou_threshold
        self.max_missed_frames = max_missed_frames
        self.min_confirmed_hits = min_confirmed_hits
        self.class_mismatch_penalty = class_mismatch_penalty
        self._tracks: dict[int, _Track] = {}
        self._next_track_id = 1

    def update(self, detections: list[Detection]) -> list[Detection]:
        for track in self._tracks.values():
            track.missed_frames += 1

        candidates: list[tuple[float, int, int]] = []
        for detection_index, detection in enumerate(detections):
            for track_id, track in self._tracks.items():
                overlap = intersection_over_union(detection.bbox, track.bbox)
                if overlap < self.iou_threshold:
                    continue
                stable_id, _ = track.stable_class
                score = (
                    overlap
                    if stable_id == detection.class_id
                    else overlap * self.class_mismatch_penalty
                )
                candidates.append((score, track_id, detection_index))

        matched_tracks: set[int] = set()
        matched_detections: set[int] = set()
        assignments: dict[int, int] = {}
        for _, track_id, detection_index in sorted(candidates, reverse=True):
            if track_id in matched_tracks or detection_index in matched_detections:
                continue
            matched_tracks.add(track_id)
            matched_detections.add(detection_index)
            assignments[detection_index] = track_id

        output: list[Detection] = []
        for detection_index, detection in enumerate(detections):
            track_id = assignments.get(detection_index)
            if track_id is None:
                track_id = self._next_track_id
                self._next_track_id += 1
                track = _Track(
                    track_id=track_id,
                    bbox=detection.bbox,
                    confidence=detection.confidence,
                )
                track.class_votes[(detection.class_id, detection.class_name)] += 1
                self._tracks[track_id] = track
            else:
                track = self._tracks[track_id]
                track.bbox = detection.bbox
                track.confidence = detection.confidence
                track.missed_frames = 0
                track.hits += 1
                track.class_votes[(detection.class_id, detection.class_name)] += 1

            stable_id, stable_name = track.stable_class
            output.append(
                detection.with_tracking(
                    track_id=track_id,
                    class_id=stable_id,
                    class_name=stable_name,
                    confirmed=track.hits >= self.min_confirmed_hits,
                )
            )

        expired = [
            track_id
            for track_id, track in self._tracks.items()
            if track.missed_frames > self.max_missed_frames
        ]
        for track_id in expired:
            del self._tracks[track_id]
        return output


class SessionCounter:
    """Counts confirmed track IDs once while allowing stabilized class updates."""

    def __init__(self) -> None:
        self._track_classes: dict[int, str] = {}

    def update(self, detections: list[Detection]) -> tuple[dict[str, int], tuple[int, ...]]:
        newly_confirmed: list[int] = []
        for detection in detections:
            if not detection.confirmed or detection.track_id is None:
                continue
            if detection.track_id not in self._track_classes:
                newly_confirmed.append(detection.track_id)
            self._track_classes[detection.track_id] = detection.class_name
        counts = Counter(self._track_classes.values())
        return dict(sorted(counts.items())), tuple(sorted(newly_confirmed))
