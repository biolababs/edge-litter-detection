from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from litter_edge.evaluate import _ensure_split_available, _json_ready


class EvaluationTests(unittest.TestCase):
    def test_requires_explicit_held_out_test_split(self) -> None:
        with TemporaryDirectory() as temporary:
            dataset = Path(temporary)
            (dataset / "data.yaml").write_text(
                "train: images/train\nval: images/val\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "does not declare a test split"):
                _ensure_split_available(dataset, "test")

            (dataset / "data.yaml").write_text(
                "train: images/train\nval: images/val\ntest: images/test\n",
                encoding="utf-8",
            )
            _ensure_split_available(dataset, "test")

    def test_serializes_metric_like_values(self) -> None:
        class ArrayLike:
            def tolist(self) -> list[float]:
                return [0.5, 0.75]

        self.assertEqual(_json_ready({"scores": ArrayLike()}), {"scores": [0.5, 0.75]})


if __name__ == "__main__":
    unittest.main()
