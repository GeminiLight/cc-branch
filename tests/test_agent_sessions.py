"""Tests for local agent session discovery."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cc_branch.application.agent_sessions import agent_session_options


class AgentSessionDiscoveryTests(unittest.TestCase):
    def test_codex_session_index_is_exposed_as_picker_options(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project = root / "workspace"
            home = root / "home"
            config_path = project / ".cc-branch" / "config.yaml"
            index_path = home / ".codex" / "session_index.jsonl"
            config_path.parent.mkdir(parents=True)
            index_path.parent.mkdir(parents=True)
            config_path.write_text("version: 1\nproject: demo\nroot: .\nslots: []\n", encoding="utf-8")
            index_path.write_text(
                "\n".join([
                    json.dumps({
                        "id": "019e0fd9-0000-7000-9000-aaaaaaaaaaaa",
                        "thread_name": "Dashboard polish",
                        "updated_at": "2026-05-10T03:06:26Z",
                    }),
                    json.dumps({"id": "", "thread_name": "ignored"}),
                ]),
                encoding="utf-8",
            )

            result = agent_session_options(config_path, agent="codex", home=home)

        self.assertTrue(result.ok)
        sessions = result.payload["sessions"]
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["agent"], "codex")
        self.assertEqual(sessions[0]["label"], "Dashboard polish")
        self.assertEqual(sessions[0]["id"], "019e0fd9-0000-7000-9000-aaaaaaaaaaaa")

    def test_claude_project_session_index_uses_summary_as_label(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project = root / "workspace"
            home = root / "home"
            config_path = project / ".cc-branch" / "config.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text("version: 1\nproject: demo\nroot: .\nslots: []\n", encoding="utf-8")

            slug = "-" + str(project).strip("/").replace("/", "-")
            index_path = home / ".claude" / "projects" / slug / "sessions-index.json"
            index_path.parent.mkdir(parents=True)
            index_path.write_text(
                json.dumps({
                    "entries": [
                        {
                            "sessionId": "claude-session-1",
                            "summary": "Fix config form",
                            "firstPrompt": "older text",
                            "modified": "2026-05-09T12:00:00Z",
                            "projectPath": str(project),
                        }
                    ]
                }),
                encoding="utf-8",
            )

            result = agent_session_options(config_path, agent="claude", home=home)

        self.assertTrue(result.ok)
        sessions = result.payload["sessions"]
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["agent"], "claude")
        self.assertEqual(sessions[0]["id"], "claude-session-1")
        self.assertEqual(sessions[0]["label"], "Fix config form")


if __name__ == "__main__":
    unittest.main()
