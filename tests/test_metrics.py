from __future__ import annotations

import unittest

from litter_edge.metrics import summarize_samples


class SampleSummaryTests(unittest.TestCase):
    def test_reports_variance_and_tail_percentiles(self) -> None:
        summary = summarize_samples([1.0, 2.0, 3.0, 4.0, 100.0])

        self.assertEqual(summary["count"], 5)
        self.assertEqual(summary["median"], 3.0)
        self.assertEqual(summary["p95"], 100.0)
        self.assertEqual(summary["p99"], 100.0)
        self.assertGreater(float(summary["standard_deviation"]), 0.0)

    def test_reports_empty_sample(self) -> None:
        summary = summarize_samples([])

        self.assertEqual(summary["count"], 0)
        self.assertIsNone(summary["standard_deviation"])


if __name__ == "__main__":
    unittest.main()
