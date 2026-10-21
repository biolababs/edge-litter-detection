from __future__ import annotations

from pathlib import Path

import yaml


def _load_payload(path: str | Path) -> tuple[Path, dict[object, object]]:
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Class configuration must be a mapping: {source}")
    return source, payload


def load_class_names(path: str | Path) -> dict[int, str]:
    source, payload = _load_payload(path)
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


def load_class_prompts(
    path: str | Path,
    class_names: dict[int, str] | None = None,
    profile: str | None = None,
) -> dict[int, str]:
    source, payload = _load_payload(path)
    names = class_names or load_class_names(source)
    profile_key = (
        f"{profile.strip().lower().replace('-', '_')}_prompts"
        if profile
        else None
    )
    raw_prompts = payload.get(profile_key) if profile_key else None
    if raw_prompts is None:
        raw_prompts = payload.get("prompts")
    if raw_prompts is None:
        return {
            class_id: class_name.replace("_", " ")
            for class_id, class_name in names.items()
        }
    if isinstance(raw_prompts, list):
        prompts = {
            index: str(prompt).strip()
            for index, prompt in enumerate(raw_prompts)
        }
    elif isinstance(raw_prompts, dict):
        prompts = {
            int(index): str(prompt).strip()
            for index, prompt in raw_prompts.items()
        }
    else:
        raise ValueError(f"Class prompts must be a list or mapping: {source}")
    if set(prompts) != set(names):
        raise ValueError("Class prompt IDs must exactly match class name IDs.")
    if any(not prompt for prompt in prompts.values()):
        raise ValueError("Class prompts cannot be empty.")
    return prompts
