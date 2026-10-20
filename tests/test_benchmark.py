import unittest

from litter_edge.benchmark import _memory_evidence


class MemoryEvidenceTests(unittest.TestCase):
    def test_passes_hard_and_preferred_memory_gates(self) -> None:
        evidence = _memory_evidence(
            [
                {
                    "phase": "before_model",
                    "system_available_gib": 4.5,
                    "process_rss_gib": 0.1,
                },
                {
                    "phase": "sample_1",
                    "system_available_gib": 3.2,
                    "process_rss_gib": 1.2,
                },
            ],
            preferred_incremental_gib=1.5,
            maximum_incremental_gib=2.0,
            minimum_remaining_gib=2.0,
        )

        self.assertEqual(evidence["preferred_status"], "pass")
        self.assertEqual(evidence["hard_gate_status"], "pass")
        self.assertAlmostEqual(evidence["observed_system_incremental_gib"], 1.3)

    def test_fails_when_remaining_memory_is_too_low(self) -> None:
        evidence = _memory_evidence(
            [
                {
                    "phase": "before_model",
                    "system_available_gib": 4.5,
                    "process_rss_gib": 0.1,
                },
                {
                    "phase": "sample_1",
                    "system_available_gib": 1.9,
                    "process_rss_gib": 1.5,
                },
            ],
            preferred_incremental_gib=1.5,
            maximum_incremental_gib=3.0,
            minimum_remaining_gib=2.0,
        )

        self.assertEqual(evidence["preferred_status"], "exceeded")
        self.assertEqual(evidence["hard_gate_status"], "fail")


if __name__ == "__main__":
    unittest.main()
