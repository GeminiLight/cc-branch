from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from cc_branch import desktop_backend


class DesktopBackendTests(unittest.TestCase):
    def test_parser_requires_backend_paths_and_port(self):
        args = desktop_backend.build_parser().parse_args([
            "--port",
            "8765",
            "--config",
            "/tmp/project/.cc-branch.yaml",
            "--state",
            "/tmp/project/.cc-branch.state.yaml",
        ])

        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8765)
        self.assertEqual(args.config, "/tmp/project/.cc-branch.yaml")
        self.assertEqual(args.state, "/tmp/project/.cc-branch.state.yaml")

    def test_main_starts_webui_server_with_explicit_paths(self):
        with patch("cc_branch.desktop_backend.start_server") as start_server:
            result = desktop_backend.main([
                "--host",
                "127.0.0.1",
                "--port",
                "8765",
                "--config",
                "/tmp/project/.cc-branch.yaml",
                "--state",
                "/tmp/project/.cc-branch.state.yaml",
                "--token",
                "secret",
            ])

        self.assertEqual(result, 0)
        start_server.assert_called_once_with(
            Path("/tmp/project/.cc-branch.yaml"),
            Path("/tmp/project/.cc-branch.state.yaml"),
            host="127.0.0.1",
            port=8765,
            token="secret",
        )


if __name__ == "__main__":
    unittest.main()
