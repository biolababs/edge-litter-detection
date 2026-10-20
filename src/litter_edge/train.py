from __future__ import annotations

import argparse
from pathlib import Path

from .common import environment_manifest, write_json
from .device import resolve_torch_device
from .settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the RF-DETR litter model.")
    parser.add_argument("--config", default="config/project.yaml")
    parser.add_argument("--data", default="data/litter")
    parser.add_argument("--model", help="Base RF-DETR model/checkpoint override.")
    parser.add_argument("--name", help="Run-name override.")
    parser.add_argument("--device", help="auto, cpu, cuda, cuda:0, etc.")
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--batch", type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = load_settings(args.config)
    dataset = Path(args.data)
    if not dataset.is_dir():
        raise FileNotFoundError(f"RF-DETR dataset directory not found: {dataset}")
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
