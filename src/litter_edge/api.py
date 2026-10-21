from __future__ import annotations

import os
from collections import Counter
from contextlib import asynccontextmanager
from pathlib import Path
from threading import BoundedSemaphore, Lock
from typing import Any, Literal

from . import __version__
from .adapters import create_detector
from .classes import load_class_names, load_class_prompts
from .device import resolve_torch_device
from .settings import load_settings, normalize_backend, resolve_model_reference
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
from .streaming import SerializedDetector, StreamManager


DEFAULT_MAXIMUM_IMAGE_BYTES = 20 * 1024 * 1024
DEFAULT_MAXIMUM_IMAGE_PIXELS = 16_777_216
ALLOWED_IMAGE_MEDIA_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


def _enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def _positive_environment_integer(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be positive.")
    return value


def _matches_image_signature(media_type: str, payload: bytes) -> bool:
    if media_type == "image/jpeg":
        return payload.startswith(b"\xff\xd8\xff")
    if media_type == "image/png":
        return payload.startswith(b"\x89PNG\r\n\x1a\n")
    if media_type == "image/webp":
        return (
            len(payload) >= 12
            and payload.startswith(b"RIFF")
            and payload[8:12] == b"WEBP"
        )
    return False

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import FileResponse, Response
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field
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
        backend_override = os.environ.get("LITTER_BACKEND")
        self.backend = normalize_backend(backend_override or self.settings.backend)
        self.model_reference = resolve_model_reference(
            self.backend,
            explicit_model=os.environ.get("LITTER_MODEL"),
            configured_backend=self.settings.backend,
            configured_model=self.settings.model,
        )
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
        self.maximum_image_bytes = _positive_environment_integer(
            "LITTER_MAX_IMAGE_BYTES",
            DEFAULT_MAXIMUM_IMAGE_BYTES,
        )
        self.maximum_image_pixels = _positive_environment_integer(
            "LITTER_MAX_IMAGE_PIXELS",
            DEFAULT_MAXIMUM_IMAGE_PIXELS,
        )
        os.environ.setdefault(
            "OPENCV_IO_MAX_IMAGE_PIXELS",
            str(self.maximum_image_pixels),
        )
        self._detector: Any = None
        self._load_lock = Lock()
        self._predict_lock = Lock()
        self._image_request_slots = BoundedSemaphore(
            _positive_environment_integer(
                "LITTER_MAX_IMAGE_REQUESTS",
                1,
            )
        )

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

    def predict_frame(self, frame: Any) -> list[Any]:
        with self._predict_lock:
            return self._get_detector().predict(frame)

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
        height, width = frame.shape[:2]
        if height * width > self.maximum_image_pixels:
            raise ValueError(
                "Decoded image exceeds the configured pixel limit of "
                f"{self.maximum_image_pixels}."
            )
        detections = self.predict_frame(frame)
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
                "Unique tracking counts require a CLI or dashboard stream "
                "session because independent image requests do not share "
                "track state."
            ),
        }


class ReviewDecision(BaseModel):
    status: Literal["confirmed", "corrected", "rejected"]
    corrected_class_name: str | None = Field(default=None, max_length=128)
    corrected_destination: str | None = Field(default=None, max_length=128)
    reviewed_by: str | None = Field(default=None, max_length=128)
    note: str | None = Field(default=None, max_length=2000)


class CollectionConfirmation(BaseModel):
    run_id: str = Field(min_length=1, max_length=128)
    class_name: str = Field(min_length=1, max_length=128)
    quantity: int = Field(default=1, ge=1, le=1_000_000)
    track_id: int | None = Field(default=None, ge=0)
    method: Literal["human", "arm_controller", "sensor_fusion", "import"]
    confirmed_by: str | None = Field(default=None, max_length=128)
    external_reference: str | None = Field(default=None, max_length=256)
    note: str | None = Field(default=None, max_length=2000)


class StreamStartRequest(BaseModel):
    source: str = Field(default="0", min_length=1, max_length=2048)
    edge_device_id: str | None = Field(default=None, max_length=128)
    vehicle_id: str | None = Field(default=None, max_length=128)
    route_id: str | None = Field(default=None, max_length=128)
    realtime: bool = True
    max_frames: int = Field(default=0, ge=0, le=10_000_000)
    persist_detections: bool = False


