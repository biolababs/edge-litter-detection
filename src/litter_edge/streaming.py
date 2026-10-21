from __future__ import annotations

import threading
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.parse import urlsplit

from .common import utc_now
from .pipeline import Detector, LitterPipeline
from .runtime import _annotate, _safe_source_label, _source_value
from .settings import ProjectSettings
from .sorting import SeparationPolicy
from .storage import SQLiteObservationStore
from .tracking import ClassStabilizedIoUTracker


ALLOWED_STREAM_SCHEMES = {"http", "https", "rtsp", "rtsps"}


class Capture(Protocol):
    def isOpened(self) -> bool:
        ...

    def read(self) -> tuple[bool, Any]:
        ...

    def get(self, property_id: int) -> float:
        ...

    def release(self) -> None:
        ...


def validate_stream_source(source: str) -> str:
    value = source.strip()
    if not value:
        raise ValueError("Stream source cannot be empty.")
    if any(ord(character) < 32 for character in value):
        raise ValueError("Stream source contains control characters.")
    if "://" in value:
        scheme = urlsplit(value).scheme.lower()
        if scheme not in ALLOWED_STREAM_SCHEMES:
            raise ValueError(
                "Stream URL must use http, https, rtsp, or rtsps."
            )
    return value


def _default_capture_factory(source: str | int) -> Capture:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "OpenCV is required for live streams. Install the runtime "
            "dependency."
        ) from exc
    return cv2.VideoCapture(source)


def _default_renderer(frame: Any, outcome: Any) -> bytes:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "OpenCV is required to render dashboard frames."
        ) from exc
    annotated = _annotate(frame, outcome)
    ok, encoded = cv2.imencode(
        ".jpg",
        annotated,
        [int(cv2.IMWRITE_JPEG_QUALITY), 82],
    )
    if not ok:
        raise RuntimeError("Unable to encode the annotated dashboard frame.")
    return bytes(encoded)


class SerializedDetector:
    """Adapts a synchronized prediction callback to the detector protocol."""

    def __init__(
        self,
        backend_name: str,
        predict: Callable[[Any], list[Any]],
    ) -> None:
        self.backend_name = backend_name
        self._predict = predict

    def predict(self, frame_bgr: Any) -> list[Any]:
        return self._predict(frame_bgr)


