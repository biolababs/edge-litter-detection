from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from litter_edge.classes import load_class_names


class ClassNamesTests(unittest.TestCase):
    def test_loads_mapping(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "classes.yaml"
            path.write_text("names:\n  0: glass\n  1: plastic\n", encoding="utf-8")
            self.assertEqual(load_class_names(path), {0: "glass", 1: "plastic"})

    def test_rejects_non_contiguous_ids(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "classes.yaml"
            path.write_text("names:\n  0: glass\n  2: plastic\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "contiguous"):
                load_class_names(path)


if __name__ == "__main__":
    unittest.main()
