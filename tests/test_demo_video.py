from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from litter_edge.demo_video import prepare_demo_video


class FakeResponse:
    def __init__(self, content: bytes, url: str) -> None:
        self.content = io.BytesIO(content)
        self.url = url
        self.headers = {"Content-Length": str(len(content))}

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def geturl(self) -> str:
        return self.url

    def read(self, maximum: int) -> bytes:
        return self.content.read(maximum)


class DemoVideoTests(unittest.TestCase):
    def test_downloads_verifies_and_attributes_video(self) -> None:
        video = b"\x1a\x45\xdf\xa3" + b"demo-video"
        sha1 = hashlib.sha1(video).hexdigest()
        url = "https://example.test/recycling.webm"

        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "demo.webm"
            with patch(
                "litter_edge.demo_video.urlopen",
                return_value=FakeResponse(video, url),
            ):
                result = prepare_demo_video(
                    output,
                    timeout=2,
                    video_url=url,
                    expected_sha1=sha1,
                )
            manifest = json.loads(
                (output.parent / "manifest.json").read_text(encoding="utf-8")
            )
            saved = output.read_bytes()

        self.assertEqual(saved, video)
        self.assertEqual(
            result["license"]["identifier"],
            "CC-BY-SA-3.0",
        )
        self.assertEqual(manifest["sha1"], sha1)
        self.assertIn("not a labelled", manifest["purpose"])
        self.assertIn("Ireland4me", manifest["attribution"])

    def test_rejects_checksum_mismatch_without_publishing_file(self) -> None:
        video = b"\x1a\x45\xdf\xa3" + b"demo-video"
        url = "https://example.test/recycling.webm"
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "demo.webm"
            with patch(
                "litter_edge.demo_video.urlopen",
                return_value=FakeResponse(video, url),
            ):
                with self.assertRaisesRegex(ValueError, "SHA-1 mismatch"):
                    prepare_demo_video(
                        output,
                        video_url=url,
                        expected_sha1="0" * 40,
                    )
            self.assertFalse(output.exists())

    def test_rejects_non_https_source(self) -> None:
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            prepare_demo_video(
                "unused.webm",
                video_url="http://example.test/video.webm",
            )


if __name__ == "__main__":
    unittest.main()
