import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml

from litter_edge.train import validate_coco_training_taxonomy


class TrainValidationTests(unittest.TestCase):
    def test_accepts_exact_coco_runtime_taxonomy(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "train").mkdir()
            (root / "train" / "_annotations.coco.json").write_text(
                json.dumps(
                    {
                        "categories": [
                            {"id": 0, "name": "bottle"},
                            {"id": 1, "name": "can"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            classes = root / "classes.yaml"
            classes.write_text(
                yaml.safe_dump({"names": {0: "bottle", 1: "can"}}),
                encoding="utf-8",
            )

            observed = validate_coco_training_taxonomy(root, classes)

        self.assertEqual(observed, {0: "bottle", 1: "can"})

    def test_rejects_category_id_or_name_drift(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "train").mkdir()
            (root / "train" / "_annotations.coco.json").write_text(
                json.dumps({"categories": [{"id": 0, "name": "bottle"}]}),
                encoding="utf-8",
            )
            classes = root / "classes.yaml"
            classes.write_text(
                yaml.safe_dump({"names": {0: "can"}}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "do not exactly match"):
                validate_coco_training_taxonomy(root, classes)


if __name__ == "__main__":
    unittest.main()