class StreamSession:
    """Runs one camera, video, or network stream through the full pipeline."""

    def __init__(
        self,
        *,
        source: str,
        detector: Detector,
        backend: str,
        model: str,
        device: str,
        settings: ProjectSettings,
        separation_policy: SeparationPolicy,
        database: str | Path,
        edge_device_id: str,
        vehicle_id: str | None,
        route_id: str | None,
        realtime: bool = True,
        max_frames: int = 0,
        persist_detections: bool = False,
        capture_factory: Callable[[str | int], Capture] = _default_capture_factory,
        renderer: Callable[[Any, Any], bytes] = _default_renderer,
    ) -> None:
        if max_frames < 0:
            raise ValueError("max_frames cannot be negative.")
        if not edge_device_id.strip():
            raise ValueError("edge_device_id cannot be empty.")
        self.session_id = str(uuid.uuid4())
        self.run_id = self.session_id
        self.source = validate_stream_source(source)
        self.source_value = _source_value(self.source)
        self.source_label = _safe_source_label(self.source_value)
        self.detector = detector
        self.backend = backend
        self.model = model
        self.device = device
        self.settings = settings
        self.separation_policy = separation_policy
        self.database = Path(database)
        self.edge_device_id = edge_device_id.strip()
        self.vehicle_id = vehicle_id.strip() if vehicle_id else None
        self.route_id = route_id.strip() if route_id else None
        self.realtime = realtime
        self.max_frames = max_frames
        self.persist_detections = persist_detections
        self.capture_factory = capture_factory
        self.renderer = renderer

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._capture: Capture | None = None
        self._store: SQLiteObservationStore | None = None
        self._status = "created"
        self._error: str | None = None
        self._latest_frame: bytes | None = None
        self._latest_outcome: dict[str, Any] | None = None
        self._frame_count = 0
        self._source_fps = 0.0
        self._peak_visible: Counter[str] = Counter()
        self._final_unique: dict[str, int] = {}
        self._inference_times: list[float] = []
        self._started_at: str | None = None
        self._completed_at: str | None = None
        self._wall_seconds: float | None = None

    @property
    def active(self) -> bool:
        with self._lock:
            return self._status in {
                "created",
                "starting",
                "running",
                "stopping",
            }

    def start(self) -> None:
        with self._lock:
            if self._status != "created":
                raise RuntimeError("Stream session has already been started.")
            self._status = "starting"
            self._started_at = utc_now()

        self._thread = threading.Thread(
            target=self._run,
            name=f"litter-stream-{self.session_id[:8]}",
            daemon=True,
        )
        self._thread.start()

    def _tracker(self) -> ClassStabilizedIoUTracker | None:
        if not self.settings.tracking_enabled:
            return None
        return ClassStabilizedIoUTracker(
            iou_threshold=self.settings.tracking_iou_threshold,
            max_missed_frames=self.settings.tracking_max_missed_frames,
            min_confirmed_hits=self.settings.tracking_min_confirmed_hits,
            class_mismatch_penalty=self.settings.tracking_class_mismatch_penalty,
        )

    def _error_message(self, error: Exception) -> str:
        message = str(error)
        if isinstance(self.source_value, str):
            message = message.replace(self.source_value, self.source_label)
        return message

    def _run(self) -> None:
        started = time.perf_counter()
        completed_status = "completed"
        run_started = False
        try:
            self._store = SQLiteObservationStore(
                self.database,
                flush_frames=self.settings.storage_flush_frames,
                persist_detections=self.persist_detections,
            )
            if self._started_at is None:
                raise RuntimeError("Stream session has no start timestamp.")
            self._store.start_run(
                run_id=self.run_id,
                started_at=self._started_at,
                source=self.source_label,
                backend=self.backend,
                model=self.model,
                compute_device=self.device,
                edge_device_id=self.edge_device_id,
                vehicle_id=self.vehicle_id,
                route_id=self.route_id,
                events_output=f"dashboard://streams/{self.session_id}/events",
                summary_output=f"dashboard://streams/{self.session_id}",
                annotated_output=None,
            )
            run_started = True
            capture = self.capture_factory(self.source_value)
            self._capture = capture
            if not capture.isOpened():
                raise RuntimeError(
                    f"Unable to open media source: {self.source_label}"
                )
            source_fps = float(capture.get(5) or 0.0)
            with self._lock:
                self._status = "running"
                self._source_fps = source_fps

            pipeline = LitterPipeline(
                detector=self.detector,
                tracker=self._tracker(),
                separation_policy=self.separation_policy,
            )
            media_started = time.perf_counter()
            while not self._stop_event.is_set():
                ok, frame = capture.read()
                if not ok:
                    break
                frame_index = self._frame_count + 1
                timestamp_msec = float(capture.get(0) or 0.0)
                timestamp = timestamp_msec / 1000.0 if timestamp_msec >= 0 else None
                outcome = pipeline.process(frame, frame_index, timestamp)
                if self._store is None:
                    raise RuntimeError("Stream observation store is unavailable.")
                self._store.record_frame(self.run_id, outcome)
                rendered = self.renderer(frame, outcome)

                for name, count in outcome.visible_counts.items():
                    self._peak_visible[name] = max(
                        self._peak_visible[name],
                        count,
                    )
                self._final_unique = outcome.unique_session_counts
                self._inference_times.append(outcome.inference_ms)
                with self._lock:
                    self._frame_count = frame_index
                    self._latest_outcome = outcome.to_dict()
                    self._latest_frame = rendered

                if self.max_frames and frame_index >= self.max_frames:
                    break
                if self.realtime and source_fps > 0:
                    expected_elapsed = frame_index / source_fps
                    remaining = expected_elapsed - (
                        time.perf_counter() - media_started
                    )
                    if remaining > 0:
                        self._stop_event.wait(remaining)

            if self._stop_event.is_set():
                completed_status = "interrupted"
            elif self._frame_count == 0:
                raise RuntimeError(
                    f"No frames were read from media source: {self.source_label}"
                )
        except Exception as exc:
            error_message = self._error_message(exc)
            with self._lock:
                self._status = "failed"
                self._error = error_message
                self._completed_at = utc_now()
                self._wall_seconds = time.perf_counter() - started
            if self._store is not None:
                if run_started:
                    self._store.fail_run(self.run_id, error_message)
                self._store.close()
                self._store = None
            return
        finally:
            capture = self._capture
            if capture is not None:
                capture.release()
            self._capture = None

        completed_at = utc_now()
        wall_seconds = time.perf_counter() - started
        mean_inference = (
            sum(self._inference_times) / len(self._inference_times)
            if self._inference_times
            else None
        )
        try:
            if self._store is None:
                raise RuntimeError("Stream observation store is unavailable.")
            self._store.finish_run(
                run_id=self.run_id,
                completed_at=completed_at,
                status=completed_status,
                frames=self._frame_count,
                wall_seconds=wall_seconds,
                source_to_result_fps=(
                    self._frame_count / wall_seconds
                    if wall_seconds > 0
                    else None
                ),
                mean_detector_call_ms=mean_inference,
                peak_visible_counts=dict(self._peak_visible),
                unique_detected_counts=self._final_unique,
            )
        except Exception as exc:
            error_message = self._error_message(exc)
            with self._lock:
                self._status = "failed"
                self._error = error_message
                self._completed_at = completed_at
                self._wall_seconds = wall_seconds
            if self._store is not None:
                try:
                    self._store.fail_run(self.run_id, error_message)
                finally:
                    self._store.close()
                    self._store = None
            return
        self._store.close()
        self._store = None
        with self._lock:
            self._status = completed_status
            self._completed_at = completed_at
            self._wall_seconds = wall_seconds

    def stop(self, timeout: float = 10.0) -> dict[str, Any]:
        with self._lock:
            if self._status in {"starting", "running"}:
                self._status = "stopping"
            self._stop_event.set()
            capture = self._capture
        if capture is not None:
            capture.release()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
        return self.snapshot()

    def wait(self, timeout: float | None = None) -> bool:
        thread = self._thread
        if thread is None:
            return True
        thread.join(timeout=timeout)
        return not thread.is_alive()

    def close(self) -> None:
        self.stop()

    def latest_frame(self) -> bytes | None:
        with self._lock:
            return self._latest_frame

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            wall_seconds = self._wall_seconds
            return {
                "session_id": self.session_id,
                "run_id": self.run_id,
                "status": self._status,
                "source": self.source_label,
                "backend": self.backend,
                "model": self.model,
                "device": self.device,
                "edge_device_id": self.edge_device_id,
                "vehicle_id": self.vehicle_id,
                "route_id": self.route_id,
                "frames": self._frame_count,
                "source_fps": self._source_fps,
                "source_to_result_fps": (
                    self._frame_count / wall_seconds
                    if wall_seconds and wall_seconds > 0
                    else None
                ),
                "started_at": self._started_at,
                "completed_at": self._completed_at,
                "error": self._error,
                "latest_outcome": self._latest_outcome,
                "frame_available": self._latest_frame is not None,
                "database": str(self.database),
            }


