from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def command(*parts: str) -> dict[str, object]:
    try:
        result = subprocess.run(parts, capture_output=True, text=True, timeout=15)
        return {
            "command": list(parts),
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except Exception as exc:
        return {"command": list(parts), "error": type(exc).__name__}


def package(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version,
        "packages": {
            "torch": package("torch"),
            "torchvision": package("torchvision"),
            "transformers": package("transformers"),
            "rfdetr": package("rfdetr"),
        },
        "commands": [
            command("uname", "-a"),
            command("nvpmodel", "-q"),
            command("jetson_clocks", "--show"),
            command("dpkg-query", "-W", "nvidia-jetpack"),
        ],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

