from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from .classes import load_class_names
from .common import utc_now, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate visible and unique-session litter counts from runtime "
            "JSONL evidence."
        )
    )
    parser.add_argument("--events", required=True)
    parser.add_argument("--ground-truth", required=True)
    parser.add_argument("--class-names", default="config/classes.yaml")
    parser.add_argument(
        "--output",
        default="reports/generated/count_accuracy.json",
    )
    return parser


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in: {path}")
    return payload


def _load_events(path: Path) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {path}: {exc}"
                ) from exc
            if not isinstance(row, dict):
                raise ValueError(
                    f"Expected an object on line {line_number} of {path}."
                )
            frame_index = row.get("frame_index")
            if not isinstance(frame_index, int) or frame_index < 1:
                raise ValueError(
                    f"Invalid frame_index on line {line_number} of {path}."
                )
            if frame_index in rows:
                raise ValueError(f"Duplicate frame_index {frame_index} in {path}.")
            rows[frame_index] = row
    if not rows:
        raise ValueError(f"No frame events found in: {path}")
    return rows


def _validated_counts(
    value: Any,
    *,
    classes: tuple[str, ...],
    label: str,
) -> dict[str, int]:
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object.")
    unknown = sorted(set(value) - set(classes))
    if unknown:
        raise ValueError(f"{label} contains unknown classes: {unknown}")
    counts: dict[str, int] = {}
    for class_name in classes:
        count = value.get(class_name, 0)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError(
                f"{label}.{class_name} must be a non-negative integer."
            )
        counts[class_name] = count
    return counts


def evaluate_count_files(
    events_path: str | Path,
    ground_truth_path: str | Path,
    class_names_path: str | Path,
) -> dict[str, Any]:
    events_source = Path(events_path)
    truth_source = Path(ground_truth_path)
    if not events_source.is_file():
        raise FileNotFoundError(f"Runtime events not found: {events_source}")
    if not truth_source.is_file():
        raise FileNotFoundError(f"Counting ground truth not found: {truth_source}")

    classes = tuple(load_class_names(class_names_path).values())
    events = _load_events(events_source)
    truth = _load_json(truth_source)
    if truth.get("schema_version") != "1.0":
        raise ValueError("Counting ground truth schema_version must be '1.0'.")
    truth_frames = truth.get("frames")
    if not isinstance(truth_frames, list) or not truth_frames:
        raise ValueError("Counting ground truth requires a non-empty frames array.")

    absolute_by_class = {class_name: [] for class_name in classes}
    signed_by_class = {class_name: [] for class_name in classes}
    total_frame_errors: list[int] = []
    exact_frames = 0
    evaluated_frames: list[int] = []
    seen_truth_frames: set[int] = set()

    for item_index, truth_frame in enumerate(truth_frames):
        if not isinstance(truth_frame, dict):
            raise ValueError(f"frames[{item_index}] must be an object.")
        frame_index = truth_frame.get("frame_index")
        if not isinstance(frame_index, int) or frame_index < 1:
            raise ValueError(f"frames[{item_index}].frame_index is invalid.")
        if frame_index in seen_truth_frames:
            raise ValueError(f"Duplicate ground-truth frame_index {frame_index}.")
        seen_truth_frames.add(frame_index)
        if frame_index not in events:
            raise ValueError(
                f"Runtime events do not contain annotated frame {frame_index}."
            )

        expected = _validated_counts(
            truth_frame.get("visible_counts"),
            classes=classes,
            label=f"frames[{item_index}].visible_counts",
        )
        observed = _validated_counts(
            events[frame_index].get("visible_counts"),
            classes=classes,
            label=f"events[{frame_index}].visible_counts",
        )
        frame_exact = True
        for class_name in classes:
            error = observed[class_name] - expected[class_name]
            signed_by_class[class_name].append(error)
            absolute_by_class[class_name].append(abs(error))
            frame_exact = frame_exact and error == 0
        exact_frames += int(frame_exact)
        total_frame_errors.append(abs(sum(observed.values()) - sum(expected.values())))
        evaluated_frames.append(frame_index)

    per_class = {
        class_name: {
            "mae": statistics.fmean(absolute_by_class[class_name]),
            "mean_error": statistics.fmean(signed_by_class[class_name]),
        }
        for class_name in classes
    }
    all_absolute_errors = [
        error
        for class_name in classes
        for error in absolute_by_class[class_name]
    ]

    unique_truth_raw = truth.get("unique_session_counts")
    unique_metrics: dict[str, Any] | None = None
    if unique_truth_raw is not None:
        expected_unique = _validated_counts(
            unique_truth_raw,
            classes=classes,
            label="unique_session_counts",
        )
        final_event = events[max(events)]
        observed_unique = _validated_counts(
            final_event.get("unique_session_counts"),
            classes=classes,
            label="final_event.unique_session_counts",
        )
        unique_by_class = {
            class_name: {
                "ground_truth": expected_unique[class_name],
                "predicted": observed_unique[class_name],
                "error": observed_unique[class_name] - expected_unique[class_name],
                "absolute_error": abs(
                    observed_unique[class_name] - expected_unique[class_name]
                ),
            }
            for class_name in classes
        }
        unique_metrics = {
            "per_class": unique_by_class,
            "mae_across_classes": statistics.fmean(
                item["absolute_error"] for item in unique_by_class.values()
            ),
            "total_count_error": sum(observed_unique.values())
            - sum(expected_unique.values()),
            "absolute_total_count_error": abs(
                sum(observed_unique.values()) - sum(expected_unique.values())
            ),
            "exact": observed_unique == expected_unique,
        }

    return {
        "created_at": utc_now(),
        "operation": "evaluate_count_accuracy",
        "scope": "single_model_use_case_evaluation",
        "events": str(events_source),
        "ground_truth": str(truth_source),
        "classes": list(classes),
        "annotated_frames": len(evaluated_frames),
        "frame_indices": evaluated_frames,
        "visible_counts": {
            "mae_across_class_frame_pairs": statistics.fmean(all_absolute_errors),
            "total_count_mae_per_frame": statistics.fmean(total_frame_errors),
            "exact_all_class_frame_rate": exact_frames / len(evaluated_frames),
            "per_class": per_class,
        },
        "unique_session_counts": unique_metrics,
        "limitations": (
            "Track duplicate, missed-track, and identity-switch rates require "
            "persistent ground-truth track identities and are not inferred "
            "from aggregate count annotations."
        ),
    }


def main() -> None:
    args = build_parser().parse_args()
    payload = evaluate_count_files(
        events_path=args.events,
        ground_truth_path=args.ground_truth,
        class_names_path=args.class_names,
    )
    output = write_json(args.output, payload)
    print(f"Counting accuracy: {output}")


if __name__ == "__main__":
    main()
