"""Tests for local agent session discovery."""

from __future__ import annotations

import json
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cc_branch.application.agent_sessions import agent_session_options


class AgentSessionDiscoveryTests(unittest.TestCase):
    def _write_config(self, project: Path) -> Path:
        config_path = project / ".cc-branch" / "config.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text("version: 1\nproject: demo\nroot: .\nslots: []\n", encoding="utf-8")
        return config_path

    def test_codex_session_index_is_exposed_as_picker_options(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project = root / "workspace"
            home = root / "home"
            config_path = self._write_config(project)
            index_path = home / ".codex" / "session_index.jsonl"
            index_path.parent.mkdir(parents=True)
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
            config_path = self._write_config(project)

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

    def test_claude_project_transcripts_are_exposed_without_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project = root / "workspace"
            home = root / "home"
            config_path = self._write_config(project)

            slug = "-" + str(project).strip("/").replace("/", "-")
            transcript_path = home / ".claude" / "projects" / slug / "transcript-session.jsonl"
            transcript_path.parent.mkdir(parents=True)
            transcript_path.write_text(
                "\n".join([
                    json.dumps({
                        "cwd": str(project),
                        "sessionId": "transcript-session",
                        "timestamp": "2026-05-12T01:00:00Z",
                        "type": "user",
                    }),
                    json.dumps({
                        "type": "summary",
                        "summary": "Refine dashboard session picker",
                    }),
                    json.dumps({
                        "cwd": str(project),
                        "sessionId": "transcript-session",
                        "timestamp": "2026-05-12T02:00:00Z",
                        "type": "assistant",
                    }),
                ]),
                encoding="utf-8",
            )

            result = agent_session_options(config_path, agent="cloud-code", home=home)

        self.assertTrue(result.ok)
        sessions = result.payload["sessions"]
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["agent"], "claude")
        self.assertEqual(sessions[0]["id"], "transcript-session")
        self.assertEqual(sessions[0]["label"], "Refine dashboard session picker")
        self.assertEqual(sessions[0]["updated_at"], "2026-05-12T02:00:00Z")

    def test_gemini_antigravity_metadata_is_exposed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project = root / "workspace"
            home = root / "home"
            config_path = self._write_config(project)

            metadata_path = home / ".gemini" / "antigravity" / "brain" / "gemini-session-1" / "task.md.metadata.json"
            metadata_path.parent.mkdir(parents=True)
            metadata_path.write_text(
                json.dumps({
                    "artifactType": "ARTIFACT_TYPE_TASK",
                    "summary": "Implement install flow",
                    "updatedAt": "2026-05-11T10:00:00Z",
                }),
                encoding="utf-8",
            )

            result = agent_session_options(config_path, agent="gemini", home=home)

        self.assertTrue(result.ok)
        sessions = result.payload["sessions"]
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["agent"], "gemini")
        self.assertEqual(sessions[0]["id"], "gemini-session-1")
        self.assertEqual(sessions[0]["label"], "Antigravity: Implement install flow")

    def test_cursor_composer_headers_are_filtered_to_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project = root / "workspace"
            other_project = root / "other"
            home = root / "home"
            config_path = self._write_config(project)

            db_path = home / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
            db_path.parent.mkdir(parents=True)
            with sqlite3.connect(db_path) as connection:
                connection.execute("create table ItemTable (key text primary key, value text)")
                connection.execute(
                    "insert into ItemTable (key, value) values (?, ?)",
                    (
                        "composer.composerHeaders",
                        json.dumps({
                            "allComposers": [
                                {
                                    "composerId": "cursor-session-1",
                                    "createdAt": 1778351844135,
                                    "unifiedMode": "agent",
                                    "workspaceIdentifier": {"uri": {"fsPath": str(project)}},
                                },
                                {
                                    "composerId": "cursor-session-other",
                                    "createdAt": 1778351844135,
                                    "unifiedMode": "agent",
                                    "workspaceIdentifier": {"uri": {"fsPath": str(other_project)}},
                                },
                                {
                                    "composerId": "cursor-chat",
                                    "createdAt": 1778351844135,
                                    "unifiedMode": "chat",
                                    "workspaceIdentifier": {"uri": {"fsPath": str(project)}},
                                },
                            ]
                        }),
                    ),
                )

            result = agent_session_options(config_path, agent="cursor", home=home)

        self.assertTrue(result.ok)
        sessions = result.payload["sessions"]
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["agent"], "cursor")
        self.assertEqual(sessions[0]["id"], "cursor-session-1")
        self.assertEqual(sessions[0]["project_path"], str(project))

    def test_kimi_project_bucket_sessions_are_exposed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project = root / "workspace"
            home = root / "home"
            config_path = self._write_config(project)

            bucket = hashlib.md5(str(project).encode("utf-8")).hexdigest()
            session_dir = home / ".kimi" / "sessions" / bucket / "kimi-session-1"
            session_dir.mkdir(parents=True)
            (session_dir / "state.json").write_text(
                json.dumps({
                    "custom_title": "Continue release checklist",
                    "archived": False,
                }),
                encoding="utf-8",
            )
            (session_dir / "context.jsonl").write_text("{}\n", encoding="utf-8")

            result = agent_session_options(config_path, agent="kimi-code", home=home)

        self.assertTrue(result.ok)
        sessions = result.payload["sessions"]
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["agent"], "kimi")
        self.assertEqual(sessions[0]["id"], "kimi-session-1")
        self.assertEqual(sessions[0]["label"], "Continue release checklist")


if __name__ == "__main__":
    unittest.main()
