from __future__ import annotations

import os
from collections import Counter
from pathlib import Path
from threading import Lock
from typing import Any

from . import __version__
from .adapters import create_detector
from .classes import load_class_names, load_class_prompts
from .device import resolve_torch_device
from .settings import load_settings
from .sorting import load_separation_policy
from .storage import (
    acknowledge_outbox_event,
    confirm_collection,
    list_outbox_events,
    list_review_queue,
    list_runs,
    summarize_counts,
    update_review,
)

try:
    from fastapi import FastAPI, HTTPException, Request
    from pydantic import BaseModel
    from starlette.concurrency import run_in_threadpool
except ImportError as exc:
    raise RuntimeError(
        "FastAPI dependencies are missing. Install the 'api' optional dependency."
    ) from exc


class DetectorHolder:
    """Lazily loads one detector and serializes access to accelerator state."""

    def __init__(self) -> None:
        config_path = os.environ.get("LITTER_CONFIG", "config/project.yaml")
        self.settings = load_settings(config_path)
        self.backend = os.environ.get("LITTER_BACKEND", self.settings.backend)
        self.model_reference = os.environ.get("LITTER_MODEL", self.settings.model)
        self.class_names_path = os.environ.get(
            "LITTER_CLASSES", str(self.settings.class_names_file)
        )
        self.class_names = load_class_names(self.class_names_path)
        self.class_prompts = load_class_prompts(
            self.class_names_path,
            self.class_names,
            profile=self.backend,
        )
        self.separation_config = os.environ.get(
            "LITTER_SEPARATION_CONFIG",
            str(self.settings.separation_policy_file),
        )
        self.separation_policy = load_separation_policy(
            self.separation_config,
            class_names=self.class_names,
        )
        self.database = Path(
            os.environ.get("LITTER_DATABASE", str(self.settings.storage_database))
        )
        self.counts_only = os.environ.get("LITTER_COUNTS_ONLY", "").lower() in {
            "1",
            "true",
            "yes",
        }
        self.device = resolve_torch_device(
            os.environ.get("LITTER_DEVICE", str(self.settings.device))
        )
        self._detector: Any = None
        self._load_lock = Lock()
        self._predict_lock = Lock()

    @property
    def model_configured(self) -> bool:
        if self.backend in {
            "grounding_dino",
            "grounding-dino",
            "omdet_turbo",
            "omdet-turbo",
            "omdet",
        }:
            return bool(self.model_reference.strip())
        return Path(self.model_reference).is_file()

    def _get_detector(self) -> Any:
        if self._detector is not None:
            return self._detector
        with self._load_lock:
            if self._detector is None:
                self._detector = create_detector(
                    backend=self.backend,
                    model=self.model_reference,
                    class_names=self.class_names,
                    confidence=self.settings.confidence,
                    device=self.device,
                    optimize=True,
                    class_prompts=self.class_prompts,
                    iou=self.settings.iou,
                    max_detections=self.settings.max_detections,
                )
        return self._detector

    def detect(self, image_bytes: bytes) -> dict[str, Any]:
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "API media dependencies are missing. Install the 'api' and "
                "'runtime' optional dependencies."
            ) from exc
        encoded = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Request body is not a decodable image.")
        with self._predict_lock:
            detections = self._get_detector().predict(frame)
        detections = [
            self.separation_policy.apply(detection) for detection in detections
        ]
        counts = Counter(detection.class_name for detection in detections)
        return {
            "mode": "single_image",
            "backend": self.backend,
            "model": self.model_reference,
            "device": self.device,
            "counts": dict(sorted(counts.items())),
            "detections": [detection.to_dict() for detection in detections],
            "note": (
                "Unique tracking counts require the streaming CLI because "
                "independent HTTP requests do not share track state."
            ),
        }


class ReviewDecision(BaseModel):
    status: str
    corrected_class_name: str | None = None
    corrected_destination: str | None = None
    reviewed_by: str | None = None
    note: str | None = None


class CollectionConfirmation(BaseModel):
    run_id: str
    class_name: str
    quantity: int = 1
    track_id: int | None = None
    method: str
    confirmed_by: str | None = None
    external_reference: str | None = None
    note: str | None = None


