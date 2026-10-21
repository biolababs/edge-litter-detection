from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from litter_edge.api import create_app


class APISecurityTests(unittest.TestCase):
    def test_dashboard_returns_security_headers(self) -> None:
        with TestClient(create_app()) as client:
            response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])

    def test_interactive_api_docs_are_disabled_by_default(self) -> None:
        with TestClient(create_app()) as client:
            response = client.get("/docs")

        self.assertEqual(response.status_code, 404)

    def test_detection_requires_an_allowed_content_type(self) -> None:
        with TestClient(create_app()) as client:
            response = client.post(
                "/v1/detect",
                content=b"not-an-image",
                headers={"Content-Type": "application/octet-stream"},
            )

        self.assertEqual(response.status_code, 415)

    def test_detection_rejects_a_mismatched_image_signature(self) -> None:
        with TestClient(create_app()) as client:
            response = client.post(
                "/v1/detect",
                content=b"not-a-jpeg",
                headers={"Content-Type": "image/jpeg"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("declared image type", response.json()["detail"])

    def test_stream_request_limits_are_validated_before_start(self) -> None:
        with TestClient(create_app()) as client:
            response = client.post(
                "/v1/streams",
                json={"source": "0", "max_frames": -1},
            )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
