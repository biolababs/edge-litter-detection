from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from litter_edge.evaluate_counts import evaluate_count_files


class CountEvaluationTests(unittest.TestCase):
    def test_scores_visible_and_unique_counts(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            classes = root / "classes.yaml"
            classes.write_text(
                "names:\n  0: glass\n  1: plastic\n",
                encoding="utf-8",
            )
            events = root / "events.jsonl"
            rows = [
                {
                    "frame_index": 1,
                    "visible_counts": {"plastic": 1},
                    "unique_session_counts": {},
                },
                {
                    "frame_index": 2,
                    "visible_counts": {"plastic": 1},
                    "unique_session_counts": {"plastic": 1},
                },
            ]
            events.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            truth = root / "truth.json"
            truth.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "frames": [
                            {
                                "frame_index": 1,
                                "visible_counts": {"plastic": 1},
                            },
                            {
                                "frame_index": 2,
                                "visible_counts": {"plastic": 2},
                            },
                        ],
                        "unique_session_counts": {"plastic": 1},
                    }
                ),
                encoding="utf-8",
            )

            result = evaluate_count_files(events, truth, classes)

        self.assertEqual(result["annotated_frames"], 2)
        self.assertEqual(
            result["visible_counts"]["mae_across_class_frame_pairs"],
            0.25,
        )
        self.assertEqual(
            result["visible_counts"]["per_class"]["plastic"]["mae"],
            0.5,
        )
        self.assertTrue(result["unique_session_counts"]["exact"])

    def test_rejects_missing_annotated_frame(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            classes = root / "classes.yaml"
            classes.write_text("names:\n  0: plastic\n", encoding="utf-8")
            events = root / "events.jsonl"
            events.write_text(
                json.dumps(
                    {
                        "frame_index": 1,
                        "visible_counts": {},
                        "unique_session_counts": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            truth = root / "truth.json"
            truth.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "frames": [
                            {"frame_index": 2, "visible_counts": {}},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "annotated frame 2"):
                evaluate_count_files(events, truth, classes)

    def test_rejects_unknown_schema_version(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            classes = root / "classes.yaml"
            classes.write_text("names:\n  0: plastic\n", encoding="utf-8")
            events = root / "events.jsonl"
            events.write_text(
                json.dumps(
                    {
                        "frame_index": 1,
                        "visible_counts": {},
                        "unique_session_counts": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            truth = root / "truth.json"
            truth.write_text(
                json.dumps(
                    {
                        "schema_version": "2.0",
                        "frames": [
                            {"frame_index": 1, "visible_counts": {}},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "schema_version"):
                evaluate_count_files(events, truth, classes)


if __name__ == "__main__":
    unittest.main()
