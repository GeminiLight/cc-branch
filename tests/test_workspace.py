import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from cc_branch.models import WorkspaceConfig, WorkspacePlan


class WorkspacePlannerTests(unittest.TestCase):
    """Workspace integration tests for YAML workspace files."""

    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]

    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def test_plan_bootstraps_generated_session_id_and_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: demo
                root: .
                agents:
                  claude:
                    command: claude
                    create_mode: generated_uuid
                    create_template: claude --session-id {session_id}
                    resume_mode: flag
                    resume_template: --resume {session_id}
                    label_template: '{project}/{slot}/{window}'
                slots:
                - name: dev
                  runtime: tmux
                  windows:
                  - name: planner
                    agent: claude
                """,
            )

            from cc_branch import load_state, load_workspace, plan_workspace

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=True)

            window = plan.slots[0].windows[0]
            self.assertEqual(window.resolved_label, "demo/dev/planner")
            self.assertRegex(window.resolved_session_id, r"^[0-9a-f-]{36}$")
            self.assertIn("--session-id", window.launch_command)

    def test_plan_prefers_existing_state_session_id_for_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: demo
                root: .
                agents:
                  codex:
                    command: codex
                    resume_mode: flag
                    resume_template: resume {session_id}
                    label_template: '{project}/{slot}/{window}'
                slots:
                - name: research
                  runtime: tmux
                  windows:
                  - name: writer
                    agent: codex
                """,
            )
            self._write(
                root / ".cc-branch/state.yaml",
                """
                version: 1
                windows:
                  research.writer:
                    session_id: 11111111-1111-1111-1111-111111111111
                    label: demo/research/writer
                """,
            )

            from cc_branch import load_state, load_workspace, plan_workspace

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            window = plan.slots[0].windows[0]
            self.assertEqual(
                window.resolved_session_id, "11111111-1111-1111-1111-111111111111"
            )
            self.assertEqual(window.launch_command, "codex resume 11111111-1111-1111-1111-111111111111")

    def test_save_state_round_trips_bootstrapped_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / ".cc-branch/state.yaml"

            from cc_branch import load_state, save_state
            from cc_branch.models import WindowState, WorkspaceState

            save_state(
                state_path,
                WorkspaceState(
                    version=1,
                    windows={
                        "dev.planner": WindowState(
                            session_id="22222222-2222-2222-2222-222222222222",
                            label="demo/dev/planner",
                            agent="claude",
                        )
                    },
                ),
            )

            state = load_state(state_path)
            self.assertEqual(
                state.windows["dev.planner"].session_id,
                "22222222-2222-2222-2222-222222222222",
            )
            self.assertEqual(state.windows["dev.planner"].label, "demo/dev/planner")

    def test_shell_slot_becomes_single_main_window_in_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: demo
                root: .
                slots:
                - name: scratch
                  runtime: terminal
                  command: zsh
                """,
            )

            from cc_branch import load_state, load_workspace, plan_workspace

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            slot = plan.slots[0]
            self.assertEqual(slot.runtime, "terminal")
            self.assertEqual(len(slot.windows), 1)
            self.assertEqual(slot.windows[0].name, "main")
            self.assertEqual(slot.windows[0].launch_command, "zsh")

    def test_init_bootstrap_populates_state_for_supported_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            from cc_branch import init_workspace, load_state

            config_path, state_path = init_workspace(root, force=False, bootstrap_sessions=True)

            self.assertTrue(config_path.exists())
            self.assertTrue(state_path.exists())

            state = load_state(state_path)
            self.assertIn("dev.review", state.windows)
            self.assertRegex(
                state.windows["dev.review"].session_id,
                r"^[0-9a-f-]{36}$",
            )
            self.assertEqual(state.windows["dev.review"].label, f"{root.name}/dev/review")

    def test_apply_workspace_creates_tmux_sessions_for_tmux_and_shell_slots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: demo
                root: .
                slots:
                - name: dev
                  runtime: tmux
                  windows:
                  - name: planner
                    command: printf planner-ready
                - name: scratch
                  runtime: terminal
                  command: printf shell-ready
                """,
            )

            from cc_branch import load_state, load_workspace, plan_workspace
            from cc_branch.runtime import apply_workspace

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            try:
                with patch("cc_branch.runtime.execution.open_command") as open_command:
                    apply_workspace(plan, detach=True)
                sessions = subprocess.check_output(
                    ["tmux", "list-sessions", "-F", "#{session_name}"],
                    text=True,
                ).splitlines()
                self.assertIn("demo-dev", sessions)
                self.assertNotIn("demo-scratch", sessions)
                open_command.assert_called_once()
            finally:
                subprocess.run(["tmux", "kill-session", "-t", "demo-dev"], check=False)

    def test_cc_branch_shell_wrapper_initializes_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = subprocess.run(
                [str(self.repo_root / "bin" / "cc-branch"), "init"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn(".cc-branch/config.yaml", result.stdout)
            self.assertTrue((root / ".cc-branch/config.yaml").exists())
            self.assertTrue((root / ".cc-branch/state.yaml").exists())

    def test_doctor_reports_missing_session_id_for_resume_only_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: demo
                root: .
                agents:
                  codex:
                    command: codex
                    resume_mode: flag
                    resume_template: resume {session_id}
                slots:
                - name: dev
                  runtime: tmux
                  windows:
                  - name: planner
                    agent: codex
                """,
            )

            from cc_branch import load_state, load_workspace, plan_workspace
            from cc_branch.doctor import build_doctor_report

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            report = build_doctor_report(workspace, plan)

            self.assertIn("missing session_id", report)

    def test_plan_applies_env_to_launch_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: demo
                root: .
                slots:
                - name: scratch
                  runtime: terminal
                  env:
                    APP_MODE: local dev
                    PORT: 8123
                  command: python -m http.server
                """,
            )

            from cc_branch import load_state, load_workspace, plan_workspace

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            launch_command = plan.slots[0].windows[0].launch_command
            self.assertIn("env ", launch_command)
            self.assertIn("APP_MODE='local dev'", launch_command)
            self.assertIn("PORT=8123", launch_command)
            self.assertTrue(launch_command.endswith("python -m http.server"))

    def test_window_command_overrides_agent_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: demo
                root: .
                agents:
                  codex:
                    command: codex
                    resume_mode: flag
                    resume_template: resume {session_id}
                slots:
                - name: dev
                  runtime: tmux
                  windows:
                  - name: planner
                    agent: codex
                    command: python custom.py
                """,
            )

            from cc_branch import load_state, load_workspace, plan_workspace

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            launch_command = plan.slots[0].windows[0].launch_command
            self.assertEqual(launch_command, "python custom.py")

    def test_window_cwd_resolves_relative_to_slot_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "apps" / "api" / "docs").mkdir(parents=True)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: demo
                root: .
                slots:
                - name: dev
                  runtime: tmux
                  cwd: apps/api
                  windows:
                  - name: planner
                    command: pwd
                    cwd: docs
                """,
            )

            from cc_branch import load_state, load_workspace, plan_workspace

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            cwd = plan.slots[0].windows[0].cwd
            self.assertEqual(cwd, str((root / "apps" / "api" / "docs").resolve()))

    def test_attach_slot_accepts_window_target(self) -> None:
        from cc_branch.runtime import attach_slot

        plan = WorkspacePlan.from_dict({
            "slots": [
                {
                    "name": "dev",
                    "tmux_session": "demo-dev",
                    "windows": [{"name": "planner"}, {"name": "review"}],
                }
            ]
        })

        with patch("cc_branch.runtime.subprocess.run") as run_mock:
            attach_slot(plan, "dev:review")

        run_mock.assert_called_once_with(
            ["tmux", "attach-session", "-t", "demo-dev:review"],
            check=True,
        )

    def test_doctor_reports_unknown_agent_and_missing_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_dir = root / "does-not-exist"
            self._write(
                root / ".cc-branch/config.yaml",
                f"""
                version: 1
                project: demo
                root: .
                slots:
                  - name: dev
                    runtime: tmux
                    cwd: "{missing_dir.name}"
                    windows:
                      - name: planner
                        agent: missing-agent
                """,
            )

            from cc_branch import load_state, load_workspace, plan_workspace
            from cc_branch.doctor import build_doctor_report

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            report = build_doctor_report(workspace, plan)

            self.assertIn("unknown agent 'missing-agent'", report)
            self.assertIn("missing cwd", report)

    def test_doctor_reports_duplicate_slots_and_invalid_window_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: demo
                root: .
                slots:
                - name: dev
                  runtime: tmux
                  windows:
                  - name: dup
                    command: python -m http.server
                    env:
                      BAD-KEY: x
                  - name: dup
                    command: definitely-missing-command
                - name: dev!
                  runtime: tmux
                  windows:
                  - name: main
                    command: zsh
                """,
            )

            from cc_branch import load_state, load_workspace, plan_workspace
            from cc_branch.doctor import build_doctor_report

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            report = build_doctor_report(workspace, plan)

            self.assertIn("duplicate tmux session 'demo-dev'", report)
            self.assertIn("duplicate window 'dup'", report)
            self.assertIn("invalid env key 'BAD-KEY'", report)
            self.assertIn("missing command 'definitely-missing-command'", report)

    def test_stop_workspace_accepts_window_target(self) -> None:
        from cc_branch.runtime import stop_workspace

        workspace = WorkspaceConfig.from_dict({"project": "demo"})
        plan = WorkspacePlan.from_dict({
            "slots": [
                {
                    "name": "dev",
                    "tmux_session": "demo-dev",
                    "windows": [{"name": "planner"}, {"name": "review"}],
                }
            ]
        })

        with (
            patch("cc_branch.runtime.which", return_value="/usr/bin/tmux"),
            patch("cc_branch.runtime.execution._kill_dashboard") as kill_dashboard_mock,
            patch("cc_branch.runtime.execution.tmux_has_window", return_value=True),
            patch("cc_branch.runtime.subprocess.run") as run_mock,
        ):
            stop_workspace(workspace, plan, "dev:review")

        kill_dashboard_mock.assert_called_once_with(workspace)
        run_mock.assert_called_once_with(
            ["tmux", "kill-window", "-t", "demo-dev:review"],
            check=True,
        )

    def test_restart_workspace_recreates_slot_detached(self) -> None:
        from cc_branch.runtime import restart_workspace

        workspace = WorkspaceConfig.from_dict({"project": "demo"})
        plan = WorkspacePlan.from_dict({
            "slots": [
                {
                    "name": "dev",
                    "tmux_session": "demo-dev",
                    "windows": [{"name": "planner"}],
                }
            ]
        })

        with (
            patch("cc_branch.runtime.which", return_value="/usr/bin/tmux"),
            patch("cc_branch.runtime.execution._kill_dashboard") as kill_dashboard_mock,
            patch("cc_branch.runtime.execution.tmux_has_session", return_value=True),
            patch("cc_branch.runtime.execution.ensure_slot") as ensure_slot_mock,
            patch("cc_branch.runtime.execution.attach_slot") as attach_slot_mock,
            patch("cc_branch.runtime.subprocess.run") as run_mock,
        ):
            restart_workspace(workspace, plan, "dev", detach=True)

        kill_dashboard_mock.assert_called_once_with(workspace)
        run_mock.assert_called_once_with(
            ["tmux", "kill-session", "-t", "demo-dev"],
            check=True,
        )
        ensure_slot_mock.assert_called_once_with(plan.slots[0], created_action="recreated")
        attach_slot_mock.assert_not_called()

    def test_dashboard_layout_uses_display_mode_and_columns(self) -> None:
        from cc_branch.runtime import _dashboard_layout

        self.assertEqual(_dashboard_layout(WorkspaceConfig.from_dict({"display": {"mode": "columns"}}), 3), "even-horizontal")
        self.assertEqual(_dashboard_layout(WorkspaceConfig.from_dict({"display": {"mode": "rows"}}), 3), "even-vertical")
        self.assertEqual(_dashboard_layout(WorkspaceConfig.from_dict({"display": {"mode": "grid", "columns": 1}}), 3), "even-vertical")
        self.assertEqual(_dashboard_layout(WorkspaceConfig.from_dict({"display": {"mode": "grid", "columns": 5}}), 3), "even-horizontal")
        self.assertEqual(_dashboard_layout(WorkspaceConfig.from_dict({"display": {"mode": "grid", "columns": 2}}), 4), "tiled")

    def test_open_dashboard_applies_layout_from_display_config(self) -> None:
        from cc_branch.runtime import open_dashboard

        workspace = WorkspaceConfig.from_dict({"project": "demo", "display": {"mode": "rows", "columns": 2}})
        plan = WorkspacePlan.from_dict({
            "slots": [
                {"tmux_session": "demo-dev"},
                {"tmux_session": "demo-review"},
            ]
        })

        with (
            patch("cc_branch.runtime.which", return_value="/usr/bin/tmux"),
            patch("cc_branch.runtime.execution.apply_workspace"),
            patch("cc_branch.runtime.execution.tmux_has_session", return_value=False),
            patch("cc_branch.runtime.subprocess.run") as run_mock,
        ):
            open_dashboard(workspace, plan)

        self.assertIn(
            (("tmux", "select-layout", "-t", "demo-dashboard:grid", "even-vertical"), {"check": True}),
            [((tuple(call.args[0])), call.kwargs) for call in run_mock.call_args_list],
        )

    def test_open_dashboard_uses_shell_wrapper_helper(self) -> None:
        from cc_branch.runtime import open_dashboard

        workspace = WorkspaceConfig.from_dict({"project": "demo", "display": {"mode": "grid", "columns": 2}})
        plan = WorkspacePlan.from_dict({
            "slots": [
                {"tmux_session": "demo-dev"},
                {"tmux_session": "demo-review"},
            ]
        })

        with (
            patch("cc_branch.runtime.which", return_value="/usr/bin/tmux"),
            patch("cc_branch.runtime.execution.apply_workspace"),
            patch("cc_branch.runtime.execution.tmux_has_session", return_value=False),
            patch(
                "cc_branch.runtime.execution.tmux_attach_shell_command",
                side_effect=lambda target: ["shell", "-c", f"attach {target}"],
            ),
            patch("cc_branch.runtime.subprocess.run") as run_mock,
        ):
            open_dashboard(workspace, plan)

        run_calls = [tuple(call.args[0]) for call in run_mock.call_args_list]
        self.assertIn(
            ("tmux", "new-session", "-d", "-s", "demo-dashboard", "-n", "grid", "shell", "-c", "attach demo-dev"),
            run_calls,
        )
        self.assertIn(
            ("tmux", "split-window", "-t", "demo-dashboard:grid", "shell", "-c", "attach demo-review"),
            run_calls,
        )

    def test_open_dashboard_does_not_open_terminal_runtime_slots(self) -> None:
        from cc_branch.runtime import open_dashboard

        workspace = WorkspaceConfig.from_dict({"project": "demo"})
        plan = WorkspacePlan.from_dict({
            "slots": [
                {
                    "name": "dev",
                    "runtime": "tmux",
                    "tmux_session": "demo-dev",
                    "windows": [{"name": "main", "launch_command": "zsh"}],
                },
                {
                    "name": "scratch",
                    "runtime": "terminal",
                    "tmux_session": "demo-scratch",
                    "windows": [{"name": "main", "launch_command": "zsh"}],
                },
            ]
        })

        with (
            patch("cc_branch.runtime.which", return_value="/usr/bin/tmux"),
            patch("cc_branch.runtime.execution.tmux_has_session", return_value=False),
            patch("cc_branch.runtime.execution.open_command") as open_command,
            patch("cc_branch.runtime.subprocess.run"),
        ):
            open_dashboard(workspace, plan)

        open_command.assert_not_called()

    def test_start_does_not_use_dashboard_implicitly_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: demo
                root: .
                display:
                  dashboard: true
                slots:
                - name: dev
                  runtime: terminal
                  command: zsh
                """,
            )

            from cc_branch.application.results import ActionResult
            from cc_branch.cli import main

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.cli.open_dashboard_workspace_action") as open_dashboard_mock,
                patch("cc_branch.cli.start_workspace_action") as start_workspace_mock,
            ):
                start_workspace_mock.return_value = ActionResult(
                    ok=True,
                    code="workspace_started",
                    message="Started workspace",
                )
                exit_code = main(["start"])

            self.assertEqual(exit_code, 0)
            open_dashboard_mock.assert_not_called()
            start_workspace_mock.assert_called_once()

    def test_terminal_runtime_opens_one_process_when_windows_remain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: demo
                root: .
                slots:
                - name: scratch
                  runtime: terminal
                  windows:
                  - name: one
                    command: echo one
                  - name: two
                    command: echo two
                """,
            )

            from cc_branch import load_state, load_workspace, plan_workspace
            from cc_branch.runtime import apply_workspace

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            with patch("cc_branch.runtime.execution.open_command") as open_command:
                apply_workspace(plan, detach=True)

            open_command.assert_called_once()
            self.assertEqual(open_command.call_args.kwargs["command"], "echo one")


if __name__ == "__main__":
    unittest.main()
