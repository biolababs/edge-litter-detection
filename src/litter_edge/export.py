from __future__ import annotations

import argparse
from pathlib import Path

from .common import environment_manifest, require_file, write_json
from .device import resolve_torch_device
from .settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export the RF-DETR litter model.")
    parser.add_argument("--config", default="config/project.yaml")
    parser.add_argument("--weights", required=True)
    parser.add_argument(
        "--format",
        choices=("onnx", "tensorrt", "tflite"),
        default="onnx",
    )
    parser.add_argument("--precision", choices=("fp32", "fp16", "int8"), default="fp32")
    parser.add_argument(
        "--calibration-data",
        help="Representative image directory or .npy file for TFLite INT8.",
    )
    parser.add_argument("--device")
    parser.add_argument("--output-dir", default="models")
    return parser


def build_export_arguments(
    *,
    export_format: str,
    precision: str,
    output_dir: Path,
    image_size: int,
    calibration_data: str | None = None,
) -> dict[str, object]:
    export_args: dict[str, object] = {
        "format": export_format,
        "output_dir": str(output_dir),
        "shape": (image_size, image_size),
        "batch_size": 1,
    }
    if export_format == "onnx" and precision != "fp32":
        raise ValueError("ONNX export uses FP32; pass --precision fp32.")
    if export_format == "tensorrt":
        if precision == "int8":
            raise ValueError(
                "Direct RF-DETR TensorRT INT8 export is not exposed by this "
                "command. Use FP16 or FP32."
            )
        export_args["fp16"] = precision == "fp16"
    if export_format == "tflite":
        export_args["quantization"] = precision
        if precision == "int8":
            if not calibration_data:
                raise ValueError(
                    "--calibration-data is required for TFLite INT8 export."
                )
            export_args["calibration_data"] = calibration_data
    return export_args


def main() -> None:
    args = build_parser().parse_args()
    settings = load_settings(args.config)
    weights = require_file(args.weights, "Trained RF-DETR weights")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    device = resolve_torch_device(args.device or str(settings.device))
    try:
        export_args = build_export_arguments(
            export_format=args.format,
            precision=args.precision,
            output_dir=output_dir,
            image_size=settings.image_size,
            calibration_data=args.calibration_data,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    try:
        from rfdetr import RFDETR
    except ImportError as exc:
        raise RuntimeError(
            "Install the matching RF-DETR export extra, such as "
            "'rfdetr[onnx]' or 'rfdetr[tensorrt]'."
        ) from exc

    model = RFDETR.from_checkpoint(str(weights), device=device)
    exported = model.export(**export_args)
    manifest = environment_manifest(Path.cwd())
    manifest.update(
        {
            "operation": "export",
            "backend": "rfdetr",
            "weights": str(weights),
            "exported": str(exported),
            "format": args.format,
            "precision": args.precision,
            "calibration_data": args.calibration_data,
            "device": device,
            "image_size": settings.image_size,
        }
    )
    manifest_path = output_dir / f"{weights.stem}-{args.format}.manifest.json"
    output = write_json(manifest_path, manifest)
    print(f"Export result: {exported}")
    print(f"Export manifest: {output}")


if __name__ == "__main__":
    main()
