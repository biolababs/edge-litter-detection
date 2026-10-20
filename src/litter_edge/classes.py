from __future__ import annotations

from pathlib import Path

import yaml


def load_class_names(path: str | Path) -> dict[int, str]:
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    raw_names = payload.get("names", payload)
    if isinstance(raw_names, list):
        names = {index: str(name) for index, name in enumerate(raw_names)}
    elif isinstance(raw_names, dict):
        names = {int(index): str(name) for index, name in raw_names.items()}
    else:
        raise ValueError(f"Class names must be a list or mapping: {source}")
    if not names:
        raise ValueError(f"No class names found in: {source}")
    if sorted(names) != list(range(len(names))):
        raise ValueError("Class IDs must be contiguous and start at zero.")
    return names
