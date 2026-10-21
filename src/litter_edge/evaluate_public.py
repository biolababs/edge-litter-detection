from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .adapters import create_detector
from .classes import load_class_names, load_class_prompts
from .common import environment_manifest, require_file, write_json
from .device import resolve_torch_device
from .metrics import summarize_samples
from .schema import Detection
from .settings import load_settings, normalize_backend, resolve_model_reference


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate a public or project detector on a frozen COCO-format "
            "litter split without training or model comparison."
        )
    )
    parser.add_argument("--config", default="config/project.yaml")
    parser.add_argument(
        "--backend",
        choices=("grounding_dino", "omdet_turbo", "rfdetr"),
        default="omdet_turbo",
    )
    parser.add_argument("--model")
    parser.add_argument("--class-names")
    parser.add_argument("--data", default="data/taco-operational-v1")
    parser.add_argument("--split", choices=("valid", "test"), default="test")
    parser.add_argument("--device")
    parser.add_argument("--confidence", type=float)
    parser.add_argument("--max-images", type=int, default=0)
    parser.add_argument(
        "--output",
        default="reports/generated/public_zero_shot_accuracy.json",
    )
    parser.add_argument(
        "--predictions-output",
        help="Optional COCO detection JSON; defaults beside --output.",
    )
    return parser


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portable_path(path: Path, root: Path | None = None) -> str:
    resolved = path.resolve()
    repository = (root or Path.cwd()).resolve()
    try:
        return str(resolved.relative_to(repository))
    except ValueError:
        return str(resolved)


def _xywh_to_xyxy(box: list[float]) -> tuple[float, float, float, float]:
    x, y, width, height = box
    return x, y, x + width, y + height


