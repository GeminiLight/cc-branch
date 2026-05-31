import tempfile
import textwrap
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from cc_branch.application.agent_sessions import AgentSessionOption
from cc_branch.application.session_binding import bind_discovered_agent_sessions
from cc_branch.config import load_workspace
from cc_branch.models import AppliedWindowResult
from cc_branch.planner import plan_workspace
from cc_branch.runtime.sync import record_applied_results
from cc_branch.state import load_state


class SessionBindingTests(unittest.TestCase):
    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def _workspace_plan_state(self, root: Path):
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
        workspace = load_workspace(root / ".cc-branch/config.yaml")
        state = load_state(root / ".cc-branch/state.yaml")
        plan = plan_workspace(workspace, state, bootstrap_missing=False)
        return workspace, plan, state

    def test_auto_session_binds_recent_discovered_agent_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, plan, state = self._workspace_plan_state(root)
            result = AppliedWindowResult(
                slot="dev",
                window="planner",
                key="dev.planner",
                runtime="tmux",
                tmux_session="demo-dev",
                action="created",
            )
            discovered = [
                AgentSessionOption(
                    agent="codex",
                    id="codex-session-1",
                    label="Working on demo",
                    updated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    source=str(root / "session.jsonl"),
                    project_path=str(root),
                )
            ]

            with patch(
                "cc_branch.application.session_binding.agent_session_options_for_project",
                return_value=discovered,
            ):
                next_state, outcomes = bind_discovered_agent_sessions(
                    state,
                    workspace,
                    plan,
                    [result],
                    project_dir=root,
                    poll_timeout=0,
                )

            entry = next_state.windows["dev.planner"]
            self.assertEqual(entry.session_id, "codex-session-1")
            self.assertEqual(entry.session_binding_status, "bound")
            self.assertEqual(entry.session_binding_source, str(root / "session.jsonl"))
            self.assertEqual(outcomes[0].status, "bound")

    def test_auto_session_remains_pending_when_no_session_is_discovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, plan, state = self._workspace_plan_state(root)
            result = AppliedWindowResult(
                slot="dev",
                window="planner",
                key="dev.planner",
                runtime="tmux",
                tmux_session="demo-dev",
                action="created",
            )

            with patch(
                "cc_branch.application.session_binding.agent_session_options_for_project",
                return_value=[],
            ):
                next_state, outcomes = bind_discovered_agent_sessions(
                    state,
                    workspace,
                    plan,
                    [result],
                    project_dir=root,
                    poll_timeout=0,
                )

            entry = next_state.windows["dev.planner"]
            self.assertIsNone(entry.session_id)
            self.assertEqual(entry.session_binding_status, "pending_capture")
            self.assertEqual(outcomes[0].status, "pending_capture")

    def test_fresh_session_clears_previous_binding_on_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
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
                        session: fresh
                """,
            )
            self._write(
                root / ".cc-branch/state.yaml",
                """
                version: 1
                windows:
                  dev.planner:
                    session_id: old-session
                    agent: codex
                    slot: dev
                    window: planner
                    session_binding_status: bound
                """,
            )
            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            result = AppliedWindowResult(
                slot="dev",
                window="planner",
                key="dev.planner",
                runtime="tmux",
                tmux_session="demo-dev",
                action="created",
            )

            next_state = record_applied_results(state, workspace, plan, [result])

            entry = next_state.windows["dev.planner"]
            self.assertIsNone(entry.session_id)
            self.assertEqual(entry.session_binding_status, "fresh")


if __name__ == "__main__":
    unittest.main()