async def _read_limited_body(request: Any, maximum_bytes: int) -> bytes:
    declared_length = request.headers.get("content-length")
    if declared_length is not None:
        try:
            if int(declared_length) > maximum_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"Image exceeds the {maximum_bytes}-byte request limit."
                    ),
                )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="Content-Length must be an integer.",
            ) from exc

    chunks: list[bytes] = []
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > maximum_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Image exceeds the {maximum_bytes}-byte request limit.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def create_app() -> Any:
    holder = DetectorHolder()
    streams = StreamManager(
        detector=SerializedDetector(holder.backend, holder.predict_frame),
        backend=holder.backend,
        model=holder.model_reference,
        device=holder.device,
        settings=holder.settings,
        separation_policy=holder.separation_policy,
        database=holder.database,
        maximum_active_streams=int(os.environ.get("LITTER_MAX_STREAMS", "1")),
        maximum_retained_streams=int(
            os.environ.get("LITTER_MAX_RETAINED_STREAMS", "100")
        ),
    )

    @asynccontextmanager
    async def lifespan(_: Any) -> Any:
        try:
            yield
        finally:
            streams.close()

    api_docs_enabled = _enabled("LITTER_ENABLE_API_DOCS")
    app = FastAPI(
        title="Edge Litter Detection API",
        version=__version__,
        description="Detect, classify, and count litter in an image.",
        lifespan=lifespan,
        docs_url="/docs" if api_docs_enabled else None,
        redoc_url="/redoc" if api_docs_enabled else None,
        openapi_url="/openapi.json" if api_docs_enabled else None,
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        script_sources = "'self'"
        style_sources = "'self'"
        image_sources = "'self' data:"
        if api_docs_enabled:
            script_sources += " https://cdn.jsdelivr.net"
            style_sources += " 'unsafe-inline' https://cdn.jsdelivr.net"
            image_sources += " https://fastapi.tiangolo.com"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src {script_sources}; "
            f"style-src {style_sources}; "
            f"img-src {image_sources}; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'; "
            "form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        if request.url.path.startswith(("/v1/", "/healthz", "/readyz")):
            response.headers["Cache-Control"] = "no-store"
        return response

    dashboard_directory = Path(__file__).with_name("dashboard")
    app.mount(
        "/dashboard-assets",
        StaticFiles(directory=dashboard_directory),
        name="dashboard-assets",
    )

    @app.get("/", include_in_schema=False)
    def dashboard() -> Any:
        return FileResponse(dashboard_directory / "index.html")

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        stream_snapshots = streams.list()
        return {
            "status": "ok",
            "backend": holder.backend,
            "device": holder.device,
            "model_configured": holder.model_configured,
            "model_loaded": holder._detector is not None,
            "database": str(holder.database),
            "database_exists": holder.database.is_file(),
            "service_mode": "counts_api" if holder.counts_only else "detection_api",
            "active_stream_count": sum(
                1
                for stream in stream_snapshots
                if stream["status"] in {"created", "starting", "running", "stopping"}
            ),
            "dashboard": "/",
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
        media_type = request.headers.get("content-type", "").split(";", 1)[0]
        media_type = media_type.strip().lower()
        if media_type not in ALLOWED_IMAGE_MEDIA_TYPES:
            raise HTTPException(
                status_code=415,
                detail=(
                    "Content-Type must be image/jpeg, image/png, or image/webp."
                ),
            )
        image_bytes = await _read_limited_body(
            request,
            holder.maximum_image_bytes,
        )
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Request body is empty.")
        if not _matches_image_signature(media_type, image_bytes):
            raise HTTPException(
                status_code=400,
                detail="Request body does not match its declared image type.",
            )
        if not holder._image_request_slots.acquire(blocking=False):
            raise HTTPException(
                status_code=429,
                detail="The detector is busy. Retry after the current request.",
                headers={"Retry-After": "1"},
            )
        try:
            return await run_in_threadpool(holder.detect, image_bytes)
        except (FileNotFoundError, RuntimeError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            holder._image_request_slots.release()

    @app.post("/v1/streams")
    def start_stream(request: StreamStartRequest) -> dict[str, Any]:
        if holder.counts_only:
            raise HTTPException(
                status_code=503,
                detail="Live stream processing is disabled in counts-only mode.",
            )
        try:
            session = streams.start(
                source=request.source,
                edge_device_id=(
                    request.edge_device_id
                    or os.environ.get("LITTER_EDGE_DEVICE_ID", "edge-node")
                ),
                vehicle_id=(
                    request.vehicle_id
                    if request.vehicle_id is not None
                    else os.environ.get("LITTER_VEHICLE_ID") or None
                ),
                route_id=(
                    request.route_id
                    if request.route_id is not None
                    else os.environ.get("LITTER_ROUTE_ID") or None
                ),
                realtime=request.realtime,
                max_frames=request.max_frames,
                persist_detections=request.persist_detections,
            )
            return session.snapshot()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/v1/streams")
    def list_streams() -> dict[str, Any]:
        return {"streams": streams.list()}

    @app.get("/v1/streams/{session_id}")
    def stream_status(session_id: str) -> dict[str, Any]:
        try:
            return streams.get(session_id).snapshot()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/v1/streams/{session_id}/frame.jpg")
    def stream_frame(session_id: str) -> Any:
        try:
            frame = streams.get(session_id).latest_frame()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if frame is None:
            raise HTTPException(
                status_code=404,
                detail="The first annotated frame is not available yet.",
            )
        return Response(
            content=frame,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    @app.delete("/v1/streams/{session_id}")
    def stop_stream(session_id: str) -> dict[str, Any]:
        try:
            return streams.stop(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

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
