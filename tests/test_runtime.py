import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from litter_edge.runtime import _safe_source_label, _timing_profile, run
from litter_edge.schema import Detection
from litter_edge.storage import summarize_counts


class FakeDetector:
    backend_name = "rfdetr"

    def predict(self, frame: object) -> list[Detection]:
        return [
            Detection(
                1,
                2,
                20,
                30,
                confidence=0.9,
                class_id=3,
                class_name="plastic",
            )
        ]


class RuntimeTests(unittest.TestCase):
    def test_timing_profile_uses_non_overlapping_component_shares(self) -> None:
        profile = _timing_profile(
            {
                "detector_call": [60.0],
                "pipeline_total": [65.0],
                "detector_preprocess": [10.0],
                "model_forward": [40.0],
                "detector_postprocess": [10.0],
                "tracking_policy_and_counting": [5.0],
                "event_serialization_and_write": [5.0],
            },
            wall_seconds=0.1,
        )

        shares = profile["exclusive_wall_share_percent"]
        self.assertNotIn("detector_call", shares)
        self.assertAlmostEqual(shares["model_forward"], 40.0)
        self.assertAlmostEqual(shares["unattributed_loop_and_finalization"], 30.0)

    def test_redacts_stream_credentials_and_query(self) -> None:
        source = "rtsp://camera-user:secret@example.test:8554/live?token=abc"
        self.assertEqual(
            _safe_source_label(source),
            "rtsp://example.test:8554/live",
        )

    def test_preserves_local_path(self) -> None:
        self.assertEqual(_safe_source_label("sample.mp4"), "sample.mp4")

    def test_run_writes_redacted_events_and_unique_counts(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "summary.json"
            events = root / "events.jsonl"
            args = argparse.Namespace(
                config="config/project.yaml",
                backend=None,
                model=None,
                class_names=None,
                separation_config=None,
                source="rtsp://user:secret@example.test/live?token=abc",
                device="cpu",
                confidence=None,
                track=True,
                optimize=False,
                display=False,
                annotated_output=None,
                events_output=str(events),
                output=str(output),
                database=str(root / "observations.db"),
                no_database=False,
                database_flush_frames=1,
                persist_detections=False,
                edge_device_id="edge-test",
                vehicle_id="truck-test",
                route_id="route-test",
                max_frames=0,
            )
            with patch(
                "litter_edge.runtime.create_detector",
                return_value=FakeDetector(),
            ):
                with patch(
                    "litter_edge.runtime._frames",
                    return_value=iter(
                        [
                            (object(), 0.0, 15.0),
                            (object(), 1 / 15, 15.0),
                        ]
                    ),
                ):
                    summary = run(args)

            events_text = events.read_text(encoding="utf-8")
            event_rows = [json.loads(line) for line in events_text.splitlines()]
            saved_summary = json.loads(output.read_text(encoding="utf-8"))
            stored_counts = summarize_counts(root / "observations.db")

        self.assertEqual(summary["unique_session_counts"], {"plastic": 1})
        self.assertEqual(saved_summary["source"], "rtsp://example.test/live")
        self.assertEqual(len(event_rows), 2)
        self.assertEqual(event_rows[1]["unique_session_counts"], {"plastic": 1})
        self.assertEqual(event_rows[1]["vehicle_id"], "truck-test")
        self.assertEqual(stored_counts["run_unique_detected_counts"], {"plastic": 1})
        self.assertNotIn("secret", events_text)


if __name__ == "__main__":
    unittest.main()
