from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def package_version(name: str) -> str | None:
    try:
        from importlib.metadata import version

        return version(name)
    except (ImportError, ValueError):
        return None


def git_revision(root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def environment_manifest(root: Path) -> dict[str, Any]:
    return {
        "created_at": utc_now(),
        "python": sys.version,
        "platform": platform.platform(),
        "torch": package_version("torch"),
        "torchvision": package_version("torchvision"),
        "transformers": package_version("transformers"),
        "rfdetr": package_version("rfdetr"),
        "tensorrt": package_version("tensorrt"),
        "git_revision": git_revision(root),
    }


def memory_snapshot() -> dict[str, float | None]:
    """Return lightweight Linux memory evidence in GiB without extra packages."""

    kib_per_gib = 1024 * 1024
    system_available_kib: int | None = None
    process_rss_kib: int | None = None

    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                system_available_kib = int(line.split()[1])
                break
    except (OSError, ValueError, IndexError):
        pass

    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                process_rss_kib = int(line.split()[1])
                break
    except (OSError, ValueError, IndexError):
        pass

    return {
        "system_available_gib": (
            system_available_kib / kib_per_gib
            if system_available_kib is not None
            else None
        ),
        "process_rss_gib": (
            process_rss_kib / kib_per_gib if process_rss_kib is not None else None
        ),
    }


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output.parent,
            prefix=f".{output.name}.",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(payload, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, output)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return output


def require_file(path: str | Path, label: str) -> Path:
    candidate = Path(path)
    if not candidate.is_file():
        raise FileNotFoundError(f"{label} not found: {candidate}")
    return candidate

