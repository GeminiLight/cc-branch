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
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def test_plan_workspace_generates_basic_plan(self):
        """Test that plan_workspace generates a basic plan."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch.yaml",
                """
                version: 1
                project: "test"
                root: "."

                slots:
                  - name: "dev"
                    backend: "tmux"
                    windows:
                      - name: "editor"
                        command: "vim"
                """,
            )

            workspace = load_workspace(root / ".cc-branch.yaml")
            state = load_state(root / ".cc-branch.state.toml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            self.assertEqual(len(plan.slots), 1)
            self.assertEqual(plan.slots[0].name, "dev")

    def test_plan_workspace_resolves_tmux_session_names(self):
        """Test that plan_workspace resolves tmux session names."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch.yaml",
                """
                version: 1
                project: "myproject"
                root: "."

                slots:
                  - name: "dev"
                    backend: "tmux"
                    windows:
                      - name: "editor"
                        command: "vim"
                """,
            )

            workspace = load_workspace(root / ".cc-branch.yaml")
            state = load_state(root / ".cc-branch.state.toml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            self.assertEqual(plan.slots[0].tmux_session, "myproject-dev")

    def test_plan_workspace_bootstraps_session_ids(self):
        """Test that plan_workspace bootstraps session IDs when requested."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch.yaml",
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
                    backend: "tmux"
                    windows:
                      - name: "editor"
                        agent: "claude"
                """,
            )

            workspace = load_workspace(root / ".cc-branch.yaml")
            state = load_state(root / ".cc-branch.state.toml")
            plan = plan_workspace(workspace, state, bootstrap_missing=True)

            window = plan.slots[0].windows[0]
            self.assertIsNotNone(window.resolved_session_id)
            self.assertRegex(window.resolved_session_id, r"^[0-9a-f-]{36}$")

    def test_plan_workspace_uses_existing_session_ids(self):
        """Test that plan_workspace uses existing session IDs from state."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch.yaml",
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
                    backend: "tmux"
                    windows:
                      - name: "editor"
                        agent: "claude"
                """,
            )
            self._write(
                root / ".cc-branch.state.toml",
                """
                version = 1

                [windows."dev.editor"]
                session_id = "existing-session-id"
                label = "test/dev/editor"
                """,
            )

            workspace = load_workspace(root / ".cc-branch.yaml")
            state = load_state(root / ".cc-branch.state.toml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            window = plan.slots[0].windows[0]
            self.assertEqual(window.resolved_session_id, "existing-session-id")

    def test_plan_workspace_resolves_labels(self):
        """Test that plan_workspace resolves labels correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch.yaml",
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
                    backend: "tmux"
                    windows:
                      - name: "editor"
                        agent: "claude"
                """,
            )

            workspace = load_workspace(root / ".cc-branch.yaml")
            state = load_state(root / ".cc-branch.state.toml")
            plan = plan_workspace(workspace, state, bootstrap_missing=True)

            window = plan.slots[0].windows[0]
            self.assertEqual(window.resolved_label, "myproject/dev/editor")

    def test_plan_workspace_handles_shell_backend(self):
        """Test that plan_workspace handles shell backend correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch.yaml",
                """
                version: 1
                project: "test"
                root: "."

                slots:
                  - name: "scratch"
                    backend: "shell"
                    command: "bash"
                """,
            )

            workspace = load_workspace(root / ".cc-branch.yaml")
            state = load_state(root / ".cc-branch.state.toml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            slot = plan.slots[0]
            self.assertEqual(slot.backend, "shell")
            self.assertEqual(len(slot.windows), 1)
            self.assertEqual(slot.windows[0].name, "main")

    def test_plan_workspace_resolves_cwd(self):
        """Test that plan_workspace resolves working directories."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "subdir").mkdir()
            self._write(
                root / ".cc-branch.yaml",
                """
                version: 1
                project: "test"
                root: "."

                slots:
                  - name: "dev"
                    backend: "tmux"
                    cwd: "subdir"
                    windows:
                      - name: "editor"
                        command: "vim"
                """,
            )

            workspace = load_workspace(root / ".cc-branch.yaml")
            state = load_state(root / ".cc-branch.state.toml")
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
                    "backend": "tmux",
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
                root / ".cc-branch.yaml",
                """
                version: 1
                project: "test"
                root: "."

                slots:
                  - name: "dev"
                    backend: "shell"
                    command: "python server.py"
                    env:
                      DEBUG: "true"
                      PORT: 8080
                """,
            )

            workspace = load_workspace(root / ".cc-branch.yaml")
            state = load_state(root / ".cc-branch.state.toml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            launch_command = plan.slots[0].windows[0].launch_command
            self.assertIn("env ", launch_command)
            self.assertIn("DEBUG=", launch_command)


if __name__ == '__main__':
    unittest.main()
