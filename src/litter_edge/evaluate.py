from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from .common import environment_manifest, require_file, write_json
from .device import resolve_torch_device
from .settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate one trained RF-DETR Nano litter checkpoint."
    )
    parser.add_argument("--config", default="config/project.yaml")
    parser.add_argument("--weights", required=True)
    parser.add_argument("--data", default="data/litter")
    parser.add_argument("--split", choices=("val", "test"), default="test")
    parser.add_argument("--device")
    parser.add_argument(
        "--output",
        default="reports/generated/detection_accuracy.json",
    )
    return parser


def _json_ready(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if hasattr(value, "results_dict"):
        return _json_ready(value.results_dict)
    if hasattr(value, "tolist"):
        return _json_ready(value.tolist())
    if hasattr(value, "item"):
        try:
            return _json_ready(value.item())
        except (TypeError, ValueError):
            pass
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value


def _ensure_split_available(dataset: Path, split: str) -> None:
    if split != "test":
        return
    for filename in ("data.yaml", "data.yml"):
        data_config = dataset / filename
        if not data_config.is_file():
            continue
        with data_config.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        if not payload.get("test"):
            raise ValueError(
                f"{data_config} does not declare a test split. Use --split val "
                "or add a frozen held-out test path before reporting test accuracy."
            )
        return
    if not (dataset / "test" / "_annotations.coco.json").is_file():
        raise ValueError(
            "No RF-DETR test split declaration was found. Provide data.yaml "
            "with a test entry or a COCO test/_annotations.coco.json file."
        )


def main() -> None:
    args = build_parser().parse_args()
    settings = load_settings(args.config)
    weights = require_file(args.weights, "Trained RF-DETR Nano weights")
    dataset = Path(args.data)
    if not dataset.is_dir():
        raise FileNotFoundError(f"RF-DETR dataset directory not found: {dataset}")
    _ensure_split_available(dataset, args.split)
    device = resolve_torch_device(args.device or str(settings.device))

    try:
        from rfdetr import RFDETR
    except ImportError as exc:
        raise RuntimeError(
            "Install RF-DETR evaluation dependencies before evaluating."
        ) from exc

    model = RFDETR.from_checkpoint(str(weights), device=device)
    metrics = model.evaluate(dataset_dir=str(dataset), split=args.split)
    payload = environment_manifest(Path.cwd())
    payload.update(
        {
            "operation": "evaluate_detection_classification",
            "backend": "rfdetr",
            "variant": "nano",
            "weights": str(weights),
            "dataset": str(dataset),
            "split": args.split,
            "device": device,
            "image_size": settings.image_size,
            "metrics": _json_ready(metrics),
            "scope": "single_model_use_case_evaluation",
        }
    )
    output = write_json(args.output, payload)
    print(f"Detection/classification accuracy: {output}")


if __name__ == "__main__":
    main()
