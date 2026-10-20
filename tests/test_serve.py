from __future__ import annotations

import unittest
from unittest.mock import patch

from litter_edge.serve import build_parser


class ServeArgumentsTests(unittest.TestCase):
    def test_uses_environment_defaults(self) -> None:
        with patch.dict(
            "os.environ",
            {"LITTER_HOST": "0.0.0.0", "LITTER_PORT": "9000"},
            clear=False,
        ):
            args = build_parser().parse_args([])

        self.assertEqual(args.host, "0.0.0.0")
        self.assertEqual(args.port, 9000)

    def test_command_line_overrides_defaults(self) -> None:
        args = build_parser().parse_args(["--host", "127.0.0.2", "--port", "8080"])

        self.assertEqual(args.host, "127.0.0.2")
        self.assertEqual(args.port, 8080)


if __name__ == "__main__":
    unittest.main()
