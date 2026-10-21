from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .classes import load_class_names
from .common import environment_manifest, write_json
from .device import resolve_torch_device
from .settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the RF-DETR litter model.")
    parser.add_argument("--config", default="config/project.yaml")
    parser.add_argument("--data", default="data/litter")
    parser.add_argument("--class-names")
    parser.add_argument("--model", help="Base RF-DETR model/checkpoint override.")
    parser.add_argument("--name", help="Run-name override.")
    parser.add_argument("--device", help="auto, cpu, cuda, cuda:0, etc.")
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--batch", type=int)
    return parser


def validate_coco_training_taxonomy(
    dataset: Path,
    class_names_file: str | Path,
) -> dict[int, str]:
    annotations_path = dataset / "train" / "_annotations.coco.json"
    if not annotations_path.is_file():
        raise FileNotFoundError(
            "RF-DETR COCO training annotations not found: "
            f"{annotations_path}"
        )
    payload = json.loads(annotations_path.read_text(encoding="utf-8"))
    categories = payload.get("categories")
    if not isinstance(categories, list) or not categories:
        raise ValueError(f"No COCO categories found in: {annotations_path}")
    dataset_names = {
        int(category["id"]): str(category["name"])
        for category in categories
        if isinstance(category, dict)
        and "id" in category
        and "name" in category
    }
    configured_names = load_class_names(class_names_file)
    if dataset_names != configured_names:
        raise ValueError(
            "Training dataset categories do not exactly match the configured "
            f"runtime taxonomy: {class_names_file}"
        )
    return dataset_names


def _dataset_manifest_evidence(dataset: Path) -> dict[str, object] | None:
    manifest_path = dataset / "manifest.json"
    if not manifest_path.is_file():
        return None
    content = manifest_path.read_bytes()
    payload = json.loads(content.decode("utf-8"))
    return {
        "path": str(manifest_path),
        "sha256": hashlib.sha256(content).hexdigest(),
        "training_data_status": payload.get("training_data_status"),
        "classes_without_instances": payload.get(
            "classes_without_instances",
            [],
        ),
    }


def main() -> None:
    args = build_parser().parse_args()
    settings = load_settings(args.config)
    dataset = Path(args.data)
    if not dataset.is_dir():
        raise FileNotFoundError(f"RF-DETR dataset directory not found: {dataset}")
    class_names_file = args.class_names or str(settings.class_names_file)
    dataset_names = validate_coco_training_taxonomy(dataset, class_names_file)
    dataset_evidence = _dataset_manifest_evidence(dataset)
    if dataset_evidence and dataset_evidence["classes_without_instances"]:
        print(
            "WARNING: dataset has no training examples for: "
            + ", ".join(
                str(name)
                for name in dataset_evidence["classes_without_instances"]
            )
        )
    model_reference = args.model or settings.base_model
    run_name = args.name or settings.run_name
    device = resolve_torch_device(args.device or str(settings.device))
    epochs = args.epochs or settings.epochs
    batch_size = args.batch or int(settings.batch)
    run_dir = settings.output_dir / run_name

    try:
        from rfdetr import RFDETRNano
    except ImportError as exc:
        raise RuntimeError(
            "Install RF-DETR training dependencies before training."
        ) from exc

    if model_reference in {"rfdetr-nano", "rf-detr-nano", "rf-detr-nano.pth"}:
        model = RFDETRNano(device=device)
    else:
        model = RFDETRNano(pretrain_weights=model_reference, device=device)
    run_dir.mkdir(parents=True, exist_ok=True)
    model.train(
        dataset_dir=str(dataset),
        output_dir=str(run_dir),
        epochs=epochs,
        batch_size=batch_size,
        resolution=settings.image_size,
        early_stopping=True,
        early_stopping_patience=settings.patience,
        tensorboard=True,
    )

    manifest = environment_manifest(Path.cwd())
    manifest.update(
        {
            "operation": "train",
            "backend": "rfdetr",
            "model": model_reference,
            "data": str(dataset),
            "dataset_manifest": dataset_evidence,
            "class_names": dataset_names,
            "class_names_file": str(class_names_file),
            "epochs": epochs,
            "batch": batch_size,
            "device": device,
            "image_size": settings.image_size,
            "save_dir": str(run_dir),
        }
    )
    output = write_json(run_dir / "research_manifest.json", manifest)
    print(f"Training complete. Manifest: {output}")


if __name__ == "__main__":
    main()
