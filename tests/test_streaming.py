from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from litter_edge.classes import load_class_names
from litter_edge.schema import Detection
from litter_edge.settings import load_settings
from litter_edge.sorting import load_separation_policy
from litter_edge.storage import list_runs
from litter_edge.streaming import StreamSession, validate_stream_source


class FakeDetector:
    backend_name = "test"

    def predict(self, frame: object) -> list[Detection]:
        return [
            Detection(
                1,
                2,
                30,
                40,
                confidence=0.9,
                class_id=0,
                class_name="plastic_bottle",
            )
        ]


class FakeCapture:
    def __init__(self, frames: int = 2) -> None:
        self.remaining = frames
        self.frame_index = 0
        self.released = False

    def isOpened(self) -> bool:
        return True

    def read(self) -> tuple[bool, object | None]:
        if self.remaining == 0:
            return False, None
        self.remaining -= 1
        self.frame_index += 1
        return True, object()

    def get(self, property_id: int) -> float:
        if property_id == 5:
            return 10.0
        if property_id == 0:
            return self.frame_index * 100.0
        return 0.0

    def release(self) -> None:
        self.released = True


class StreamingTests(unittest.TestCase):
    def test_rejects_unsupported_network_scheme(self) -> None:
        with self.assertRaisesRegex(ValueError, "http, https, rtsp"):
            validate_stream_source("ftp://example.test/video.mp4")

    def test_redacts_stream_credentials(self) -> None:
        settings = load_settings("config/project.yaml")
        policy = load_separation_policy(
            "config/separation.yaml",
            class_names=load_class_names("config/classes.yaml"),
        )
        capture = FakeCapture()
        with TemporaryDirectory() as temporary:
            database = Path(temporary) / "stream.db"
            session = StreamSession(
                source="rtsp://user:secret@example.test/live?token=abc",
                detector=FakeDetector(),
                backend="test",
                model="test-model",
                device="cpu",
                settings=settings,
                separation_policy=policy,
                database=database,
                edge_device_id="edge-test",
                vehicle_id="truck-test",
                route_id="route-test",
                realtime=False,
                capture_factory=lambda source: capture,
                renderer=lambda frame, outcome: b"jpeg",
            )
            session.start()
            self.assertTrue(session.wait(timeout=2))
            snapshot = session.snapshot()
            runs = list_runs(database, limit=1)
            session.close()

        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["frames"], 2)
        self.assertEqual(
            snapshot["latest_outcome"]["unique_session_counts"],
            {"plastic_bottle": 1},
        )
        self.assertEqual(snapshot["source"], "rtsp://example.test/live")
        self.assertEqual(runs[0]["source"], "rtsp://example.test/live")
        self.assertNotIn("secret", str(snapshot))
        self.assertTrue(capture.released)

    def test_redacts_credentials_from_capture_errors(self) -> None:
        settings = load_settings("config/project.yaml")
        policy = load_separation_policy(
            "config/separation.yaml",
            class_names=load_class_names("config/classes.yaml"),
        )
        source = "rtsp://user:secret@example.test/live?token=abc"
        with TemporaryDirectory() as temporary:
            session = StreamSession(
                source=source,
                detector=FakeDetector(),
                backend="test",
                model="test-model",
                device="cpu",
                settings=settings,
                separation_policy=policy,
                database=Path(temporary) / "stream.db",
                edge_device_id="edge-test",
                vehicle_id=None,
                route_id=None,
                capture_factory=lambda value: (_ for _ in ()).throw(
                    RuntimeError(f"Unable to connect to {value}")
                ),
                renderer=lambda frame, outcome: b"jpeg",
            )
            session.start()
            self.assertTrue(session.wait(timeout=2))
            snapshot = session.snapshot()

        self.assertEqual(snapshot["status"], "failed")
        self.assertEqual(
            snapshot["error"],
            "Unable to connect to rtsp://example.test/live",
        )
        self.assertNotIn("secret", str(snapshot))


if __name__ == "__main__":
    unittest.main()
