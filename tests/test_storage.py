from __future__ import annotations

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from litter_edge.schema import Detection, FrameOutcome
from litter_edge.storage import (
    SQLiteObservationStore,
    acknowledge_outbox_event,
    confirm_collection,
    list_outbox_events,
    list_review_queue,
    list_runs,
    summarize_counts,
    update_review,
)


def outcome(
    *,
    frame_index: int = 1,
    review_required: bool = True,
    newly_confirmed_track_ids: tuple[int, ...] = (7,),
) -> FrameOutcome:
    detection = Detection(
        10,
        20,
        40,
        60,
        confidence=0.48,
        class_id=3,
        class_name="plastic",
        track_id=7,
        confirmed=True,
        separation_destination="plastic_stream",
        review_required=review_required,
    )
    return FrameOutcome(
        frame_index=frame_index,
        timestamp_seconds=0.0,
        detections=(detection,),
        visible_counts={"plastic": 1},
        confirmed_visible_counts={"plastic": 1},
        unique_session_counts={"plastic": 1},
        newly_confirmed_track_ids=newly_confirmed_track_ids,
        inference_ms=12.5,
    )


class SQLiteObservationStoreTests(unittest.TestCase):
    def test_persists_counts_review_and_integration_events(self) -> None:
        with TemporaryDirectory() as temporary:
            database = Path(temporary) / "observations.db"
            store = SQLiteObservationStore(database, flush_frames=1)
            store.start_run(
                run_id="run-1",
                started_at="2026-10-21T00:00:00+00:00",
                source="0",
                backend="rfdetr",
                model="model.pth",
                compute_device="cpu",
                edge_device_id="edge-01",
                vehicle_id="truck-12",
                route_id="route-a",
                events_output="events.jsonl",
                summary_output="summary.json",
                annotated_output=None,
            )
            store.record_frame("run-1", outcome())
            active_summary = summarize_counts(database)
            self.assertEqual(active_summary["active_run_count"], 1)
            self.assertEqual(
                active_summary["active_unique_detected_counts"],
                {"plastic": 1},
            )

            collection = confirm_collection(
                database,
                run_id="run-1",
                track_id=7,
                class_name="plastic",
                method="human",
                confirmed_by="operator-1",
                external_reference="pickup-0001",
            )
            self.assertEqual(
                collection["meaning"],
                "externally_confirmed_collected_material",
            )
            self.assertEqual(
                summarize_counts(database)["confirmed_collected_counts"],
                {"plastic": 1},
            )
            store.finish_run(
                run_id="run-1",
                completed_at="2026-10-21T00:01:00+00:00",
                status="completed",
                frames=1,
                wall_seconds=1.0,
                source_to_result_fps=1.0,
                mean_detector_call_ms=12.5,
                peak_visible_counts={"plastic": 1},
                unique_detected_counts={"plastic": 1},
            )
            store.close()

            summary = summarize_counts(
                database,
                vehicle_id="truck-12",
                route_id="route-a",
            )
            runs = list_runs(database)
            reviews = list_review_queue(database)
            events = list_outbox_events(database)

            self.assertEqual(summary["run_unique_detected_counts"], {"plastic": 1})
            self.assertEqual(summary["frame_count"], 1)
            self.assertEqual(runs[0]["vehicle_id"], "truck-12")
            self.assertEqual(
                runs[0]["confirmed_collected_counts"],
                {"plastic": 1},
            )
            self.assertEqual(len(reviews), 1)
            self.assertEqual(reviews[0]["suggested_destination"], "plastic_stream")
            self.assertEqual(
                {event["event_type"] for event in events},
                {
                    "litter.object.confirmed",
                    "litter.collection.confirmed",
                    "litter.run.completed",
                },
            )

            self.assertTrue(
                update_review(
                    database,
                    review_id=reviews[0]["review_id"],
                    status="corrected",
                    corrected_class_name="other_litter",
                    corrected_destination="manual_sort",
                    reviewed_by="operator-1",
                )
            )
            self.assertEqual(len(list_review_queue(database, status="corrected")), 1)
            updated_summary = summarize_counts(database)
            self.assertEqual(
                updated_summary["confirmed_collected_counts"],
                {"plastic": 1},
            )
            with self.assertRaisesRegex(ValueError, "already exists"):
                confirm_collection(
                    database,
                    run_id="run-1",
                    track_id=7,
                    class_name="plastic",
                    method="arm_controller",
                    external_reference="pickup-0002",
                )
            self.assertTrue(acknowledge_outbox_event(database, events[0]["event_id"]))
            self.assertEqual(len(list_outbox_events(database)), 3)

    def test_detection_rows_are_opt_in(self) -> None:
        with TemporaryDirectory() as temporary:
            database = Path(temporary) / "observations.db"
            store = SQLiteObservationStore(database, persist_detections=False)
            store.start_run(
                run_id="run-2",
                started_at="2026-10-21T00:00:00+00:00",
                source="video.mp4",
                backend="rfdetr",
                model="model.pth",
                compute_device="cpu",
                edge_device_id="edge-01",
                vehicle_id=None,
                route_id=None,
                events_output="events.jsonl",
                summary_output="summary.json",
                annotated_output=None,
            )
            store.record_frame("run-2", outcome())
            store.close()

            connection = sqlite3.connect(database)
            try:
                count = connection.execute(
                    "SELECT COUNT(*) FROM detections"
                ).fetchone()[0]
            finally:
                connection.close()

        self.assertEqual(count, 0)

    def test_late_uncertainty_still_enters_review_queue(self) -> None:
        with TemporaryDirectory() as temporary:
            database = Path(temporary) / "observations.db"
            store = SQLiteObservationStore(database, flush_frames=1)
            store.start_run(
                run_id="run-3",
                started_at="2026-10-21T00:00:00+00:00",
                source="0",
                backend="rfdetr",
                model="model.pth",
                compute_device="cpu",
                edge_device_id="edge-01",
                vehicle_id=None,
                route_id=None,
                events_output="events.jsonl",
                summary_output="summary.json",
                annotated_output=None,
            )
            store.record_frame("run-3", outcome(review_required=False))
            store.record_frame(
                "run-3",
                outcome(
                    frame_index=2,
                    review_required=True,
                    newly_confirmed_track_ids=(),
                ),
            )
            store.close()

            reviews = list_review_queue(database)

        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["frame_index"], 2)


if __name__ == "__main__":
    unittest.main()
