import unittest

from litter_edge.schema import Detection
from litter_edge.tracking import (
    ClassStabilizedIoUTracker,
    SessionCounter,
    intersection_over_union,
)


def detection(
    bbox: tuple[float, float, float, float],
    class_id: int = 0,
    class_name: str = "glass",
) -> Detection:
    return Detection(*bbox, confidence=0.9, class_id=class_id, class_name=class_name)


class TrackingTests(unittest.TestCase):
    def test_iou(self) -> None:
        self.assertAlmostEqual(
            intersection_over_union((0, 0, 10, 10), (5, 5, 15, 15)),
            25 / 175,
        )

    def test_same_object_is_counted_once_across_frames(self) -> None:
        tracker = ClassStabilizedIoUTracker(min_confirmed_hits=2)
        counter = SessionCounter()

        first = tracker.update([detection((10, 10, 40, 40))])
        first_counts, first_new = counter.update(first)
        second = tracker.update([detection((11, 10, 41, 40))])
        second_counts, second_new = counter.update(second)
        third = tracker.update([detection((12, 11, 42, 41))])
        third_counts, third_new = counter.update(third)

        self.assertEqual(first_counts, {})
        self.assertEqual(first_new, ())
        self.assertEqual(second_counts, {"glass": 1})
        self.assertEqual(second_new, (1,))
        self.assertEqual(third_counts, {"glass": 1})
        self.assertEqual(third_new, ())

    def test_class_vote_stabilizes_one_noisy_prediction(self) -> None:
        tracker = ClassStabilizedIoUTracker(min_confirmed_hits=1)
        first = tracker.update([detection((10, 10, 40, 40), 3, "plastic")])
        second = tracker.update([detection((10, 10, 40, 40), 1, "metal")])
        third = tracker.update([detection((10, 10, 40, 40), 3, "plastic")])

        self.assertEqual(first[0].track_id, second[0].track_id)
        self.assertEqual(second[0].class_name, "plastic")
        self.assertEqual(third[0].class_name, "plastic")


if __name__ == "__main__":
    unittest.main()
