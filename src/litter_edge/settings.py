from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ProjectSettings:
    project_name: str
    backend: str
    model: str
    base_model: str
    class_names_file: Path
    task: str
    image_size: int
    epochs: int
    batch: int | float
    device: str | int
    workers: int
    seed: int
    deterministic: bool
    patience: int
    confidence: float
    iou: float
    max_detections: int
    output_dir: Path
    run_name: str
    engine_workspace_gb: int
    preferred_incremental_memory_gb: float
    maximum_incremental_memory_gb: float
    minimum_remaining_available_memory_gb: float
    tracking_enabled: bool
    tracking_iou_threshold: float
    tracking_max_missed_frames: int
    tracking_min_confirmed_hits: int
    tracking_class_mismatch_penalty: float
    separation_policy_file: Path
    storage_database: Path
    storage_flush_frames: int
    storage_persist_detections: bool


def _required(mapping: dict[str, Any], key: str) -> Any:
    if key not in mapping:
        raise ValueError(f"Missing required configuration key: {key}")
    return mapping[key]


def load_settings(path: str | Path) -> ProjectSettings:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    target = raw.get("target") or {}
    tracking = raw.get("tracking") or {}
    separation = raw.get("separation") or {}
    storage = raw.get("storage") or {}
    validation = raw.get("validation") or {}
    required_gates = validation.get("operational_gates") or {}
    settings = ProjectSettings(
        project_name=str(_required(raw, "project_name")),
        backend=str(raw.get("backend", "rfdetr")),
        model=str(_required(raw, "model")),
        base_model=str(raw.get("base_model", "rfdetr-nano")),
        class_names_file=Path(raw.get("class_names", "config/classes.yaml")),
        task=str(raw.get("task", "detect")),
        image_size=int(raw.get("image_size", 640)),
        epochs=int(raw.get("epochs", 100)),
        batch=raw.get("batch", -1),
        device=raw.get("device", 0),
        workers=int(raw.get("workers", 8)),
        seed=int(raw.get("seed", 42)),
        deterministic=bool(raw.get("deterministic", True)),
        patience=int(raw.get("patience", 30)),
        confidence=float(raw.get("confidence", 0.25)),
        iou=float(raw.get("iou", 0.45)),
        max_detections=int(raw.get("max_detections", 100)),
        output_dir=Path(raw.get("output_dir", "runs/litter")),
        run_name=str(raw.get("run_name", "rfdetr-nano-baseline")),
        engine_workspace_gb=int(target.get("engine_workspace_gb", 1)),
        preferred_incremental_memory_gb=float(
            required_gates.get("preferred_incremental_memory_gb", 1.5)
        ),
        maximum_incremental_memory_gb=float(
            required_gates.get("maximum_incremental_memory_gb", 2.0)
        ),
        minimum_remaining_available_memory_gb=float(
            required_gates.get("minimum_remaining_available_memory_gb", 2.0)
        ),
        tracking_enabled=bool(tracking.get("enabled", True)),
        tracking_iou_threshold=float(tracking.get("iou_threshold", 0.3)),
        tracking_max_missed_frames=int(tracking.get("max_missed_frames", 30)),
        tracking_min_confirmed_hits=int(tracking.get("min_confirmed_hits", 2)),
        tracking_class_mismatch_penalty=float(
            tracking.get("class_mismatch_penalty", 0.75)
        ),
        separation_policy_file=Path(
            separation.get("policy", "config/separation.yaml")
        ),
        storage_database=Path(storage.get("database", "state/litter-edge.db")),
        storage_flush_frames=int(storage.get("flush_frames", 15)),
        storage_persist_detections=bool(storage.get("persist_detections", False)),
    )
    validate_settings(settings)
    return settings


def validate_settings(settings: ProjectSettings) -> None:
    if settings.task != "detect":
        raise ValueError("This study currently supports task='detect' only.")
    if settings.backend != "rfdetr":
        raise ValueError("backend must be 'rfdetr'.")
    if settings.image_size <= 0 or settings.image_size % 32:
        raise ValueError("image_size must be a positive multiple of 32.")
    if settings.epochs <= 0:
        raise ValueError("epochs must be positive.")
    if not 0.0 <= settings.confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1.")
    if not 0.0 <= settings.iou <= 1.0:
        raise ValueError("iou must be between 0 and 1.")
    if settings.max_detections <= 0:
        raise ValueError("max_detections must be positive.")
    if settings.engine_workspace_gb <= 0:
        raise ValueError("engine_workspace_gb must be positive.")
    if settings.preferred_incremental_memory_gb <= 0:
        raise ValueError("preferred_incremental_memory_gb must be positive.")
    if settings.maximum_incremental_memory_gb <= 0:
        raise ValueError("maximum_incremental_memory_gb must be positive.")
    if settings.minimum_remaining_available_memory_gb <= 0:
        raise ValueError("minimum_remaining_available_memory_gb must be positive.")
    if settings.preferred_incremental_memory_gb > settings.maximum_incremental_memory_gb:
        raise ValueError(
            "preferred_incremental_memory_gb cannot exceed "
            "maximum_incremental_memory_gb."
        )
    if not 0.0 <= settings.tracking_iou_threshold <= 1.0:
        raise ValueError("tracking.iou_threshold must be between 0 and 1.")
    if settings.tracking_max_missed_frames < 0:
        raise ValueError("tracking.max_missed_frames cannot be negative.")
    if settings.tracking_min_confirmed_hits <= 0:
        raise ValueError("tracking.min_confirmed_hits must be positive.")
    if not 0.0 < settings.tracking_class_mismatch_penalty <= 1.0:
        raise ValueError("tracking.class_mismatch_penalty must be in (0, 1].")
    if settings.storage_flush_frames <= 0:
        raise ValueError("storage.flush_frames must be positive.")

