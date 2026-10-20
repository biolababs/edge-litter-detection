import unittest

from litter_edge.pipeline import LitterPipeline
from litter_edge.schema import Detection
from litter_edge.tracking import ClassStabilizedIoUTracker


class FakeDetector:
    backend_name = "fake"

    def predict(self, frame_bgr: object) -> list[Detection]:
        return [
            Detection(
                10,
                10,
                40,
                40,
                confidence=0.9,
                class_id=3,
                class_name="plastic",
            )
        ]


class PipelineTests(unittest.TestCase):
    def test_reports_visible_and_unique_counts(self) -> None:
        pipeline = LitterPipeline(
            detector=FakeDetector(),
            tracker=ClassStabilizedIoUTracker(min_confirmed_hits=2),
        )

        first = pipeline.process(object(), 1)
        second = pipeline.process(object(), 2)

        self.assertEqual(first.visible_counts, {"plastic": 1})
        self.assertEqual(first.unique_session_counts, {})
        self.assertEqual(second.confirmed_visible_counts, {"plastic": 1})
        self.assertEqual(second.unique_session_counts, {"plastic": 1})
        self.assertEqual(second.newly_confirmed_track_ids, (1,))


if __name__ == "__main__":
    unittest.main()
