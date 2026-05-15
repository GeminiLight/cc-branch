from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cc_branch.application.global_agents import read_global_agents, save_global_agents


class GlobalAgentsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.home = Path(self.tmpdir.name)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_read_missing_global_agents_returns_template(self):
        with patch("cc_branch.agent_registry.paths.Path.home", return_value=self.home):
            result = read_global_agents()

        self.assertTrue(result.ok)
        self.assertFalse(result.payload["exists"])
        self.assertEqual(result.payload["path"], str(self.home / ".cc-branch/agents.yaml"))
        self.assertIn("agents: {}", result.payload["content"])
        self.assertIn("codex", {agent["id"] for agent in result.payload["agents"]})
        self.assertIn("codex", {agent["id"] for agent in result.payload["builtin_agents"]})
        self.assertEqual(result.payload["user_agents"], [])

    def test_save_global_agents_writes_user_override(self):
        content = """agents:
  codex:
    command: codex
    resume_mode: flag
    resume_template: "resume {session_id}"
"""
        with patch("cc_branch.agent_registry.paths.Path.home", return_value=self.home):
            result = save_global_agents(content)

        path = self.home / ".cc-branch/agents.yaml"
        self.assertTrue(result.ok)
        self.assertTrue(path.exists())
        self.assertIn("codex", path.read_text(encoding="utf-8"))
        self.assertIn("codex", {agent["id"] for agent in result.payload["agents"]})
        self.assertIn("codex", {agent["id"] for agent in result.payload["user_agents"]})

    def test_save_global_agents_rejects_invalid_shape(self):
        with patch("cc_branch.agent_registry.paths.Path.home", return_value=self.home):
            result = save_global_agents("agents: []\n")

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "invalid_global_agents")
        self.assertFalse((self.home / ".cc-branch/agents.yaml").exists())


if __name__ == "__main__":
    unittest.main()