def _iou(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    x1 = max(left[0], right[0])
    y1 = max(left[1], right[1])
    x2 = min(left[2], right[2])
    y2 = min(left[3], right[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    right_area = max(0.0, right[2] - right[0]) * max(
        0.0, right[3] - right[1]
    )
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


def _operating_point_metrics(
    ground_truth: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    class_names: dict[int, str],
    *,
    iou_threshold: float = 0.5,
) -> dict[str, Any]:
    ground_truth_by_key: dict[
        tuple[int, int], list[tuple[float, float, float, float]]
    ] = defaultdict(list)
    predictions_by_key: dict[
        tuple[int, int],
        list[tuple[float, tuple[float, float, float, float]]],
    ] = defaultdict(list)
    support: Counter[int] = Counter()

    for annotation in ground_truth:
        if int(annotation.get("iscrowd", 0)):
            continue
        category_id = int(annotation["category_id"])
        image_id = int(annotation["image_id"])
        ground_truth_by_key[(image_id, category_id)].append(
            _xywh_to_xyxy([float(value) for value in annotation["bbox"]])
        )
        support[category_id] += 1

    for prediction in predictions:
        category_id = int(prediction["category_id"])
        image_id = int(prediction["image_id"])
        predictions_by_key[(image_id, category_id)].append(
            (
                float(prediction["score"]),
                _xywh_to_xyxy([float(value) for value in prediction["bbox"]]),
            )
        )

    totals: Counter[str] = Counter()
    per_class: dict[str, dict[str, Any]] = {}
    for category_id, class_name in class_names.items():
        true_positive = 0
        false_positive = 0
        false_negative = 0
        image_ids = {
            image_id
            for image_id, candidate_id in (
                set(ground_truth_by_key) | set(predictions_by_key)
            )
            if candidate_id == category_id
        }
        for image_id in image_ids:
            reference_boxes = ground_truth_by_key[(image_id, category_id)]
            candidate_predictions = sorted(
                predictions_by_key[(image_id, category_id)],
                key=lambda item: item[0],
                reverse=True,
            )
            matched: set[int] = set()
            for _, predicted_box in candidate_predictions:
                best_index = None
                best_iou = 0.0
                for index, reference_box in enumerate(reference_boxes):
                    if index in matched:
                        continue
                    overlap = _iou(predicted_box, reference_box)
                    if overlap > best_iou:
                        best_iou = overlap
                        best_index = index
                if best_index is not None and best_iou >= iou_threshold:
                    matched.add(best_index)
                    true_positive += 1
                else:
                    false_positive += 1
            false_negative += len(reference_boxes) - len(matched)

        precision_denominator = true_positive + false_positive
        recall_denominator = true_positive + false_negative
        precision = (
            true_positive / precision_denominator if precision_denominator else 0.0
        )
        recall = true_positive / recall_denominator if recall_denominator else 0.0
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        per_class[class_name] = {
            "support": support[category_id],
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "evidence_status": (
                "measured" if support[category_id] else "no_ground_truth_instances"
            ),
        }
        totals.update(
            {
                "true_positive": true_positive,
                "false_positive": false_positive,
                "false_negative": false_negative,
            }
        )

    total_precision_denominator = totals["true_positive"] + totals["false_positive"]
    total_recall_denominator = totals["true_positive"] + totals["false_negative"]
    micro_precision = (
        totals["true_positive"] / total_precision_denominator
        if total_precision_denominator
        else 0.0
    )
    micro_recall = (
        totals["true_positive"] / total_recall_denominator
        if total_recall_denominator
        else 0.0
    )
    supported = [
        metrics for metrics in per_class.values() if int(metrics["support"]) > 0
    ]
    return {
        "iou_threshold": iou_threshold,
        "matching": "score-ordered greedy one-to-one matching within image and class",
        "crowd_annotations": "excluded from operating-point metrics",
        "micro": {
            **dict(totals),
            "precision": micro_precision,
            "recall": micro_recall,
            "f1": (
                2.0 * micro_precision * micro_recall
                / (micro_precision + micro_recall)
                if micro_precision + micro_recall
                else 0.0
            ),
        },
        "macro_supported_classes": {
            "class_count": len(supported),
            "precision": (
                sum(float(item["precision"]) for item in supported) / len(supported)
                if supported
                else None
            ),
            "recall": (
                sum(float(item["recall"]) for item in supported) / len(supported)
                if supported
                else None
            ),
            "f1": (
                sum(float(item["f1"]) for item in supported) / len(supported)
                if supported
                else None
            ),
        },
        "per_class": per_class,
    }


def _coco_metrics(
    annotation_path: Path,
    predictions: list[dict[str, Any]],
    image_ids: list[int],
    class_names: dict[int, str],
) -> dict[str, Any]:
    try:
        import numpy as np
        from pycocotools.coco import COCO
        from pycocotools.cocoeval import COCOeval
    except ImportError as exc:
        raise RuntimeError(
            "Install the evaluation dependency before running public accuracy "
            "evaluation: python -m pip install -e '.[evaluation]'"
        ) from exc

    coco_ground_truth = COCO(str(annotation_path))
    if predictions:
        coco_predictions = coco_ground_truth.loadRes(predictions)
    else:
        coco_predictions = COCO()
        coco_predictions.dataset = {
            "images": [
                image
                for image in coco_ground_truth.dataset["images"]
                if int(image["id"]) in set(image_ids)
            ],
            "categories": coco_ground_truth.dataset["categories"],
            "annotations": [],
        }
        coco_predictions.createIndex()
    evaluator = COCOeval(coco_ground_truth, coco_predictions, "bbox")
    evaluator.params.imgIds = image_ids
    evaluator.params.catIds = sorted(class_names)
    evaluator.evaluate()
    evaluator.accumulate()
    evaluator.summarize()

    precision = evaluator.eval["precision"]
    recall = evaluator.eval["recall"]
    per_class: dict[str, dict[str, float | int | None]] = {}
    annotation_support = Counter(
        int(annotation["category_id"])
        for annotation in coco_ground_truth.dataset["annotations"]
        if int(annotation["image_id"]) in set(image_ids)
    )
    threshold_50 = int(np.argmin(np.abs(evaluator.params.iouThrs - 0.5)))
    for category_index, category_id in enumerate(evaluator.params.catIds):
        all_precision = precision[:, :, category_index, 0, -1]
        valid_precision = all_precision[all_precision > -1]
        precision_50 = precision[threshold_50, :, category_index, 0, -1]
        valid_precision_50 = precision_50[precision_50 > -1]
        all_recall = recall[:, category_index, 0, -1]
        valid_recall = all_recall[all_recall > -1]
        per_class[class_names[category_id]] = {
            "support": annotation_support[category_id],
            "ap_50_95": (
                float(np.mean(valid_precision)) if valid_precision.size else None
            ),
            "ap_50": (
                float(np.mean(valid_precision_50))
                if valid_precision_50.size
                else None
            ),
            "ar_100": float(np.mean(valid_recall)) if valid_recall.size else None,
        }

    stats = evaluator.stats
    return {
        "implementation": "pycocotools COCOeval bbox",
        "max_detections": [1, 10, 100],
        "aggregate": {
            "ap_50_95": float(stats[0]),
            "ap_50": float(stats[1]),
            "ap_75": float(stats[2]),
            "ap_small": float(stats[3]),
            "ap_medium": float(stats[4]),
            "ap_large": float(stats[5]),
            "ar_1": float(stats[6]),
            "ar_10": float(stats[7]),
            "ar_100": float(stats[8]),
            "ar_small": float(stats[9]),
            "ar_medium": float(stats[10]),
            "ar_large": float(stats[11]),
        },
        "per_class": per_class,
    }


def main() -> None:
    args = build_parser().parse_args()
    if args.max_images < 0:
        raise ValueError("max-images cannot be negative.")
    settings = load_settings(args.config)
    confidence = settings.confidence if args.confidence is None else args.confidence
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1.")

    dataset = Path(args.data).expanduser().resolve()
    split_dir = dataset / args.split
    annotation_path = require_file(
        split_dir / "_annotations.coco.json",
        f"COCO annotations for the {args.split} split",
    )
    dataset_manifest = require_file(dataset / "manifest.json", "Dataset manifest")
    annotation_payload = json.loads(annotation_path.read_text(encoding="utf-8"))
    images = sorted(
        annotation_payload.get("images", []),
        key=lambda image: int(image["id"]),
    )
    if args.max_images:
        images = images[: args.max_images]
    if not images:
        raise RuntimeError(f"No images are declared in {annotation_path}")
    image_ids = [int(image["id"]) for image in images]
    image_id_set = set(image_ids)
    ground_truth = [
        annotation
        for annotation in annotation_payload.get("annotations", [])
        if int(annotation["image_id"]) in image_id_set
    ]

    class_names_path = args.class_names or str(settings.class_names_file)
    class_names = load_class_names(class_names_path)
    backend = normalize_backend(args.backend)
    model_reference = resolve_model_reference(
        backend,
        explicit_model=args.model,
        configured_backend=settings.backend,
        configured_model=settings.model,
    )
    device = resolve_torch_device(args.device or str(settings.device))
    detector = create_detector(
        backend=backend,
        model=model_reference,
        class_names=class_names,
        confidence=confidence,
        device=device,
        optimize=True,
        class_prompts=load_class_prompts(
            class_names_path,
            class_names,
            profile=backend,
        ),
        iou=settings.iou,
        max_detections=settings.max_detections,
    )

    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "Install a runtime optional dependency before evaluation."
        ) from exc

    predictions: list[dict[str, Any]] = []
    inference_times: list[float] = []
    started = time.perf_counter()
    for index, image in enumerate(images, start=1):
        image_path = require_file(
            split_dir / str(image["file_name"]),
            f"Evaluation image {image['id']}",
        )
        frame = cv2.imread(str(image_path))
        if frame is None:
            raise RuntimeError(f"Unable to decode evaluation image: {image_path}")
        inference_started = time.perf_counter()
        detections: list[Detection] = detector.predict(frame)
        inference_times.append((time.perf_counter() - inference_started) * 1000.0)
        for detection in detections:
            predictions.append(
                {
                    "image_id": int(image["id"]),
                    "category_id": detection.class_id,
                    "bbox": [
                        detection.x1,
                        detection.y1,
                        max(0.0, detection.x2 - detection.x1),
                        max(0.0, detection.y2 - detection.y1),
                    ],
                    "score": detection.confidence,
                }
            )
        if index % 25 == 0 or index == len(images):
            print(f"Evaluated {index}/{len(images)} images", flush=True)
    wall_seconds = time.perf_counter() - started

    output_path = Path(args.output)
    predictions_path = Path(
        args.predictions_output
        or output_path.with_name(f"{output_path.stem}-predictions.json")
    )
    predictions_path.parent.mkdir(parents=True, exist_ok=True)
    predictions_path.write_text(
        json.dumps(predictions, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    dataset_manifest_payload = json.loads(
        dataset_manifest.read_text(encoding="utf-8")
    )
    image_records = sorted(
        (
            {
                "image_id": int(record["image_id"]),
                "local_file": str(record["local_file"]),
                "sha256": str(record["sha256"]),
            }
            for record in dataset_manifest_payload.get("downloaded_images", [])
            if int(record["image_id"]) in image_id_set
        ),
        key=lambda record: record["image_id"],
    )
    image_set_digest = hashlib.sha256(
        json.dumps(image_records, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    payload: dict[str, Any] = environment_manifest(Path.cwd())
    payload.update(
        {
            "operation": "public_zero_shot_detection_evaluation",
            "scope": "single_model_use_case_evaluation_not_model_comparison",
            "backend": backend,
            "model": model_reference,
            "device": device,
            "confidence_threshold": confidence,
            "nms_iou_threshold": settings.iou,
            "maximum_detections": settings.max_detections,
            "dataset": _portable_path(dataset),
            "dataset_name": dataset_manifest_payload.get("dataset"),
            "dataset_manifest": _portable_path(dataset_manifest),
            "dataset_manifest_sha256": _sha256(dataset_manifest),
            "annotations": _portable_path(annotation_path),
            "annotations_sha256": _sha256(annotation_path),
            "split": args.split,
            "split_policy": dataset_manifest_payload.get("split_policy"),
            "split_seed": dataset_manifest_payload.get("seed"),
            "official_dataset_split": False,
            "image_count": len(images),
            "annotation_count": len(ground_truth),
            "prediction_count": len(predictions),
            "evaluated_image_set_sha256": image_set_digest,
            "evaluated_image_records_in_manifest": len(image_records),
            "wall_seconds": wall_seconds,
            "source_to_result_fps": (
                len(images) / wall_seconds if wall_seconds else None
            ),
            "detector_call_ms": summarize_samples(inference_times),
            "coco_bbox": _coco_metrics(
                annotation_path,
                predictions,
                image_ids,
                class_names,
            ),
            "operating_point_iou_50": _operating_point_metrics(
                ground_truth,
                predictions,
                class_names,
                iou_threshold=0.5,
            ),
            "predictions_output": _portable_path(predictions_path),
            "predictions_sha256": _sha256(predictions_path),
            "interpretation": {
                "model_status": (
                    "public pretrained open-vocabulary checkpoint; no project "
                    "litter fine-tuning"
                ),
                "split_status": (
                    "deterministic project-defined group split because TACO "
                    "does not publish an official train/test partition"
                ),
                "taxonomy_status": (
                    "TACO source categories mapped to the 16-class operational "
                    "taxonomy; unsupported distinctions collapse to other_litter"
                ),
                "claim_boundary": (
                    "preliminary public-data zero-shot accuracy only; not target-"
                    "domain, vehicle, sorting-floor, or counting validation"
                ),
            },
        }
    )
    output = write_json(output_path, payload)
    print(f"Public zero-shot accuracy evidence: {output}")


if __name__ == "__main__":
    main()
