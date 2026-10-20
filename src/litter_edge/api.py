from __future__ import annotations

import os
from collections import Counter
from pathlib import Path
from threading import Lock
from typing import Any

from .adapters import create_detector
from .classes import load_class_names
from .device import resolve_torch_device
from .settings import load_settings

try:
    from fastapi import FastAPI, HTTPException, Request
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
        self.device = resolve_torch_device(
            os.environ.get("LITTER_DEVICE", str(self.settings.device))
        )
        self._detector: Any = None
        self._load_lock = Lock()
        self._predict_lock = Lock()

    @property
    def model_configured(self) -> bool:
        return Path(self.model_reference).is_file()

    def _get_detector(self) -> Any:
        if self._detector is not None:
            return self._detector
        with self._load_lock:
            if self._detector is None:
                self._detector = create_detector(
                    backend=self.backend,
                    model=self.model_reference,
                    class_names=load_class_names(self.class_names_path),
                    confidence=self.settings.confidence,
                    device=self.device,
                    optimize=True,
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


def create_app() -> Any:
    holder = DetectorHolder()
    app = FastAPI(
        title="Edge Litter Detection API",
        version="0.4.0",
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
        }

    @app.get("/readyz")
    def readyz() -> dict[str, Any]:
        if not holder.model_configured:
            raise HTTPException(
                status_code=503,
                detail="The trained litter checkpoint is not mounted.",
            )
        return {
            "status": "ready",
            "backend": holder.backend,
            "device": holder.device,
        }

    @app.post("/v1/detect")
    async def detect(request: Request) -> dict[str, Any]:
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

    return app


app = create_app()
