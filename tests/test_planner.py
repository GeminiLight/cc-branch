import tempfile
import textwrap
import unittest
from pathlib import Path

from cc_branch.config import load_workspace
from cc_branch.models import WorkspacePlan
from cc_branch.planner import format_plan, plan_workspace
from cc_branch.state import load_state


class PlannerTests(unittest.TestCase):
    """Tests for workspace planning functionality."""

    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def test_plan_workspace_generates_basic_plan(self):
        """Test that plan_workspace generates a basic plan."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "test"
                root: "."

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "editor"
                        command: "vim"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            self.assertEqual(len(plan.slots), 1)
            self.assertEqual(plan.slots[0].name, "dev")

    def test_plan_workspace_resolves_tmux_session_names(self):
        """Test that plan_workspace resolves tmux session names."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "myproject"
                root: "."

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "editor"
                        command: "vim"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            self.assertEqual(plan.slots[0].tmux_session, "myproject-dev")

    def test_plan_workspace_bootstraps_session_ids(self):
        """Test that plan_workspace bootstraps session IDs when requested."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "test"
                root: "."

                agents:
                  claude:
                    command: "claude"
                    create_mode: "generated_uuid"
                    create_template: "claude --session-id {session_id}"

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "editor"
                        agent: "claude"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=True)

            window = plan.slots[0].windows[0]
            self.assertIsNotNone(window.resolved_session_id)
            self.assertRegex(window.resolved_session_id, r"^[0-9a-f-]{36}$")

    def test_plan_workspace_uses_existing_session_ids(self):
        """Test that plan_workspace uses existing session IDs from state."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "test"
                root: "."

                agents:
                  claude:
                    command: "claude"
                    resume_mode: "flag"
                    resume_template: "--resume {session_id}"

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "editor"
                        agent: "claude"
                """,
            )
            self._write(
                root / ".cc-branch/state.yaml",
                """
                version: 1
                windows:
                  dev.editor:
                    session_id: "existing-session-id"
                    label: "test/dev/editor"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            window = plan.slots[0].windows[0]
            self.assertEqual(window.resolved_session_id, "existing-session-id")

    def test_plan_workspace_explicit_session_value_resumes_that_session(self):
        """A non-keyword session value is treated as the real agent session id."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 2
                project: "test"
                root: "."

                tabs:
                  - name: "dev"
                    panes:
                      - name: "planner"
                        runtime: "tmux"
                        agent: "codex"
                        session: "codex-session-123"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            window = plan.slots[0].windows[0]
            self.assertEqual(window.resolved_session_id, "codex-session-123")
            self.assertEqual(window.launch_command, "codex resume codex-session-123")

    def test_plan_workspace_fresh_session_ignores_existing_state_session(self):
        """session: fresh means start clean and do not bind the old state session."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 2
                project: "test"
                root: "."

                tabs:
                  - name: "dev"
                    panes:
                      - name: "planner"
                        runtime: "tmux"
                        agent: "codex"
                        session: "fresh"
                """,
            )
            self._write(
                root / ".cc-branch/state.yaml",
                """
                version: 1
                windows:
                  dev.planner:
                    session_id: "old-session-id"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            window = plan.slots[0].windows[0]
            self.assertIsNone(window.resolved_session_id)
            self.assertEqual(window.launch_command, "codex")
            self.assertNotIn("session_id", plan.state_updates.get("dev.planner", {}))

    def test_plan_workspace_auto_session_uses_bound_state_session(self):
        """session: auto keeps the default reuse-or-create behavior explicit."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 2
                project: "test"
                root: "."

                tabs:
                  - name: "dev"
                    panes:
                      - name: "planner"
                        runtime: "tmux"
                        agent: "codex"
                        session: "auto"
                """,
            )
            self._write(
                root / ".cc-branch/state.yaml",
                """
                version: 1
                windows:
                  dev.planner:
                    session_id: "bound-session-id"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            window = plan.slots[0].windows[0]
            self.assertEqual(window.resolved_session_id, "bound-session-id")
            self.assertEqual(window.launch_command, "codex resume bound-session-id")

    def test_plan_workspace_resolves_labels(self):
        """Test that plan_workspace resolves labels correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "myproject"
                root: "."

                agents:
                  claude:
                    command: "claude"
                    label_template: "{project}/{slot}/{window}"

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "editor"
                        agent: "claude"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=True)

            window = plan.slots[0].windows[0]
            self.assertEqual(window.resolved_label, "myproject/dev/editor")

    def test_plan_workspace_handles_terminal_runtime(self):
        """Test that plan_workspace handles terminal runtime correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "test"
                root: "."

                slots:
                  - name: "scratch"
                    runtime: "terminal"
                    command: "bash"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            slot = plan.slots[0]
            self.assertEqual(slot.runtime, "terminal")
            self.assertEqual(len(slot.windows), 1)
            self.assertEqual(slot.windows[0].name, "main")

    def test_terminal_runtime_uses_all_configured_panes(self):
        """Terminal tabs launch every configured pane as a visible process."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 2
                project: "test"
                root: "."

                tabs:
                  - name: "scratch"
                    panes:
                      - name: "one"
                        command: "echo one"
                      - name: "two"
                        command: "echo two"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            slot = plan.slots[0]
            self.assertEqual(slot.runtime, "terminal")
            self.assertEqual(len(slot.windows), 2)
            self.assertEqual(slot.windows[0].name, "one")
            self.assertEqual(slot.windows[0].launch_command, "echo one")
            self.assertEqual(slot.windows[1].name, "two")
            self.assertEqual(slot.windows[1].launch_command, "echo two")

    def test_plan_workspace_resolves_cwd(self):
        """Test that plan_workspace resolves working directories."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "subdir").mkdir()
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "test"
                root: "."

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    cwd: "subdir"
                    windows:
                      - name: "editor"
                        command: "vim"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            window = plan.slots[0].windows[0]
            self.assertEqual(window.cwd, str((root / "subdir").resolve()))

    def test_format_plan_returns_string(self):
        """Test that format_plan returns a formatted string."""
        plan = WorkspacePlan.from_dict({
            "project": "test",
            "slots": [
                {
                    "name": "dev",
                    "runtime": "tmux",
                    "tmux_session": "test-dev",
                    "windows": [
                        {
                            "name": "editor",
                            "launch_command": "vim",
                            "resolved_session_id": "test-session",
                            "resolved_label": "test-label",
                            "bootstrapped": True,
                            "post_launch_commands": [],
                        }
                    ],
                }
            ]
        })

        formatted = format_plan(plan)
        self.assertIsInstance(formatted, str)
        self.assertIn("dev", formatted)

    def test_plan_workspace_applies_env_variables(self):
        """Test that plan_workspace applies environment variables."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "test"
                root: "."

                slots:
                  - name: "dev"
                    runtime: "terminal"
                    command: "python server.py"
                    env:
                      DEBUG: "true"
                      PORT: 8080
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            launch_command = plan.slots[0].windows[0].launch_command
            self.assertIn("env ", launch_command)
            self.assertIn("DEBUG=", launch_command)


if __name__ == '__main__':
    unittest.main()