class StreamManager:
    def __init__(
        self,
        *,
        detector: Detector,
        backend: str,
        model: str,
        device: str,
        settings: ProjectSettings,
        separation_policy: SeparationPolicy,
        database: str | Path,
        maximum_active_streams: int = 1,
        maximum_retained_streams: int = 100,
    ) -> None:
        if maximum_active_streams <= 0:
            raise ValueError("maximum_active_streams must be positive.")
        if maximum_retained_streams < maximum_active_streams:
            raise ValueError(
                "maximum_retained_streams must be at least "
                "maximum_active_streams."
            )
        self.detector = detector
        self.backend = backend
        self.model = model
        self.device = device
        self.settings = settings
        self.separation_policy = separation_policy
        self.database = Path(database)
        self.maximum_active_streams = maximum_active_streams
        self.maximum_retained_streams = maximum_retained_streams
        self._lock = threading.Lock()
        self._sessions: dict[str, StreamSession] = {}

    def _prune_finished_locked(self) -> None:
        finished = [
            session_id
            for session_id, session in self._sessions.items()
            if not session.active
        ]
        while (
            len(self._sessions) >= self.maximum_retained_streams
            and finished
        ):
            self._sessions.pop(finished.pop(0), None)

    def start(
        self,
        *,
        source: str,
        edge_device_id: str,
        vehicle_id: str | None = None,
        route_id: str | None = None,
        realtime: bool = True,
        max_frames: int = 0,
        persist_detections: bool = False,
    ) -> StreamSession:
        with self._lock:
            active_count = sum(
                1 for session in self._sessions.values() if session.active
            )
            if active_count >= self.maximum_active_streams:
                raise RuntimeError(
                    "The edge device is already processing the maximum "
                    "number of live streams."
                )
            self._prune_finished_locked()
            session = StreamSession(
                source=source,
                detector=self.detector,
                backend=self.backend,
                model=self.model,
                device=self.device,
                settings=self.settings,
                separation_policy=self.separation_policy,
                database=self.database,
                edge_device_id=edge_device_id,
                vehicle_id=vehicle_id,
                route_id=route_id,
                realtime=realtime,
                max_frames=max_frames,
                persist_detections=persist_detections,
            )
            self._sessions[session.session_id] = session
        try:
            session.start()
        except Exception:
            with self._lock:
                self._sessions.pop(session.session_id, None)
            raise
        return session

    def get(self, session_id: str) -> StreamSession:
        with self._lock:
            try:
                return self._sessions[session_id]
            except KeyError as exc:
                raise KeyError("Stream session not found.") from exc

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            sessions = list(self._sessions.values())
        return [session.snapshot() for session in reversed(sessions)]

    def stop(self, session_id: str) -> dict[str, Any]:
        return self.get(session_id).stop()

    def close(self) -> None:
        with self._lock:
            sessions = list(self._sessions.values())
        for session in sessions:
            session.close()
