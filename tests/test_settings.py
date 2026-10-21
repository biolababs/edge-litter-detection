from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from litter_edge.settings import load_settings


VALID_CONFIG = """
project_name: litter
backend: grounding_dino
model: IDEA-Research/grounding-dino-tiny
base_model: IDEA-Research/grounding-dino-tiny
class_names: config/classes.yaml
task: detect
image_size: 640
epochs: 5
confidence: 0.25
iou: 0.45
max_detections: 100
target:
  engine_workspace_gb: 1
validation:
  operational_gates:
    preferred_incremental_memory_gb: 1.5
    maximum_incremental_memory_gb: 2.0
    minimum_remaining_available_memory_gb: 2.0
tracking:
  enabled: true
  iou_threshold: 0.3
  max_missed_frames: 30
  min_confirmed_hits: 2
  class_mismatch_penalty: 0.75
"""


class SettingsTests(unittest.TestCase):
    def test_loads_valid_configuration(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "project.yaml"
            path.write_text(VALID_CONFIG, encoding="utf-8")
            settings = load_settings(path)
        self.assertEqual(settings.backend, "grounding_dino")
        self.assertEqual(settings.model, "IDEA-Research/grounding-dino-tiny")
        self.assertEqual(settings.image_size, 640)
        self.assertEqual(settings.run_name, "rfdetr-nano-custom")
        self.assertEqual(settings.engine_workspace_gb, 1)
        self.assertEqual(settings.maximum_incremental_memory_gb, 2.0)
        self.assertTrue(settings.tracking_enabled)
        self.assertEqual(
            settings.separation_policy_file,
            Path("config/separation.yaml"),
        )
        self.assertEqual(settings.storage_database, Path("state/litter-edge.db"))
        self.assertEqual(settings.storage_flush_frames, 15)

    def test_rejects_non_stride_aligned_image_size(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "project.yaml"
            path.write_text(VALID_CONFIG.replace("640", "650"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "multiple of 32"):
                load_settings(path)

    def test_accepts_optional_rfdetr_backend(self) -> None:
        config = VALID_CONFIG.replace(
            "backend: grounding_dino",
            "backend: rfdetr",
        )
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "project.yaml"
            path.write_text(config, encoding="utf-8")
            settings = load_settings(path)
        self.assertEqual(settings.backend, "rfdetr")

    def test_loads_nested_optional_training_settings(self) -> None:
        config = VALID_CONFIG + """
custom_training:
  base_model: rfdetr-nano
  epochs: 12
  run_name: site-custom
"""
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "project.yaml"
            path.write_text(config, encoding="utf-8")
            settings = load_settings(path)
        self.assertEqual(settings.base_model, "rfdetr-nano")
        self.assertEqual(settings.epochs, 12)
        self.assertEqual(settings.run_name, "site-custom")

    def test_rejects_preferred_memory_above_hard_limit(self) -> None:
        invalid = VALID_CONFIG.replace(
            "preferred_incremental_memory_gb: 1.5",
            "preferred_incremental_memory_gb: 2.5",
        )
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "project.yaml"
            path.write_text(invalid, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cannot exceed"):
                load_settings(path)


if __name__ == "__main__":
    unittest.main()

