import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from cc_branch.config import load_workspace
from cc_branch.doctor import (
    auto_fix_issues,
    build_doctor_report,
    collect_doctor_report,
    render_doctor_report,
)
from cc_branch.models import DoctorReport
from cc_branch.planner import plan_workspace
from cc_branch.state import load_state


class DoctorTests(unittest.TestCase):
    """Tests for workspace diagnostics functionality."""

    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def test_doctor_reports_missing_session_id(self):
        """Test that doctor reports missing session IDs for resume-only agents."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "test"
                root: "."

                agents:
                  codex:
                    command: "codex"
                    resume_mode: "flag"
                    resume_template: "resume {session_id}"

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "editor"
                        agent: "codex"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            report = build_doctor_report(workspace, plan)

            self.assertIn("missing session_id", report.lower())

    def test_command_override_does_not_require_agent_session_id(self):
        """Explicit commands can keep agent metadata without using agent resume."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "test"
                root: "."

                agents:
                  codex:
                    command: "codex"
                    resume_mode: "flag"
                    resume_template: "resume {session_id}"
                    label_template: "{project}/{slot}/{window}"

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "shell"
                        agent: "codex"
                        command: "zsh"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            report = build_doctor_report(workspace, plan)

            self.assertNotIn("missing session_id", report.lower())

    def test_doctor_reports_unknown_agent(self):
        """Test that doctor reports unknown agent references."""
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
                        agent: "nonexistent-agent"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            report = build_doctor_report(workspace, plan)

            self.assertIn("unknown agent", report.lower())

    def test_doctor_reports_missing_cwd(self):
        """Test that doctor reports missing working directories."""
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
                    cwd: "nonexistent-directory"
                    windows:
                      - name: "editor"
                        command: "vim"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            report = build_doctor_report(workspace, plan)

            self.assertIn("missing cwd", report.lower())

    def test_doctor_reports_duplicate_slots(self):
        """Test that doctor reports duplicate slot names."""
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
                  - name: "dev"
                    runtime: "terminal"
                    command: "bash"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            report = build_doctor_report(workspace, plan)

            self.assertIn("duplicate", report.lower())

    def test_doctor_normalizes_names_before_duplicate_checks(self):
        """Doctor should report names that only differ by surrounding spaces as duplicates."""
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
                      - name: " editor "
                        command: "zsh"
                  - name: " dev "
                    runtime: "terminal"
                    command: "bash"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            report = build_doctor_report(workspace, plan)

            self.assertIn("duplicate slot 'dev'", report.lower())
            self.assertIn("duplicate window 'editor'", report.lower())

    def test_doctor_reports_duplicate_windows(self):
        """Test that doctor reports duplicate window names within a slot."""
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
                      - name: "editor"
                        command: "emacs"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            report = build_doctor_report(workspace, plan)

            self.assertIn("duplicate window", report.lower())

    def test_doctor_reports_invalid_env_keys(self):
        """Test that doctor reports invalid environment variable keys."""
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
                    command: "bash"
                    env:
                      INVALID-KEY: "value"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            report = build_doctor_report(workspace, plan)

            self.assertIn("invalid env key", report.lower())

    def test_doctor_reports_missing_command(self):
        """Test that doctor reports missing executable commands."""
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
                        command: "definitely-nonexistent-command-12345"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            report = build_doctor_report(workspace, plan)

            self.assertIn("missing command", report.lower())

    def test_doctor_passes_valid_configuration(self):
        """Test that doctor passes a valid configuration without errors."""
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
                        command: "echo"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            report = build_doctor_report(workspace, plan)

            # Report should not contain common error keywords
            report_lower = report.lower()
            self.assertNotIn("error", report_lower)
            self.assertNotIn("missing", report_lower)
            self.assertNotIn("invalid", report_lower)

    def test_doctor_returns_string(self):
        """Test that build_doctor_report returns a string."""
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
            report = build_doctor_report(workspace, plan)

            self.assertIsInstance(report, str)
            self.assertGreater(len(report), 0)

    def test_doctor_collects_structured_report_before_rendering(self):
        """Doctor should expose structured issues separately from text rendering."""
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
                        agent: "nonexistent-agent"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            report = collect_doctor_report(workspace, plan)
            rendered = render_doctor_report(report)

            self.assertIsInstance(report, DoctorReport)
            self.assertTrue(any(issue.issue_type == "unknown_agent" for issue in report.issues))
            self.assertIn("unknown agent", rendered.lower())

    def test_doctor_fix_bootstraps_generated_uuid_sessions(self):
        """doctor --fix path should write session IDs using the current windows state schema."""
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
                    resume_mode: "flag"
                    resume_template: "-r {session_id}"
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
            state_path = root / ".cc-branch/state.yaml"
            state = load_state(state_path)
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            def which_mock(command: str):
                if command in {"tmux", "claude"}:
                    return f"/usr/bin/{command}"
                return None

            with patch("cc_branch.doctor.which", side_effect=which_mock), patch("pathlib.Path.cwd", return_value=root):
                fixed = auto_fix_issues(workspace, plan, state_path)

            self.assertTrue(fixed)
            updated_state = load_state(state_path)
            self.assertIn("dev.editor", updated_state.windows)
            self.assertRegex(
                updated_state.windows["dev.editor"].session_id,
                r"^[0-9a-f-]{36}$",
            )


if __name__ == '__main__':
    unittest.main()
