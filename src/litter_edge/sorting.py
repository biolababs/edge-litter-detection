from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from .schema import Detection


@dataclass(frozen=True)
class SeparationPolicy:
    destinations: dict[str, str]
    review_below_confidence: float
    always_review: frozenset[str]

    def apply(self, detection: Detection) -> Detection:
        destination = self.destinations.get(detection.class_name, "manual_sort")
        review_required = (
            detection.confidence < self.review_below_confidence
            or detection.class_name in self.always_review
            or detection.class_name not in self.destinations
        )
        return replace(
            detection,
            separation_destination=destination,
            review_required=review_required,
        )


def load_separation_policy(
    path: str | Path,
    class_names: dict[int, str] | None = None,
) -> SeparationPolicy:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload: dict[str, Any] = yaml.safe_load(handle) or {}

    if payload.get("schema_version") not in {"1.0", "2.0"}:
        raise ValueError("Separation policy schema_version must be '1.0' or '2.0'.")
    destinations = payload.get("destinations")
    if not isinstance(destinations, dict) or not destinations:
        raise ValueError("Separation policy requires a destinations mapping.")
    normalized = {
        str(class_name): str(destination)
        for class_name, destination in destinations.items()
        if str(class_name).strip() and str(destination).strip()
    }
    if len(normalized) != len(destinations):
        raise ValueError("Separation class and destination names cannot be empty.")

    if class_names is not None:
        configured_classes = set(class_names.values())
        missing = configured_classes - set(normalized)
        extra = set(normalized) - configured_classes
        if missing or extra:
            raise ValueError(
                "Separation destinations must match the litter class schema; "
                f"missing={sorted(missing)}, extra={sorted(extra)}."
            )

    review = payload.get("review") or {}
    threshold = float(review.get("confidence_below", 0.55))
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("review.confidence_below must be between 0 and 1.")
    always_review = frozenset(str(value) for value in review.get("always_review", []))
    unknown_review_classes = always_review - set(normalized)
    if unknown_review_classes:
        raise ValueError(
            "review.always_review contains unknown classes: "
            f"{sorted(unknown_review_classes)}."
        )

    return SeparationPolicy(
        destinations=normalized,
        review_below_confidence=threshold,
        always_review=always_review,
    )
