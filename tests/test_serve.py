from __future__ import annotations

import unittest
from unittest.mock import patch

from litter_edge.serve import build_parser, validate_bind_host


class ServeArgumentsTests(unittest.TestCase):
    def test_uses_environment_defaults(self) -> None:
        with patch.dict(
            "os.environ",
            {"LITTER_HOST": "127.0.0.1", "LITTER_PORT": "9000"},
            clear=False,
        ):
            args = build_parser().parse_args([])

        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 9000)

    def test_command_line_overrides_defaults(self) -> None:
        args = build_parser().parse_args(["--host", "127.0.0.2", "--port", "8080"])

        self.assertEqual(args.host, "127.0.0.2")
        self.assertEqual(args.port, 8080)

    def test_rejects_public_bind_without_explicit_container_boundary(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "loopback"):
                validate_bind_host("0.0.0.0")

    def test_allows_container_internal_bind_when_explicit(self) -> None:
        with patch.dict(
            "os.environ",
            {"LITTER_CONTAINER_INTERNAL_BIND": "true"},
            clear=True,
        ):
            self.assertEqual(validate_bind_host("0.0.0.0"), "0.0.0.0")


if __name__ == "__main__":
    unittest.main()
