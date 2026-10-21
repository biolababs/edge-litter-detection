from __future__ import annotations

import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from litter_edge.demo_data import prepare_demo_data


class FakeResponse:
    def __init__(self, content: bytes, url: str) -> None:
        self._content = content
        self._url = url
        self.headers = {"Content-Length": str(len(content))}

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def geturl(self) -> str:
        return self._url

    def read(self, maximum: int) -> bytes:
        return io.BytesIO(self._content).read(maximum)


class DemoDataTests(unittest.TestCase):
    def test_downloads_image_and_writes_attribution_manifest(self) -> None:
        annotations_url = "https://example.test/annotations.json"
        image_url = "https://example.test/litter.jpg"
        annotations = {
            "licenses": [
                {
                    "id": 1,
                    "name": "CC BY 4.0",
                    "url": "https://creativecommons.org/licenses/by/4.0/",
                }
            ],
            "categories": [{"id": 4, "name": "Clear plastic bottle"}],
            "images": [
                {
                    "id": 7,
                    "file_name": "batch_1/000007.JPG",
                    "flickr_640_url": image_url,
                    "license": 1,
                }
            ],
            "annotations": [{"image_id": 7, "category_id": 4}],
        }
        annotation_bytes = json.dumps(annotations).encode("utf-8")
        jpeg_bytes = b"\xff\xd8\xff\xe0" + b"demo-image"

        def fake_urlopen(request: object, timeout: float) -> FakeResponse:
            url = request.full_url
            if url == annotations_url:
                return FakeResponse(annotation_bytes, url)
            if url == image_url:
                return FakeResponse(jpeg_bytes, url)
            raise AssertionError(url)

        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "demo"
            with patch("litter_edge.demo_data.urlopen", side_effect=fake_urlopen):
                result = prepare_demo_data(
                    output=output,
                    limit=1,
                    timeout=2,
                    annotations_url=annotations_url,
                )
            manifest = json.loads(
                (output / "manifest.json").read_text(encoding="utf-8")
            )
            image_path = Path(result["first_image"])

        self.assertEqual(result["count"], 1)
        self.assertTrue(image_path.name.endswith(".jpg"))
        self.assertEqual(manifest["images"][0]["license"]["name"], "CC BY 4.0")
        self.assertEqual(
            manifest["images"][0]["categories"],
            ["Clear plastic bottle"],
        )

    def test_reuses_complete_cached_demo_set(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            image = output / "taco-000001.jpg"
            image.write_bytes(b"\xff\xd8\xff")
            (output / "manifest.json").write_text(
                json.dumps({"images": [{"local_file": image.name}]}),
                encoding="utf-8",
            )
            with patch(
                "litter_edge.demo_data.urlopen",
                side_effect=AssertionError("network should not be used"),
            ):
                result = prepare_demo_data(output=output, limit=1)

        self.assertTrue(result["cached"])
        self.assertEqual(result["count"], 1)

    def test_uses_taco_default_when_image_license_is_empty(self) -> None:
        annotations_url = "https://example.test/annotations.json"
        image_url = "https://example.test/litter.jpg"
        annotations = {
            "licenses": [],
            "categories": [{"id": 1, "name": "Bottle"}],
            "images": [
                {
                    "id": 2,
                    "file_name": "batch_1/000002.jpg",
                    "flickr_640_url": image_url,
                    "license": [],
                }
            ],
            "annotations": [{"image_id": 2, "category_id": 1}],
        }
        annotation_bytes = json.dumps(annotations).encode("utf-8")

        def fake_urlopen(request: object, timeout: float) -> FakeResponse:
            url = request.full_url
            if url == annotations_url:
                return FakeResponse(annotation_bytes, url)
            if url == image_url:
                return FakeResponse(b"\xff\xd8\xff\xe0demo", url)
            raise AssertionError(url)

        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            with patch("litter_edge.demo_data.urlopen", side_effect=fake_urlopen):
                prepare_demo_data(
                    output=output,
                    limit=1,
                    annotations_url=annotations_url,
                )
            manifest = json.loads(
                (output / "manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(manifest["images"][0]["license"]["name"], "CC BY 4.0")
        self.assertIn("default", manifest["images"][0]["license"]["basis"])

    def test_rejects_unbounded_download_count(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not exceed 100"):
            prepare_demo_data(output="unused", limit=101)


if __name__ == "__main__":
    unittest.main()
