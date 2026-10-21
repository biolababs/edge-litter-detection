from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .common import utc_now
from .schema import FrameOutcome


SCHEMA_VERSION = 1
COMPLETED_STATUSES = ("completed", "interrupted")


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _open_database(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    return connection


class SQLiteObservationStore:
    """Offline-first storage for run, count, review, and integration records."""

    def __init__(
        self,
        path: str | Path,
        *,
        flush_frames: int = 15,
        persist_detections: bool = False,
    ) -> None:
        if flush_frames <= 0:
            raise ValueError("flush_frames must be positive.")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.flush_frames = flush_frames
        self.persist_detections = persist_detections
        self.connection = _open_database(self.path)
        self._pending_frames = 0
        self._run_metadata: dict[str, dict[str, Any]] = {}
        self._initialize()

    def _initialize(self) -> None:
        version = int(self.connection.execute("PRAGMA user_version").fetchone()[0])
        if version not in {0, SCHEMA_VERSION}:
            raise RuntimeError(
                f"Unsupported SQLite schema version {version}; "
                f"this software supports {SCHEMA_VERSION}."
            )
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL
                    CHECK (status IN ('running', 'completed', 'interrupted', 'failed')),
                source TEXT NOT NULL,
                backend TEXT NOT NULL,
                model TEXT NOT NULL,
                compute_device TEXT NOT NULL,
                edge_device_id TEXT NOT NULL,
                vehicle_id TEXT,
                route_id TEXT,
                frames INTEGER NOT NULL DEFAULT 0,
                wall_seconds REAL,
                source_to_result_fps REAL,
                mean_detector_call_ms REAL,
                events_output TEXT,
                summary_output TEXT,
                annotated_output TEXT,
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS frame_observations (
                run_id TEXT NOT NULL,
                frame_index INTEGER NOT NULL,
                timestamp_seconds REAL,
                recorded_at TEXT NOT NULL,
                inference_ms REAL NOT NULL,
                detection_count INTEGER NOT NULL,
                confirmed_detection_count INTEGER NOT NULL,
                visible_counts_json TEXT NOT NULL,
                confirmed_visible_counts_json TEXT NOT NULL,
                unique_detected_counts_json TEXT NOT NULL,
                PRIMARY KEY (run_id, frame_index),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS detections (
                run_id TEXT NOT NULL,
                frame_index INTEGER NOT NULL,
                detection_index INTEGER NOT NULL,
                track_id INTEGER,
                class_id INTEGER NOT NULL,
                class_name TEXT NOT NULL,
                confidence REAL NOT NULL,
                x1 REAL NOT NULL,
                y1 REAL NOT NULL,
                x2 REAL NOT NULL,
                y2 REAL NOT NULL,
                confirmed INTEGER NOT NULL,
                separation_destination TEXT,
                review_required INTEGER NOT NULL,
                PRIMARY KEY (run_id, frame_index, detection_index),
                FOREIGN KEY (run_id, frame_index)
                    REFERENCES frame_observations(run_id, frame_index)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS run_class_counts (
                run_id TEXT NOT NULL,
                class_name TEXT NOT NULL,
                peak_visible_count INTEGER NOT NULL,
                unique_detected_count INTEGER NOT NULL,
                PRIMARY KEY (run_id, class_name),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS review_queue (
                review_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                frame_index INTEGER NOT NULL,
                track_id INTEGER,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK (status IN ('pending', 'confirmed', 'corrected', 'rejected')),
                suggested_class_name TEXT NOT NULL,
                suggested_destination TEXT,
                confidence REAL NOT NULL,
                bbox_json TEXT NOT NULL,
                corrected_class_name TEXT,
                corrected_destination TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                note TEXT,
                UNIQUE (run_id, track_id),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS integration_outbox (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                acknowledged_at TEXT
            );

            CREATE TABLE IF NOT EXISTS collection_confirmations (
                confirmation_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                track_id INTEGER,
                confirmed_at TEXT NOT NULL,
                class_name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                method TEXT NOT NULL
                    CHECK (method IN (
                        'human', 'arm_controller', 'sensor_fusion', 'import'
                    )),
                confirmed_by TEXT,
                external_reference TEXT UNIQUE,
                note TEXT,
                UNIQUE (run_id, track_id),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_runs_vehicle_route
                ON runs(vehicle_id, route_id, started_at);
            CREATE INDEX IF NOT EXISTS idx_runs_device_started
                ON runs(edge_device_id, started_at);
            CREATE INDEX IF NOT EXISTS idx_review_status_created
                ON review_queue(status, created_at);
            CREATE INDEX IF NOT EXISTS idx_outbox_pending
                ON integration_outbox(acknowledged_at, created_at);
            CREATE INDEX IF NOT EXISTS idx_collection_run_class
                ON collection_confirmations(run_id, class_name);
            """
        )
        self.connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self.connection.commit()

    def start_run(
        self,
        *,
        run_id: str,
        started_at: str,
        source: str,
        backend: str,
        model: str,
        compute_device: str,
        edge_device_id: str,
        vehicle_id: str | None,
        route_id: str | None,
        events_output: str,
        summary_output: str,
        annotated_output: str | None,
    ) -> None:
        metadata = {
            "run_id": run_id,
            "edge_device_id": edge_device_id,
            "vehicle_id": vehicle_id,
            "route_id": route_id,
            "source": source,
        }
        self.connection.execute(
            """
            INSERT INTO runs (
                run_id, started_at, status, source, backend, model,
                compute_device, edge_device_id, vehicle_id, route_id,
                events_output, summary_output, annotated_output
            ) VALUES (?, ?, 'running', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                started_at,
                source,
                backend,
                model,
                compute_device,
                edge_device_id,
                vehicle_id,
                route_id,
                events_output,
                summary_output,
                annotated_output,
            ),
        )
        self._run_metadata[run_id] = metadata
        self.connection.commit()

    def record_frame(self, run_id: str, outcome: FrameOutcome) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO frame_observations (
                run_id, frame_index, timestamp_seconds, recorded_at,
                inference_ms, detection_count, confirmed_detection_count,
                visible_counts_json, confirmed_visible_counts_json,
                unique_detected_counts_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                outcome.frame_index,
                outcome.timestamp_seconds,
                utc_now(),
                outcome.inference_ms,
                len(outcome.detections),
                sum(1 for detection in outcome.detections if detection.confirmed),
                _json(outcome.visible_counts),
                _json(outcome.confirmed_visible_counts),
                _json(outcome.unique_session_counts),
            ),
        )

        if self.persist_detections:
            self.connection.execute(
                "DELETE FROM detections WHERE run_id = ? AND frame_index = ?",
                (run_id, outcome.frame_index),
            )
            self.connection.executemany(
                """
                INSERT INTO detections (
                    run_id, frame_index, detection_index, track_id, class_id,
                    class_name, confidence, x1, y1, x2, y2, confirmed,
                    separation_destination, review_required
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        outcome.frame_index,
                        index,
                        detection.track_id,
                        detection.class_id,
                        detection.class_name,
                        detection.confidence,
                        detection.x1,
                        detection.y1,
                        detection.x2,
                        detection.y2,
                        int(detection.confirmed),
                        detection.separation_destination,
                        int(detection.review_required),
                    )
                    for index, detection in enumerate(outcome.detections)
                ],
            )

        confirmed_track_ids = set(outcome.newly_confirmed_track_ids)
        for detection in outcome.detections:
            if detection.track_id in confirmed_track_ids:
                payload = self._object_event_payload(run_id, outcome, detection)
                self._enqueue_event(
                    event_type="litter.object.confirmed",
                    aggregate_id=f"{run_id}:{detection.track_id}",
                    payload=payload,
                )
            if (
                detection.confirmed
                and detection.track_id is not None
                and detection.review_required
            ):
                self.connection.execute(
                    """
                    INSERT OR IGNORE INTO review_queue (
                        review_id, run_id, frame_index, track_id, created_at,
                        status, suggested_class_name, suggested_destination,
                        confidence, bbox_json
                    ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        run_id,
                        outcome.frame_index,
                        detection.track_id,
                        utc_now(),
                        detection.class_name,
                        detection.separation_destination,
                        detection.confidence,
                        _json(list(detection.bbox)),
                    ),
                )

        self._pending_frames += 1
        if self._pending_frames >= self.flush_frames:
            self.connection.commit()
            self._pending_frames = 0

    def _object_event_payload(
        self,
        run_id: str,
        outcome: FrameOutcome,
        detection: Any,
    ) -> dict[str, Any]:
        metadata = self._run_metadata[run_id]
        return {
            "schema_version": "1.0",
            "event_type": "litter.object.confirmed",
            "run_id": run_id,
            "frame_index": outcome.frame_index,
            "timestamp_seconds": outcome.timestamp_seconds,
            "track_id": detection.track_id,
            "class_id": detection.class_id,
            "class_name": detection.class_name,
            "confidence": detection.confidence,
            "bbox_xyxy": list(detection.bbox),
            "separation_destination": detection.separation_destination,
            "review_required": detection.review_required,
            "edge_device_id": metadata["edge_device_id"],
            "vehicle_id": metadata["vehicle_id"],
            "route_id": metadata["route_id"],
            "source": metadata["source"],
            "created_at": utc_now(),
            "meaning": "detected_object_candidate_not_collection_confirmation",
        }

    def _enqueue_event(
        self,
        *,
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
    ) -> str:
        event_id = str(uuid.uuid4())
        payload = {"event_id": event_id, **payload}
        self.connection.execute(
            """
            INSERT INTO integration_outbox (
                event_id, event_type, aggregate_id, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (event_id, event_type, aggregate_id, _json(payload), utc_now()),
        )
        return event_id

    def finish_run(
        self,
        *,
        run_id: str,
        completed_at: str,
        status: str,
        frames: int,
        wall_seconds: float,
        source_to_result_fps: float | None,
        mean_detector_call_ms: float | None,
        peak_visible_counts: dict[str, int],
        unique_detected_counts: dict[str, int],
    ) -> None:
        if status not in COMPLETED_STATUSES:
            raise ValueError(f"Invalid completed run status: {status}")
        self.connection.execute(
            """
            UPDATE runs
            SET completed_at = ?, status = ?, frames = ?, wall_seconds = ?,
                source_to_result_fps = ?, mean_detector_call_ms = ?
            WHERE run_id = ?
            """,
            (
                completed_at,
                status,
                frames,
                wall_seconds,
                source_to_result_fps,
                mean_detector_call_ms,
                run_id,
            ),
        )
        self.connection.execute(
            "DELETE FROM run_class_counts WHERE run_id = ?",
            (run_id,),
        )
        class_names = sorted(set(peak_visible_counts) | set(unique_detected_counts))
        self.connection.executemany(
            """
            INSERT INTO run_class_counts (
                run_id, class_name, peak_visible_count, unique_detected_count
            ) VALUES (?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    class_name,
                    int(peak_visible_counts.get(class_name, 0)),
                    int(unique_detected_counts.get(class_name, 0)),
                )
                for class_name in class_names
            ],
        )
        metadata = self._run_metadata.get(run_id, {})
        self._enqueue_event(
            event_type="litter.run.completed",
            aggregate_id=run_id,
            payload={
                "schema_version": "1.0",
                "event_type": "litter.run.completed",
                "run_id": run_id,
                "status": status,
                "completed_at": completed_at,
                "frames": frames,
                "peak_visible_counts": peak_visible_counts,
                "unique_detected_counts": unique_detected_counts,
                "edge_device_id": metadata.get("edge_device_id"),
                "vehicle_id": metadata.get("vehicle_id"),
                "route_id": metadata.get("route_id"),
                "meaning": "observed_litter_not_confirmed_collected_material",
            },
        )
        self.connection.commit()
        self._pending_frames = 0

    def fail_run(self, run_id: str, error_message: str) -> None:
        self.connection.execute(
            """
            UPDATE runs
            SET completed_at = ?, status = 'failed', error_message = ?
            WHERE run_id = ?
            """,
            (utc_now(), error_message[:2000], run_id),
        )
        self.connection.commit()
        self._pending_frames = 0

    def close(self) -> None:
        self.connection.commit()
        self.connection.close()


def _read_connection(path: str | Path) -> sqlite3.Connection | None:
    database = Path(path)
    if not database.is_file():
        return None
    connection = sqlite3.connect(str(database), timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def _run_filters(
    *,
    status_clause: str,
    vehicle_id: str | None,
    route_id: str | None,
    edge_device_id: str | None,
) -> tuple[str, list[Any]]:
    clauses = [status_clause]
    values: list[Any] = []
    for column, value in (
        ("vehicle_id", vehicle_id),
        ("route_id", route_id),
        ("edge_device_id", edge_device_id),
    ):
        if value is not None:
            clauses.append(f"r.{column} = ?")
            values.append(value)
    return " AND ".join(clauses), values


def summarize_counts(
    path: str | Path,
    *,
    vehicle_id: str | None = None,
    route_id: str | None = None,
    edge_device_id: str | None = None,
) -> dict[str, Any]:
    connection = _read_connection(path)
    filters = {
        "vehicle_id": vehicle_id,
        "route_id": route_id,
        "edge_device_id": edge_device_id,
    }
    if connection is None:
        return {
            "database": str(path),
            "database_exists": False,
            "filters": filters,
            "run_count": 0,
            "frame_count": 0,
            "active_run_count": 0,
            "current_visible_counts": {},
            "active_unique_detected_counts": {},
            "run_unique_detected_counts": {},
            "maximum_simultaneously_visible": {},
            "confirmed_collected_counts": {},
            "count_scope": "observed_litter_not_confirmed_collected_material",
        }

    where, values = _run_filters(
        status_clause="r.status IN ('completed', 'interrupted')",
        vehicle_id=vehicle_id,
        route_id=route_id,
        edge_device_id=edge_device_id,
    )
    active_where, active_values = _run_filters(
        status_clause="r.status = 'running'",
        vehicle_id=vehicle_id,
        route_id=route_id,
        edge_device_id=edge_device_id,
    )
    collection_where, collection_values = _run_filters(
        status_clause="r.status IN ('running', 'completed', 'interrupted')",
        vehicle_id=vehicle_id,
        route_id=route_id,
        edge_device_id=edge_device_id,
    )
    try:
        run_row = connection.execute(
            f"""
            SELECT COUNT(*) AS run_count,
                   COALESCE(SUM(r.frames), 0) AS frame_count,
                   MIN(r.started_at) AS first_started_at,
                   MAX(r.completed_at) AS last_completed_at
            FROM runs r
            WHERE {where}
            """,
            values,
        ).fetchone()
        class_rows = connection.execute(
            f"""
            SELECT c.class_name,
                   COALESCE(SUM(c.unique_detected_count), 0)
                       AS run_unique_detected_count,
                   COALESCE(MAX(c.peak_visible_count), 0)
                       AS maximum_simultaneously_visible
            FROM run_class_counts c
            JOIN runs r ON r.run_id = c.run_id
            WHERE {where}
            GROUP BY c.class_name
            ORDER BY c.class_name
            """,
            values,
        ).fetchall()
        active_rows = connection.execute(
            f"""
            SELECT fo.visible_counts_json, fo.unique_detected_counts_json
            FROM runs r
            JOIN frame_observations fo ON fo.run_id = r.run_id
            WHERE {active_where}
              AND fo.frame_index = (
                  SELECT MAX(latest.frame_index)
                  FROM frame_observations latest
                  WHERE latest.run_id = r.run_id
              )
            """,
            active_values,
        ).fetchall()
        collected_rows = connection.execute(
            f"""
            SELECT c.class_name, COALESCE(SUM(c.quantity), 0) AS quantity
            FROM collection_confirmations c
            JOIN runs r ON r.run_id = c.run_id
            WHERE {collection_where}
            GROUP BY c.class_name
            ORDER BY c.class_name
            """,
            collection_values,
        ).fetchall()
        current_visible: dict[str, int] = {}
        active_unique: dict[str, int] = {}
        for row in active_rows:
            for class_name, count in json.loads(
                row["visible_counts_json"]
            ).items():
                current_visible[class_name] = (
                    current_visible.get(class_name, 0) + int(count)
                )
            for class_name, count in json.loads(
                row["unique_detected_counts_json"]
            ).items():
                active_unique[class_name] = (
                    active_unique.get(class_name, 0) + int(count)
                )
        return {
            "database": str(path),
            "database_exists": True,
            "filters": filters,
            "run_count": int(run_row["run_count"]),
            "frame_count": int(run_row["frame_count"]),
            "active_run_count": len(active_rows),
            "current_visible_counts": dict(sorted(current_visible.items())),
            "active_unique_detected_counts": dict(sorted(active_unique.items())),
            "first_started_at": run_row["first_started_at"],
            "last_completed_at": run_row["last_completed_at"],
            "run_unique_detected_counts": {
                row["class_name"]: int(row["run_unique_detected_count"])
                for row in class_rows
            },
            "maximum_simultaneously_visible": {
                row["class_name"]: int(row["maximum_simultaneously_visible"])
                for row in class_rows
            },
            "confirmed_collected_counts": {
                row["class_name"]: int(row["quantity"])
                for row in collected_rows
            },
            "count_scope": "observed_litter_not_confirmed_collected_material",
            "deduplication_warning": (
                "Unique counts are summed across run boundaries and may include "
                "the same physical object in more than one run."
            ),
        }
    finally:
        connection.close()


def list_runs(
    path: str | Path,
    *,
    limit: int = 50,
    vehicle_id: str | None = None,
    route_id: str | None = None,
    edge_device_id: str | None = None,
) -> list[dict[str, Any]]:
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000.")
    connection = _read_connection(path)
    if connection is None:
        return []
    clauses = ["1 = 1"]
    values: list[Any] = []
    for column, value in (
        ("vehicle_id", vehicle_id),
        ("route_id", route_id),
        ("edge_device_id", edge_device_id),
    ):
        if value is not None:
            clauses.append(f"{column} = ?")
            values.append(value)
    values.append(limit)
    try:
        rows = connection.execute(
            f"""
            SELECT run_id, started_at, completed_at, status, source,
                   edge_device_id, vehicle_id, route_id, frames,
                   source_to_result_fps
            FROM runs
            WHERE {' AND '.join(clauses)}
            ORDER BY started_at DESC
            LIMIT ?
            """,
            values,
        ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            counts = connection.execute(
                """
                SELECT class_name, unique_detected_count
                FROM run_class_counts
                WHERE run_id = ?
                ORDER BY class_name
                """,
                (row["run_id"],),
            ).fetchall()
            collected = connection.execute(
                """
                SELECT class_name, SUM(quantity) AS quantity
                FROM collection_confirmations
                WHERE run_id = ?
                GROUP BY class_name
                ORDER BY class_name
                """,
                (row["run_id"],),
            ).fetchall()
            payload = dict(row)
            payload["unique_detected_counts"] = {
                count["class_name"]: int(count["unique_detected_count"])
                for count in counts
            }
            payload["confirmed_collected_counts"] = {
                count["class_name"]: int(count["quantity"])
                for count in collected
            }
            results.append(payload)
        return results
    finally:
        connection.close()


def list_review_queue(
    path: str | Path,
    *,
    status: str = "pending",
    limit: int = 50,
) -> list[dict[str, Any]]:
    if status not in {"pending", "confirmed", "corrected", "rejected"}:
        raise ValueError("Unsupported review status.")
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000.")
    connection = _read_connection(path)
    if connection is None:
        return []
    try:
        rows = connection.execute(
            """
            SELECT review_id, run_id, frame_index, track_id, created_at, status,
                   suggested_class_name, suggested_destination, confidence,
                   bbox_json, corrected_class_name, corrected_destination,
                   reviewed_by, reviewed_at, note
            FROM review_queue
            WHERE status = ?
            ORDER BY created_at
            LIMIT ?
            """,
            (status, limit),
        ).fetchall()
        output = []
        for row in rows:
            payload = dict(row)
            payload["bbox_xyxy"] = json.loads(payload.pop("bbox_json"))
            output.append(payload)
        return output
    finally:
        connection.close()


def update_review(
    path: str | Path,
    *,
    review_id: str,
    status: str,
    corrected_class_name: str | None = None,
    corrected_destination: str | None = None,
    reviewed_by: str | None = None,
    note: str | None = None,
) -> bool:
    if status not in {"confirmed", "corrected", "rejected"}:
        raise ValueError("Review status must be confirmed, corrected, or rejected.")
    if status == "corrected" and not corrected_class_name:
        raise ValueError("A corrected review requires corrected_class_name.")
    connection = _read_connection(path)
    if connection is None:
        return False
    try:
        existing = connection.execute(
            """
            SELECT review_id, run_id, frame_index, track_id, status,
                   suggested_class_name, suggested_destination
            FROM review_queue
            WHERE review_id = ?
            """,
            (review_id,),
        ).fetchone()
        if existing is None:
            return False
        if existing["status"] != "pending":
            raise ValueError("This review item has already been completed.")
        cursor = connection.execute(
            """
            UPDATE review_queue
            SET status = ?, corrected_class_name = ?,
                corrected_destination = ?, reviewed_by = ?,
                reviewed_at = ?, note = ?
            WHERE review_id = ? AND status = 'pending'
            """,
            (
                status,
                corrected_class_name,
                corrected_destination,
                reviewed_by,
                utc_now(),
                note,
                review_id,
            ),
        )
        if cursor.rowcount != 1:
            raise ValueError("This review item has already been completed.")
        event_id = str(uuid.uuid4())
        connection.execute(
            """
            INSERT INTO integration_outbox (
                event_id, event_type, aggregate_id, payload_json, created_at
            ) VALUES (?, 'litter.review.completed', ?, ?, ?)
            """,
            (
                event_id,
                review_id,
                _json(
                    {
                        "event_id": event_id,
                        "schema_version": "1.0",
                        "event_type": "litter.review.completed",
                        "review_id": review_id,
                        "run_id": existing["run_id"],
                        "frame_index": existing["frame_index"],
                        "track_id": existing["track_id"],
                        "status": status,
                        "suggested_class_name": existing["suggested_class_name"],
                        "suggested_destination": existing[
                            "suggested_destination"
                        ],
                        "corrected_class_name": corrected_class_name,
                        "corrected_destination": corrected_destination,
                        "reviewed_by": reviewed_by,
                        "meaning": (
                            "human_reviewed_classification_not_collection_confirmation"
                        ),
                    }
                ),
                utc_now(),
            ),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def list_outbox_events(
    path: str | Path,
    *,
    limit: int = 100,
    include_acknowledged: bool = False,
) -> list[dict[str, Any]]:
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000.")
    connection = _read_connection(path)
    if connection is None:
        return []
    where = "" if include_acknowledged else "WHERE acknowledged_at IS NULL"
    try:
        rows = connection.execute(
            f"""
            SELECT event_id, event_type, aggregate_id, payload_json,
                   created_at, acknowledged_at
            FROM integration_outbox
            {where}
            ORDER BY created_at
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        output = []
        for row in rows:
            payload = dict(row)
            payload["payload"] = json.loads(payload.pop("payload_json"))
            output.append(payload)
        return output
    finally:
        connection.close()


def acknowledge_outbox_event(path: str | Path, event_id: str) -> bool:
    connection = _read_connection(path)
    if connection is None:
        return False
    try:
        cursor = connection.execute(
            """
            UPDATE integration_outbox
            SET acknowledged_at = ?
            WHERE event_id = ? AND acknowledged_at IS NULL
            """,
            (utc_now(), event_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def confirm_collection(
    path: str | Path,
    *,
    run_id: str,
    class_name: str,
    quantity: int = 1,
    track_id: int | None = None,
    method: str,
    confirmed_by: str | None = None,
    external_reference: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    if quantity <= 0:
        raise ValueError("Collection quantity must be positive.")
    if method not in {"human", "arm_controller", "sensor_fusion", "import"}:
        raise ValueError(
            "Collection method must be human, arm_controller, sensor_fusion, or import."
        )
    if not class_name.strip():
        raise ValueError("Collection class_name cannot be empty.")
    connection = _read_connection(path)
    if connection is None:
        raise FileNotFoundError(f"Observation database not found: {path}")
    try:
        run = connection.execute(
            """
            SELECT edge_device_id, vehicle_id, route_id
            FROM runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if run is None:
            raise ValueError(f"Unknown run_id: {run_id}")
        confirmation_id = str(uuid.uuid4())
        confirmed_at = utc_now()
        try:
            connection.execute(
                """
                INSERT INTO collection_confirmations (
                    confirmation_id, run_id, track_id, confirmed_at,
                    class_name, quantity, method, confirmed_by,
                    external_reference, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    confirmation_id,
                    run_id,
                    track_id,
                    confirmed_at,
                    class_name,
                    quantity,
                    method,
                    confirmed_by,
                    external_reference,
                    note,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "This collection confirmation or external reference already exists."
            ) from exc
        event_id = str(uuid.uuid4())
        payload = {
            "event_id": event_id,
            "schema_version": "1.0",
            "event_type": "litter.collection.confirmed",
            "confirmation_id": confirmation_id,
            "run_id": run_id,
            "track_id": track_id,
            "class_name": class_name,
            "quantity": quantity,
            "method": method,
            "confirmed_by": confirmed_by,
            "external_reference": external_reference,
            "confirmed_at": confirmed_at,
            "edge_device_id": run["edge_device_id"],
            "vehicle_id": run["vehicle_id"],
            "route_id": run["route_id"],
            "meaning": "externally_confirmed_collected_material",
        }
        connection.execute(
            """
            INSERT INTO integration_outbox (
                event_id, event_type, aggregate_id, payload_json, created_at
            ) VALUES (?, 'litter.collection.confirmed', ?, ?, ?)
            """,
            (
                event_id,
                confirmation_id,
                _json(payload),
                confirmed_at,
            ),
        )
        connection.commit()
        return payload
    finally:
        connection.close()
