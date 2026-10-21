from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from litter_edge.schema import Detection
from litter_edge.sorting import load_separation_policy


POLICY = """
schema_version: "1.0"
destinations:
  plastic: plastics_stream
  other_litter: manual_sort
review:
  confidence_below: 0.55
  always_review:
    - other_litter
"""


class SeparationPolicyTests(unittest.TestCase):
    def test_assigns_destination_and_low_confidence_review(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "separation.yaml"
            path.write_text(POLICY, encoding="utf-8")
            policy = load_separation_policy(
                path,
                class_names={0: "plastic", 1: "other_litter"},
            )

        detection = policy.apply(
            Detection(1, 2, 3, 4, 0.4, 0, "plastic", track_id=7, confirmed=True)
        )
        self.assertEqual(detection.separation_destination, "plastics_stream")
        self.assertTrue(detection.review_required)

    def test_always_reviews_other_litter(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "separation.yaml"
            path.write_text(POLICY, encoding="utf-8")
            policy = load_separation_policy(path)

        detection = policy.apply(
            Detection(1, 2, 3, 4, 0.99, 1, "other_litter")
        )
        self.assertEqual(detection.separation_destination, "manual_sort")
        self.assertTrue(detection.review_required)


if __name__ == "__main__":
    unittest.main()
