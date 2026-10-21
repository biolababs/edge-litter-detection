from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from litter_edge.classes import load_class_names, load_class_prompts


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

    def test_loads_open_vocabulary_prompts(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "classes.yaml"
            path.write_text(
                "names:\n"
                "  0: plastic_bottle\n"
                "  1: metal_can\n"
                "prompts:\n"
                "  0: discarded plastic bottle\n"
                "  1: discarded metal can\n",
                encoding="utf-8",
            )
            names = load_class_names(path)
            prompts = load_class_prompts(path, names)

        self.assertEqual(
            prompts,
            {
                0: "discarded plastic bottle",
                1: "discarded metal can",
            },
        )

    def test_derives_prompts_when_not_configured(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "classes.yaml"
            path.write_text("names:\n  0: plastic_bottle\n", encoding="utf-8")
            self.assertEqual(
                load_class_prompts(path),
                {0: "plastic bottle"},
            )

    def test_loads_backend_specific_prompts(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "classes.yaml"
            path.write_text(
                "names:\n"
                "  0: plastic_bottle\n"
                "prompts:\n"
                "  0: discarded plastic bottle\n"
                "omdet_turbo_prompts:\n"
                "  0: plastic bottle\n",
                encoding="utf-8",
            )

            prompts = load_class_prompts(
                path,
                profile="omdet_turbo",
            )

        self.assertEqual(prompts, {0: "plastic bottle"})


if __name__ == "__main__":
    unittest.main()
