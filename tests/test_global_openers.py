from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cc_branch.application.global_openers import read_global_openers, save_global_openers
from cc_branch.opener_registry import load_global_openers


class GlobalOpenersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.home = Path(self.tmpdir.name)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_read_missing_global_openers_returns_template(self):
        with patch("cc_branch.opener_registry.Path.home", return_value=self.home):
            result = read_global_openers()

        self.assertTrue(result.ok)
        self.assertFalse(result.payload["exists"])
        self.assertEqual(result.payload["path"], str(self.home / ".cc-branch/openers.yaml"))
        self.assertIn("openers: {}", result.payload["content"])

    def test_save_global_openers_writes_user_opener(self):
        content = """openers:
  ghostty:
    label: Ghostty
    kind: terminal
    command: ghostty
"""
        with patch("cc_branch.opener_registry.Path.home", return_value=self.home):
            result = save_global_openers(content)
            openers = load_global_openers()

        self.assertTrue(result.ok)
        self.assertEqual(openers["ghostty"].label, "Ghostty")
        self.assertEqual(openers["ghostty"].command, "ghostty")
        self.assertIn("ghostty", {opener["id"] for opener in result.payload["user_openers"]})

    def test_save_global_openers_rejects_invalid_shape(self):
        with patch("cc_branch.opener_registry.Path.home", return_value=self.home):
            result = save_global_openers("openers: []\n")

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "invalid_global_openers")
        self.assertFalse((self.home / ".cc-branch/openers.yaml").exists())


if __name__ == "__main__":
    unittest.main()
