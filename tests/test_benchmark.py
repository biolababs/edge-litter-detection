import unittest

from litter_edge.benchmark import (
    _accelerator_memory_evidence,
    _cuda_device_reference,
    _memory_evidence,
)


class MemoryEvidenceTests(unittest.TestCase):
    def test_plain_cuda_uses_current_device_index(self) -> None:
        class FakeCuda:
            @staticmethod
            def current_device() -> int:
                return 2

        self.assertEqual(_cuda_device_reference(FakeCuda(), "cuda"), 2)
        self.assertEqual(_cuda_device_reference(FakeCuda(), "cuda:0"), "cuda:0")

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

    def test_summarizes_accelerator_memory_without_nvidia_smi(self) -> None:
        evidence = _accelerator_memory_evidence(
            [
                {
                    "accelerator": "Test GPU",
                    "accelerator_allocated_gib": 1.0,
                    "accelerator_reserved_gib": 1.2,
                    "accelerator_peak_allocated_gib": 1.1,
                    "accelerator_peak_reserved_gib": 1.3,
                    "accelerator_free_gib": 6.8,
                    "accelerator_total_gib": 8.0,
                },
                {
                    "accelerator": "Test GPU",
                    "accelerator_allocated_gib": 1.4,
                    "accelerator_reserved_gib": 1.8,
                    "accelerator_peak_allocated_gib": 1.6,
                    "accelerator_peak_reserved_gib": 1.9,
                    "accelerator_free_gib": 6.2,
                    "accelerator_total_gib": 8.0,
                },
            ]
        )

        self.assertEqual(evidence["status"], "measured")
        self.assertEqual(evidence["device"], "Test GPU")
        self.assertEqual(evidence["maximum_allocated_gib"], 1.4)
        self.assertEqual(evidence["peak_reserved_gib"], 1.9)
        self.assertEqual(evidence["minimum_free_gib"], 6.2)


if __name__ == "__main__":
    unittest.main()
