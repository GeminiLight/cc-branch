import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from unittest.mock import patch

from cc_branch.application.session_hooks import SessionHookEvent, apply_session_hook_event
from cc_branch.cli import main
from cc_branch.models import WindowState, WorkspaceState
from cc_branch.state import load_state, save_state


class SessionHookTests(unittest.TestCase):
    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def _write_workspace(self, root: Path) -> None:
        self._write(
            root / ".cc-branch/config.yaml",
            """
            version: 2
            project: demo
            root: .

            agents:
              codex:
                command: codex
                resume_mode: flag
                resume_template: resume {session_id}

            tabs:
              - name: dev
                panes:
                  - name: planner
                    agent: codex
            """,
        )

    def test_session_hook_started_binds_session_and_transcript_to_existing_pane(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / ".cc-branch/state.yaml"
            save_state(
                state_path,
                WorkspaceState(
                    windows={
                        "dev.planner": WindowState(
                            agent="codex",
                            slot="dev",
                            window="planner",
                            session_binding_status="pending_capture",
                        )
                    }
                ),
            )

            updated = apply_session_hook_event(
                state_path,
                SessionHookEvent(
                    key="dev.planner",
                    agent="codex",
                    event="started",
                    session_id="codex-session-1",
                    transcript_path=str(root / "transcript.jsonl"),
                    label="Working on planner",
                    pid=1234,
                    timestamp="2026-06-06T01:02:03Z",
                ),
            )

            entry = updated.windows["dev.planner"]
            self.assertEqual(entry.session_id, "codex-session-1")
            self.assertEqual(entry.session_binding_status, "bound")
            self.assertEqual(entry.session_binding_source, str(root / "transcript.jsonl"))
            self.assertEqual(entry.session_hook_event, "started")
            self.assertEqual(entry.session_runtime_status, "running")
            self.assertEqual(entry.session_transcript_path, str(root / "transcript.jsonl"))
            self.assertEqual(entry.session_pid, 1234)
            self.assertEqual(entry.session_hook_updated_at, "2026-06-06T01:02:03Z")

    def test_session_hook_exited_preserves_session_id_and_marks_runtime_stopped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / ".cc-branch/state.yaml"
            save_state(
                state_path,
                WorkspaceState(
                    windows={
                        "dev.planner": WindowState(
                            session_id="codex-session-1",
                            agent="codex",
                            slot="dev",
                            window="planner",
                            session_binding_status="bound",
                            session_runtime_status="running",
                        )
                    }
                ),
            )

            updated = apply_session_hook_event(
                state_path,
                SessionHookEvent(
                    key="dev.planner",
                    agent="codex",
                    event="exited",
                    exit_code=0,
                    timestamp="2026-06-06T01:05:00Z",
                ),
            )

            entry = updated.windows["dev.planner"]
            self.assertEqual(entry.session_id, "codex-session-1")
            self.assertEqual(entry.session_hook_event, "exited")
            self.assertEqual(entry.session_runtime_status, "stopped")
            self.assertEqual(entry.session_exit_code, 0)
            self.assertEqual(entry.session_hook_updated_at, "2026-06-06T01:05:00Z")

    def test_session_hook_cli_accepts_colon_target_and_updates_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main([
                    "--project",
                    str(root),
                    "session",
                    "hook",
                    "dev:planner",
                    "--event",
                    "started",
                    "--agent",
                    "codex",
                    "--session-id",
                    "codex-session-cli",
                    "--transcript",
                    str(root / "codex.jsonl"),
                    "--format",
                    "json",
                ])

            self.assertEqual(exit_code, 0)
            payload = stdout.getvalue()
            self.assertIn("codex-session-cli", payload)
            state = load_state(root / ".cc-branch/state.yaml")
            entry = state.windows["dev.planner"]
            self.assertEqual(entry.session_id, "codex-session-cli")
            self.assertEqual(entry.session_binding_status, "bound")
            self.assertEqual(entry.session_runtime_status, "running")

    def test_session_restore_cli_scans_local_transcripts_and_updates_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            self._write_workspace(root)
            transcript = home / ".codex" / "sessions" / "2026" / "06" / "12" / "rollout-current.jsonl"
            transcript.parent.mkdir(parents=True)
            transcript.write_text(
                json.dumps({
                    "timestamp": "2026-06-12T01:00:00Z",
                    "type": "session_meta",
                    "payload": {"id": "codex-session-scan", "cwd": str(root)},
                }) + "\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            with patch("pathlib.Path.home", return_value=home), redirect_stdout(stdout):
                exit_code = main([
                    "--project",
                    str(root),
                    "session",
                    "restore",
                    "--format",
                    "json",
                ])

            payload = json.loads(stdout.getvalue())
            state = load_state(root / ".cc-branch/state.yaml")

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["code"], "sessions_restored")
        self.assertEqual(payload["changed_targets"], ["dev:planner"])
        self.assertEqual(state.windows["dev.planner"].session_id, "codex-session-scan")


if __name__ == "__main__":
    unittest.main()
