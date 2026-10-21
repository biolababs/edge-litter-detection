from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any


def package(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def command(*parts: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return {
            "command": list(parts),
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {"command": list(parts), "error": type(exc).__name__}


def torch_manifest() -> dict[str, Any]:
    try:
        import torch
    except ImportError:
        return {"installed": False}
    available = bool(torch.cuda.is_available())
    devices = []
    if available:
        for index in range(torch.cuda.device_count()):
            properties = torch.cuda.get_device_properties(index)
            devices.append(
                {
                    "index": index,
                    "name": properties.name,
                    "total_memory_bytes": properties.total_memory,
                }
            )
    return {
        "installed": True,
        "version": torch.__version__,
        "accelerator_available": available,
        "cuda_version": torch.version.cuda,
        "hip_version": torch.version.hip,
        "device_count": len(devices),
        "devices": devices,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write a read-only cross-platform edge-AI hardware manifest."
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": sys.version,
        "packages": {
            "torch": package("torch"),
            "transformers": package("transformers"),
            "rfdetr": package("rfdetr"),
            "onnxruntime": package("onnxruntime"),
            "openvino": package("openvino"),
            "tensorrt": package("tensorrt"),
            "opencv": package("opencv-python-headless") or package("opencv-python"),
        },
        "torch": torch_manifest(),
        "commands": {
            "nvidia_smi": command("nvidia-smi"),
            "rocm_smi": command("rocm-smi", "--showproductname"),
            "jetson_release": command("cat", "/etc/nv_tegra_release"),
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
