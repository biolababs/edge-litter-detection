from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from litter_edge.evaluate_public import (
    _diagnostic_class_confusion,
    _operating_point_metrics,
    _portable_path,
)


class PublicEvaluationTests(unittest.TestCase):
    def test_records_repository_relative_paths_when_possible(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            nested = root / "data" / "test.json"

            self.assertEqual(_portable_path(nested, root), "data/test.json")

    def test_scores_operating_point_by_class(self) -> None:
        metrics = _operating_point_metrics(
            ground_truth=[
                {
                    "image_id": 1,
                    "category_id": 0,
                    "bbox": [10, 10, 20, 20],
                    "iscrowd": 0,
                },
                {
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [50, 50, 10, 10],
                    "iscrowd": 0,
                },
            ],
            predictions=[
                {
                    "image_id": 1,
                    "category_id": 0,
                    "bbox": [10, 10, 20, 20],
                    "score": 0.9,
                },
                {
                    "image_id": 1,
                    "category_id": 0,
                    "bbox": [70, 70, 5, 5],
                    "score": 0.4,
                },
            ],
            class_names={0: "bottle", 1: "can"},
        )

        bottle = metrics["per_class"]["bottle"]
        can = metrics["per_class"]["can"]
        self.assertEqual(bottle["true_positive"], 1)
        self.assertEqual(bottle["false_positive"], 1)
        self.assertEqual(can["false_negative"], 1)
        self.assertAlmostEqual(metrics["micro"]["precision"], 0.5)
        self.assertAlmostEqual(metrics["micro"]["recall"], 0.5)

    def test_marks_classes_without_ground_truth(self) -> None:
        metrics = _operating_point_metrics(
            ground_truth=[],
            predictions=[],
            class_names={0: "battery"},
        )

        self.assertEqual(
            metrics["per_class"]["battery"]["evidence_status"],
            "no_ground_truth_instances",
        )

    def test_reports_cross_class_confusion_after_localization(self) -> None:
        metrics = _diagnostic_class_confusion(
            ground_truth=[
                {
                    "image_id": 1,
                    "category_id": 0,
                    "bbox": [10, 10, 20, 20],
                    "iscrowd": 0,
                },
                {
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [50, 50, 10, 10],
                    "iscrowd": 0,
                },
            ],
            predictions=[
                {
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [10, 10, 20, 20],
                    "score": 0.9,
                },
                {
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [50, 50, 10, 10],
                    "score": 0.8,
                },
                {
                    "image_id": 1,
                    "category_id": 0,
                    "bbox": [80, 80, 5, 5],
                    "score": 0.4,
                },
            ],
            class_names={0: "bottle", 1: "can"},
        )

        self.assertEqual(metrics["correct_class_matches"], 1)
        self.assertEqual(metrics["wrong_class_matches"], 1)
        self.assertEqual(metrics["unmatched_predictions"], 1)
        self.assertEqual(metrics["unmatched_ground_truth"], 0)
        self.assertEqual(
            metrics["top_confusions"][0],
            {
                "ground_truth": "bottle",
                "predicted": "can",
                "count": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
