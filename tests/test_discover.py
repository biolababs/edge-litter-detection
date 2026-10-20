from __future__ import annotations

import unittest

from litter_edge.discover import discover_cameras, probe_source


class FakeFrame:
    shape = (720, 1280, 3)


class FakeCapture:
    def __init__(self, source: object) -> None:
        self.source = source
        self.released = False

    def isOpened(self) -> bool:
        return self.source in {0, "rtsp://user:secret@example.test/live?token=abc"}

    def read(self) -> tuple[bool, FakeFrame | None]:
        return (True, FakeFrame()) if self.isOpened() else (False, None)

    def get(self, property_id: int) -> float:
        return 30.0 if property_id == FakeCV2.CAP_PROP_FPS else 0.0

    def getBackendName(self) -> str:
        return "FAKE"

    def release(self) -> None:
        self.released = True


class FakeCV2:
    CAP_PROP_FPS = 5

    @staticmethod
    def VideoCapture(source: object) -> FakeCapture:
        return FakeCapture(source)

    @staticmethod
    def imread(source: str) -> FakeFrame | None:
        return FakeFrame() if source.endswith("sample.jpg") else None


class DiscoverTests(unittest.TestCase):
    def test_discovers_working_camera(self) -> None:
        cameras = discover_cameras(2, cv2_module=FakeCV2)

        self.assertEqual(len(cameras), 1)
        self.assertEqual(cameras[0]["source"], "0")
        self.assertEqual(cameras[0]["width"], 1280)
        self.assertEqual(cameras[0]["reported_fps"], 30.0)

    def test_probes_image(self) -> None:
        result = probe_source("sample.jpg", cv2_module=FakeCV2)

        self.assertEqual(result["kind"], "image")
        self.assertTrue(result["frame_read"])
        self.assertEqual(result["height"], 720)

    def test_redacts_stream_credentials(self) -> None:
        result = probe_source(
            "rtsp://user:secret@example.test/live?token=abc",
            cv2_module=FakeCV2,
        )

        self.assertEqual(result["source"], "rtsp://example.test/live")
        self.assertTrue(result["available"])


if __name__ == "__main__":
    unittest.main()
