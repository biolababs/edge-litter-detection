from __future__ import annotations

from io import BytesIO
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from litter_edge.model_fetch import download_model


class FakeResponse(BytesIO):
    def __init__(self, payload: bytes) -> None:
        super().__init__(payload)
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class ModelFetchTests(unittest.TestCase):
    def test_downloads_and_verifies_model(self) -> None:
        content = b"trained-litter-checkpoint"
        expected = hashlib.sha256(content).hexdigest()

        def opener(request: object, timeout: float) -> FakeResponse:
            self.assertEqual(timeout, 5.0)
            return FakeResponse(content)

        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "model.pth"
            manifest = download_model(
                url="https://user:secret@example.test/model.pth?token=abc",
                expected_sha256=expected,
                output=output,
                timeout=5.0,
                opener=opener,
            )
            saved_manifest = json.loads(
                output.with_suffix(".pth.download.json").read_text(encoding="utf-8")
            )

            self.assertEqual(output.read_bytes(), content)

        self.assertEqual(manifest["sha256"], expected)
        self.assertEqual(saved_manifest["source"], "https://example.test/model.pth")

    def test_checksum_failure_leaves_no_model(self) -> None:
        content = b"wrong-content"

        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "model.pth"
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                download_model(
                    url="https://example.test/model.pth",
                    expected_sha256="0" * 64,
                    output=output,
                    opener=lambda request, timeout: FakeResponse(content),
                )
            self.assertFalse(output.exists())

    def test_rejects_non_https_url(self) -> None:
        with TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                download_model(
                    url="http://example.test/model.pth",
                    expected_sha256="0" * 64,
                    output=Path(temporary) / "model.pth",
                    opener=lambda request, timeout: FakeResponse(b""),
                )


if __name__ == "__main__":
    unittest.main()