def create_app() -> Any:
    holder = DetectorHolder()
    app = FastAPI(
        title="Edge Litter Detection API",
        version=__version__,
        description="Detect, classify, and count litter in an image.",
    )

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {
            "status": "ok",
            "backend": holder.backend,
            "device": holder.device,
            "model_configured": holder.model_configured,
            "model_loaded": holder._detector is not None,
            "database": str(holder.database),
            "database_exists": holder.database.is_file(),
            "service_mode": "counts_api" if holder.counts_only else "detection_api",
        }

    @app.get("/readyz")
    def readyz() -> dict[str, Any]:
        if holder.counts_only:
            return {
                "status": "ready",
                "service_mode": "counts_api",
                "database": str(holder.database),
            }
        if not holder.model_configured:
            raise HTTPException(
                status_code=503,
                detail="The configured detector model is not available.",
            )
        return {
            "status": "ready",
            "backend": holder.backend,
            "device": holder.device,
        }

    @app.post("/v1/detect")
    async def detect(request: Request) -> dict[str, Any]:
        if holder.counts_only:
            raise HTTPException(
                status_code=503,
                detail="Image detection is disabled in counts-only API mode.",
            )
        image_bytes = await request.body()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Request body is empty.")
        maximum_bytes = int(os.environ.get("LITTER_MAX_IMAGE_BYTES", "20971520"))
        if len(image_bytes) > maximum_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Image exceeds the {maximum_bytes}-byte request limit.",
            )
        try:
            return await run_in_threadpool(holder.detect, image_bytes)
        except (FileNotFoundError, RuntimeError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/v1/counts/summary")
    def counts_summary(
        vehicle_id: str | None = None,
        route_id: str | None = None,
        edge_device_id: str | None = None,
    ) -> dict[str, Any]:
        return summarize_counts(
            holder.database,
            vehicle_id=vehicle_id,
            route_id=route_id,
            edge_device_id=edge_device_id,
        )

    @app.get("/v1/runs")
    def runs(
        limit: int = 50,
        vehicle_id: str | None = None,
        route_id: str | None = None,
        edge_device_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            return {
                "runs": list_runs(
                    holder.database,
                    limit=limit,
                    vehicle_id=vehicle_id,
                    route_id=route_id,
                    edge_device_id=edge_device_id,
                )
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/v1/review-queue")
    def review_queue(status: str = "pending", limit: int = 50) -> dict[str, Any]:
        try:
            return {
                "reviews": list_review_queue(
                    holder.database,
                    status=status,
                    limit=limit,
                )
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/v1/review-queue/{review_id}")
    def decide_review(review_id: str, decision: ReviewDecision) -> dict[str, Any]:
        corrected_destination = decision.corrected_destination
        if decision.corrected_class_name is not None:
            if decision.corrected_class_name not in holder.class_names.values():
                raise HTTPException(
                    status_code=400,
                    detail="corrected_class_name is not in the configured taxonomy.",
                )
            corrected_destination = (
                corrected_destination
                or holder.separation_policy.destinations[
                    decision.corrected_class_name
                ]
            )
        try:
            updated = update_review(
                holder.database,
                review_id=review_id,
                status=decision.status,
                corrected_class_name=decision.corrected_class_name,
                corrected_destination=corrected_destination,
                reviewed_by=decision.reviewed_by,
                note=decision.note,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not updated:
            raise HTTPException(status_code=404, detail="Review item not found.")
        return {"review_id": review_id, "status": decision.status}

    @app.get("/v1/integration/events")
    def integration_events(
        limit: int = 100,
        include_acknowledged: bool = False,
    ) -> dict[str, Any]:
        try:
            return {
                "events": list_outbox_events(
                    holder.database,
                    limit=limit,
                    include_acknowledged=include_acknowledged,
                )
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/v1/integration/events/{event_id}/ack")
    def acknowledge_event(event_id: str) -> dict[str, Any]:
        if not acknowledge_outbox_event(holder.database, event_id):
            raise HTTPException(
                status_code=404,
                detail="Pending integration event not found.",
            )
        return {"event_id": event_id, "acknowledged": True}

    @app.post("/v1/collections")
    def collection_confirmation(
        confirmation: CollectionConfirmation,
    ) -> dict[str, Any]:
        if confirmation.class_name not in holder.class_names.values():
            raise HTTPException(
                status_code=400,
                detail="class_name is not in the configured taxonomy.",
            )
        try:
            return confirm_collection(
                holder.database,
                run_id=confirmation.run_id,
                class_name=confirmation.class_name,
                quantity=confirmation.quantity,
                track_id=confirmation.track_id,
                method=confirmation.method,
                confirmed_by=confirmation.confirmed_by,
                external_reference=confirmation.external_reference,
                note=confirmation.note,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()
