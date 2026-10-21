from __future__ import annotations

import base64
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml

from litter_edge.training_data import prepare_training_data


TEST_CLASS_NAMES = {
    0: "plastic_bottle",
    1: "glass_bottle",
    2: "metal_can",
    3: "paper",
    4: "cardboard",
    5: "plastic_bag",
    6: "food_wrapper",
    7: "disposable_cup",
    8: "cigarette_butt",
    9: "food_waste",
    10: "textile",
    11: "tire",
    12: "battery",
    13: "electronic_waste",
    14: "broken_glass",
    15: "other_litter",
}


class TrainingDataTests(unittest.TestCase):
    def test_builds_grouped_coco_splits_and_reports_taxonomy_gaps(self) -> None:
        annotations_url = "https://example.test/annotations.json"
        source = {
            "licenses": [
                {
                    "id": 1,
                    "name": "CC BY 4.0",
                    "url": "https://creativecommons.org/licenses/by/4.0/",
                }
            ],
            "categories": [
                {"id": 10, "name": "Clear plastic bottle"},
                {"id": 11, "name": "Drink can"},
                {"id": 12, "name": "Plastic bottle cap"},
            ],
            "images": [
                {
                    "id": 1,
                    "file_name": "batch_a/000001.jpg",
                    "flickr_640_url": "https://example.test/1.jpg",
                    "width": 100,
                    "height": 80,
                    "license": 1,
                },
                {
                    "id": 2,
                    "file_name": "batch_b/000002.jpg",
                    "flickr_640_url": "https://example.test/2.jpg",
                    "width": 100,
                    "height": 80,
                    "license": 1,
                },
                {
                    "id": 3,
                    "file_name": "batch_c/000003.jpg",
                    "flickr_640_url": "https://example.test/3.jpg",
                    "width": 100,
                    "height": 80,
                    "license": 1,
                },
            ],
            "annotations": [
                {"id": 101, "image_id": 1, "category_id": 10, "bbox": [1, 2, 3, 4]},
                {"id": 102, "image_id": 2, "category_id": 11, "bbox": [2, 3, 4, 5]},
                {"id": 103, "image_id": 3, "category_id": 12, "bbox": [3, 4, 5, 6]},
            ],
        }

        def reader(url: str, timeout: float, maximum_bytes: int) -> bytes:
            self.assertGreater(timeout, 0)
            self.assertGreater(maximum_bytes, 0)
            if url == annotations_url:
                return json.dumps(source).encode("utf-8")
            if url.startswith("https://example.test/"):
                return base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAUCAIAAAA7jDsB"
                    "AAAAC0lEQVR4nGNgGAWjYBSMAgABtAABkRu9WQAAAABJRU5ErkJggg=="
                )
            raise AssertionError(url)

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            classes_file = root / "classes.yaml"
            classes_file.write_text(
                yaml.safe_dump(
                    {
                        "names": TEST_CLASS_NAMES
                    }
                ),
                encoding="utf-8",
            )
            output = root / "dataset"
            result = prepare_training_data(
                output=output,
                class_names_file=classes_file,
                annotations_url=annotations_url,
                workers=2,
                reader=reader,
            )
            manifest = json.loads(
                (output / "manifest.json").read_text(encoding="utf-8")
            )
            split_payloads = {
                split: json.loads(
                    (output / split / "_annotations.coco.json").read_text(
                        encoding="utf-8"
                    )
                )
                for split in ("train", "valid", "test")
            }
            normalized_annotations = [
                annotation
                for payload in split_payloads.values()
                for annotation in payload["annotations"]
            ]
            normalized_images = [
                image
                for payload in split_payloads.values()
                for image in payload["images"]
            ]

        self.assertFalse(result["cached"])
        self.assertEqual(
            sum(summary["images"] for summary in result["splits"].values()),
            3,
        )
        all_groups = [
            group
            for summary in result["splits"].values()
            for group in summary["groups"]
        ]
        self.assertEqual(len(all_groups), len(set(all_groups)))
        self.assertEqual(manifest["class_instance_counts"]["plastic_bottle"], 1)
        self.assertEqual(manifest["class_instance_counts"]["metal_can"], 1)
        self.assertEqual(manifest["class_instance_counts"]["other_litter"], 1)
        self.assertEqual(manifest["schema_version"], "1.1")
        self.assertIn("tire", manifest["classes_without_instances"])
        self.assertTrue(
            all(image["width"] == 10 and image["height"] == 20 for image in normalized_images)
        )
        first_bbox = next(
            annotation["bbox"]
            for annotation in normalized_annotations
            if annotation["id"] == 101
        )
        for observed, expected in zip(
            first_bbox,
            [0.1, 0.5, 0.3, 1.0],
            strict=True,
        ):
            self.assertAlmostEqual(observed, expected)
        for payload in split_payloads.values():
            self.assertEqual(len(payload["images"]), 1)
            self.assertEqual(len(payload["annotations"]), 1)
            self.assertEqual(len(payload["categories"]), 16)

    def test_requires_three_independent_groups(self) -> None:
        annotations_url = "https://example.test/annotations.json"
        source = {
            "licenses": [],
            "categories": [{"id": 1, "name": "Cigarette"}],
            "images": [
                {
                    "id": 1,
                    "file_name": "batch_a/1.jpg",
                    "flickr_640_url": "https://example.test/1.jpg",
                }
            ],
            "annotations": [],
        }

        def reader(url: str, timeout: float, maximum_bytes: int) -> bytes:
            return json.dumps(source).encode("utf-8")

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            classes_file = root / "classes.yaml"
            classes_file.write_text(
                yaml.safe_dump(
                    {
                        "names": TEST_CLASS_NAMES
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "three independent"):
                prepare_training_data(
                    output=root / "dataset",
                    class_names_file=classes_file,
                    annotations_url=annotations_url,
                    reader=reader,
                )


if __name__ == "__main__":
    unittest.main()
