import json
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import cc_branch
from cc_branch.cli import build_parser, main, print_command_help, print_help


class CLITests(unittest.TestCase):
    """Tests for the CLI interface and the real non-Web command seam."""

    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def _write_workspace(self, root: Path, *, dashboard: bool = False) -> None:
        self._write(
            root / ".cc-branch/config.yaml",
            f"""
            version: 1
            project: "demo"
            root: "."

            display:
              dashboard: {"true" if dashboard else "false"}

            agents:
              claude:
                command: "claude"
                create_mode: "generated_uuid"
                create_template: "claude --session-id {{{{session_id}}}}"
                resume_mode: "flag"
                resume_template: "resume {{{{session_id}}}}"
                label_template: "{{project}}/{{slot}}/{{window}}"

            slots:
              - name: "dev"
                runtime: "tmux"
                windows:
                  - name: "planner"
                    agent: "claude"
            """,
        )

    def _write_mixed_runtime_workspace(self, root: Path) -> None:
        self._write(
            root / ".cc-branch/config.yaml",
            """
            version: 1
            project: "demo"
            root: "."

            slots:
              - name: "dev"
                runtime: "tmux"
                windows:
                  - name: "planner"
                    command: "echo planner"
                  - name: "coder"
                    command: "echo coder"
              - name: "scratch"
                runtime: "terminal"
                windows:
                  - name: "shell"
                    command: "zsh"
            """,
        )

    def test_main_with_no_args_shows_help(self):
        with patch("cc_branch.cli.console") as mock_console:
            exit_code = main([])
            self.assertEqual(exit_code, 0)
            mock_console.print.assert_called()

    def test_package_exposes_release_version(self):
        self.assertEqual(cc_branch.__version__, "0.1.0")

    def test_main_with_help_flag_shows_help(self):
        with patch("cc_branch.cli.console") as mock_console:
            exit_code = main(["-h"])
            self.assertEqual(exit_code, 0)
            mock_console.print.assert_called()

    def test_command_help_shows_command_specific_help(self):
        with patch("cc_branch.cli.console") as mock_console:
            exit_code = main(["init", "-h"])
            self.assertEqual(exit_code, 0)
            mock_console.print.assert_called()

    def test_parser_exposes_release_ready_command_surface(self):
        parser = build_parser()
        commands = parser._subparsers._group_actions[0].choices

        self.assertEqual(
            list(commands),
            [
                "serve",
                "init",
                "start",
                "open",
                "status",
                "plan",
                "attach",
                "stop",
                "restart",
                "sync",
                "doctor",
                "dashboard",
                "session",
                "help",
            ],
        )
        for removed in ["sessions", "workspace", "target", "config", "ui", "state", "apply"]:
            self.assertNotIn(removed, commands)

    def test_print_help_uses_current_short_alias(self):
        with patch("cc_branch.cli.console") as mock_console:
            print_help()

            rendered_calls = [str(call) for call in mock_console.print.call_args_list]
            self.assertTrue(any("ccb" in call for call in rendered_calls))
            self.assertFalse(any("agb" in call for call in rendered_calls))

    def test_print_command_help_for_init(self):
        with patch("cc_branch.cli.console") as mock_console:
            print_command_help("init")
            mock_console.print.assert_called()

    def test_print_command_help_for_unknown_command(self):
        with patch("cc_branch.cli.console") as mock_console:
            print_command_help("unknown-command")
            mock_console.print.assert_called()

    def test_init_command_creates_config_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("cc_branch.cli.Path.cwd", return_value=root):
                exit_code = main(["init"])
                self.assertEqual(exit_code, 0)
                self.assertTrue((root / ".cc-branch/config.yaml").exists())
                self.assertTrue((root / ".cc-branch/state.yaml").exists())

    def test_init_command_with_force_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text("existing content", encoding="utf-8")

            with patch("cc_branch.cli.Path.cwd", return_value=root):
                exit_code = main(["init", "--force"])
                self.assertEqual(exit_code, 0)
                self.assertNotEqual(config_path.read_text(encoding="utf-8"), "existing content")

    def test_plan_command_requires_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = StringIO()
            with patch("cc_branch.cli.Path.cwd", return_value=root):
                with redirect_stdout(stdout):
                    exit_code = main(["plan"])

            self.assertEqual(exit_code, 1)
            self.assertIn("No workspace config found", stdout.getvalue())
            self.assertIn("cc-branch serve", stdout.getvalue())
            self.assertIn("cc-branch init", stdout.getvalue())

    def test_debug_mode_preserves_traceback_for_unexpected_diagnosis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("cc_branch.cli.Path.cwd", return_value=root):
                with self.assertRaises(FileNotFoundError):
                    main(["--debug", "plan"])

    def test_plan_write_state_persists_generated_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            with patch("cc_branch.cli.Path.cwd", return_value=root):
                exit_code = main(["plan", "--write-state"])

            self.assertEqual(exit_code, 0)
            state = (root / ".cc-branch/state.yaml").read_text(encoding="utf-8")
            self.assertIn('dev.planner', state)
            self.assertIn('session_id:', state)

    def test_status_uses_runtime_status_formatting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.runtime.execution.tmux_has_session", return_value=False),
                patch("cc_branch.runtime.execution.tmux_has_window", return_value=False),
                redirect_stdout(stdout),
            ):
                exit_code = main(["status", "--write-state"])

            self.assertEqual(exit_code, 0)
            rendered = stdout.getvalue()
            self.assertIn("workspace demo @", rendered)
            self.assertIn("status=stopped", rendered)

    def test_attach_routes_through_application_attach_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)
            from cc_branch.application.results import ActionResult

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch(
                    "cc_branch.cli.attach_workspace_action",
                    return_value=ActionResult(ok=True, code="attach_applied", message="Attached dev"),
                ) as attach_workspace,
            ):
                exit_code = main(["attach", "dev"])

            self.assertEqual(exit_code, 0)
            workspace, plan, state, state_path = attach_workspace.call_args.args
            self.assertEqual(workspace.project, "demo")
            self.assertEqual(plan.slots[0].name, "dev")
            self.assertEqual(state.version, 1)
            self.assertEqual(state_path, root / ".cc-branch/state.yaml")
            self.assertEqual(attach_workspace.call_args.kwargs["target"], "dev")

    def test_stop_routes_through_application_stop_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)
            from cc_branch.application.results import ActionResult

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch(
                    "cc_branch.cli.stop_workspace_action",
                    return_value=ActionResult(ok=True, code="stop_applied", message="Stopped dev"),
                ) as stop_workspace_mock,
            ):
                exit_code = main(["stop", "dev"])

            self.assertEqual(exit_code, 0)
            workspace, plan, state, state_path = stop_workspace_mock.call_args.args
            self.assertEqual(workspace.project, "demo")
            self.assertEqual(plan.slots[0].name, "dev")
            self.assertEqual(state.version, 1)
            self.assertEqual(state_path, root / ".cc-branch/state.yaml")
            self.assertEqual(stop_workspace_mock.call_args.kwargs["target"], "dev")

    def test_start_detach_routes_through_application_launch_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)
            from cc_branch.application.results import ActionResult

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch(
                    "cc_branch.cli.launch_workspace_action",
                    return_value=ActionResult(ok=True, code="launch_applied", message="Launched workspace"),
                ) as launch_workspace,
            ):
                exit_code = main(["start", "--detach", "--prepare"])

            self.assertEqual(exit_code, 0)
            workspace, plan, state, state_path = launch_workspace.call_args.args
            self.assertEqual(workspace.project, "demo")
            self.assertEqual(plan.slots[0].name, "dev")
            self.assertEqual(state.version, 1)
            self.assertEqual(state_path, root / ".cc-branch/state.yaml")

    def test_removed_aliases_are_not_registered_as_commands(self):
        parser = build_parser()

        for command in ["up", "apply", "sessions", "workspace", "target", "config", "ui", "state"]:
            with self.subTest(command=command):
                with redirect_stderr(StringIO()):
                    with self.assertRaises(SystemExit):
                        parser.parse_args([command])

    def test_start_detach_does_not_open_terminal_runtime_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_mixed_runtime_workspace(root)

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.runtime.get_backend") as get_backend,
                patch("cc_branch.runtime.execution.open_command") as open_command,
            ):
                backend = get_backend.return_value
                backend.available.return_value = True
                backend.has_session.return_value = False
                backend.create_session.return_value = None
                backend.create_window.return_value = None
                backend.send_keys.return_value = None
                exit_code = main(["start", "--detach"])

            self.assertEqual(exit_code, 0)
            open_command.assert_not_called()

    def test_open_workspace_with_vscode_opens_workspace_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_mixed_runtime_workspace(root)

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.application.workspace_actions.ensure_slot", return_value=[]),
                patch("cc_branch.application.workspace_actions.open_workspace_file") as open_workspace_file,
                patch("cc_branch.application.workspace_actions.open_with") as open_with,
                patch("cc_branch.application.workspace_actions.opener_supports", side_effect=lambda opener, capability, custom=None: capability in {"open_project", "workspace_file"}),
                patch("cc_branch.application.workspace_actions.opener_label", return_value="VS Code"),
            ):
                exit_code = main(["open", "--opener", "vscode"])

            self.assertEqual(exit_code, 0)
            open_with.assert_not_called()
            open_workspace_file.assert_called_once()
            self.assertEqual(open_workspace_file.call_args.args[0], "vscode")
            specs = open_workspace_file.call_args.kwargs["commands"]
            self.assertTrue(any(spec.command.startswith("cc-branch attach") for spec in specs))

    def test_open_project_dir_uses_selected_opener(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.application.workspace_actions.open_with") as open_with,
                patch("cc_branch.application.workspace_actions.opener_label", return_value="Cursor"),
            ):
                exit_code = main(["open", "--project-dir", "--opener", "cursor"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(open_with.call_args.kwargs["opener_id"], "cursor")
            self.assertEqual(open_with.call_args.kwargs["intent"].kind, "project_folder")
            self.assertEqual(open_with.call_args.kwargs["cwd"], root)

    def test_start_does_not_open_dashboard_implicitly_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root, dashboard=True)
            from cc_branch.application.results import ActionResult

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch(
                    "cc_branch.cli.start_workspace_action",
                    return_value=ActionResult(ok=True, code="start_applied", message="Started workspace"),
                ) as start_workspace,
                patch("cc_branch.cli.open_dashboard_workspace_action") as open_dashboard_workspace,
            ):
                exit_code = main(["start"])

            self.assertEqual(exit_code, 0)
            open_dashboard_workspace.assert_not_called()
            start_workspace.assert_called_once()

    def test_start_dashboard_flag_opens_dashboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.application.workspace_actions.ensure_slot", return_value=[]),
                patch("cc_branch.application.workspace_actions.open_dashboard") as open_dashboard_mock,
                patch("cc_branch.cli.start_workspace_action") as start_workspace_mock,
            ):
                exit_code = main(["start", "--dashboard"])

            self.assertEqual(exit_code, 0)
            open_dashboard_mock.assert_called_once()
            start_workspace_mock.assert_not_called()

    def test_start_dashboard_persists_created_tmux_slot_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            from cc_branch.models import AppliedWindowResult

            results = [
                AppliedWindowResult(
                    slot="dev",
                    window="planner",
                    key="dev.planner",
                    runtime="tmux",
                    tmux_session="demo-dev",
                    action="created",
                )
            ]

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.application.workspace_actions.ensure_slot", return_value=results),
                patch("cc_branch.application.workspace_actions.open_dashboard"),
            ):
                exit_code = main(["start", "--dashboard", "--prepare"])

            self.assertEqual(exit_code, 0)
            state = (root / ".cc-branch/state.yaml").read_text(encoding="utf-8")
            self.assertIn("launch_fingerprint", state)
            self.assertIn("slots:", state)
            self.assertIn("dev:", state)

    def test_restart_routes_through_application_restart_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)
            from cc_branch.application.results import ActionResult

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch(
                    "cc_branch.cli.restart_workspace_action",
                    return_value=ActionResult(ok=True, code="restart_applied", message="Restarted dev"),
                ) as restart_workspace_mock,
            ):
                exit_code = main(["restart", "dev", "--detach", "--prepare"])

            self.assertEqual(exit_code, 0)
            workspace, plan, state, state_path = restart_workspace_mock.call_args.args
            self.assertEqual(workspace.project, "demo")
            self.assertEqual(plan.slots[0].name, "dev")
            self.assertEqual(state.version, 1)
            self.assertEqual(state_path, root / ".cc-branch/state.yaml")
            self.assertEqual(restart_workspace_mock.call_args.kwargs["target"], "dev")
            self.assertTrue(restart_workspace_mock.call_args.kwargs["detach"])

    def test_attach_requires_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            stderr = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                redirect_stdout(StringIO()),
                patch("sys.stderr", stderr),
            ):
                with self.assertRaises(SystemExit) as ctx:
                    main(["attach"])

            self.assertEqual(ctx.exception.code, 2)
            self.assertIn("attach requires a <slot>", stderr.getvalue())

    def test_all_commands_have_help_data(self):
        commands = [
            "init",
            "plan",
            "status",
            "start",
            "attach",
            "stop",
            "restart",
            "sync",
            "doctor",
            "dashboard",
            "serve",
        ]

        for command in commands:
            with patch("cc_branch.cli.console"):
                print_command_help(command)

    def test_help_is_generated_from_parser_options(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["init", "--help"])

        self.assertEqual(exit_code, 0)
        rendered = stdout.getvalue()
        self.assertIn("--minimal", rendered)
        self.assertIn("--profile", rendered)

    def test_attach_help_documents_window_targets(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["attach", "--help"])

        self.assertEqual(exit_code, 0)
        rendered = stdout.getvalue()
        self.assertIn("slot[:window]", rendered)
        self.assertIn("dev:planner", rendered)

    def test_serve_help_includes_token_in_rich_help(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["serve", "--help"])

        self.assertEqual(exit_code, 0)
        self.assertIn("--token", stdout.getvalue())

    def test_serve_starts_without_existing_workspace_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.webui.server.start_server") as start_server,
            ):
                exit_code = main(["serve", "--port", "9999"])

            self.assertEqual(exit_code, 0)
            start_server.assert_called_once_with(
                root / ".cc-branch/config.yaml",
                root / ".cc-branch/state.yaml",
                host="127.0.0.1",
                port=9999,
                token=None,
            )

    def test_global_config_and_state_options_override_workspace_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            elsewhere = root / "elsewhere"
            project.mkdir()
            elsewhere.mkdir()
            self._write_workspace(project)
            state_path = project / "custom-state.yaml"
            state_path.write_text("version: 1\n", encoding="utf-8")

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=elsewhere),
                redirect_stdout(stdout),
            ):
                exit_code = main([
                    "--config",
                    str(project / ".cc-branch/config.yaml"),
                    "--state",
                    str(state_path),
                    "plan",
                ])

            self.assertEqual(exit_code, 0)
            self.assertIn("workspace demo plan", stdout.getvalue())

    def test_project_option_changes_workspace_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            elsewhere = root / "elsewhere"
            project.mkdir()
            elsewhere.mkdir()
            self._write_workspace(project)

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=elsewhere),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--project", str(project), "plan"])

            self.assertEqual(exit_code, 0)
            self.assertIn("workspace demo plan", stdout.getvalue())

    def test_plan_format_json_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--format", "json", "plan"])

            self.assertEqual(exit_code, 0)
            data = json.loads(stdout.getvalue())
            self.assertEqual(data["project"], "demo")

    def test_status_format_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.application.workspace_status._default_session_exists", return_value=False),
                patch("cc_branch.application.workspace_status._default_window_exists", return_value=False),
                patch("cc_branch.runtime.sync._tmux_has_session", return_value=False),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--format", "json", "status"])

            self.assertEqual(exit_code, 0)
            data = json.loads(stdout.getvalue())
            self.assertEqual(data["project"], "demo")
            self.assertEqual(data["slots"][0]["status"], "stopped")

    def test_doctor_format_json_returns_structured_report_and_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "planner"
                        agent: "missing-agent"
                """,
            )

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--format", "json", "doctor"])

            self.assertEqual(exit_code, 0)
            data = json.loads(stdout.getvalue())
            self.assertIsInstance(data["report"], dict)
            self.assertIn("issues", data["report"])
            self.assertIn("text", data)
            self.assertTrue(
                any(issue["issue_type"] == "unknown_agent" for issue in data["report"]["issues"])
            )

    def test_session_alias_accepts_colon_target_for_inspect(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.runtime.sessions.tmux_has_session", return_value=False),
                redirect_stdout(stdout),
            ):
                exit_code = main(["session", "inspect", "dev:planner"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Session:", stdout.getvalue())
            self.assertIn("dev.planner", stdout.getvalue())

    def test_session_command_accepts_colon_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                redirect_stdout(stdout),
            ):
                exit_code = main(["session", "command", "dev:planner"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Launch command", stdout.getvalue())

    def test_help_targets_explains_public_target_syntax(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["help", "targets"])

        self.assertEqual(exit_code, 0)
        rendered = stdout.getvalue()
        self.assertIn("dev:planner", rendered)
        self.assertIn("legacy compatibility", rendered)

    def test_sync_dry_run_lists_restart_and_extra_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)
            self._write(
                root / ".cc-branch/state.yaml",
                """
                version: 1
                windows:
                  dev.planner:
                    session_id: "11111111-1111-1111-1111-111111111111"
                    label: "demo/dev/planner"
                    agent: "claude"
                    slot: "dev"
                    window: "planner"
                    launch_fingerprint: "sha256:old"
                """,
            )

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.runtime.sync._tmux_has_session", return_value=True),
                patch("cc_branch.runtime.sync._list_window_names", return_value={"planner", "extra"}),
                redirect_stdout(stdout),
            ):
                exit_code = main(["sync", "--dry-run", "--stop-removed"])

            self.assertEqual(exit_code, 0)
            rendered = stdout.getvalue()
            self.assertIn("restart dev:planner", rendered)
            self.assertIn("stop extra demo-dev:extra", rendered)

    def test_sync_yes_restarts_changed_and_stops_extra(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)
            self._write(
                root / ".cc-branch/state.yaml",
                """
                version: 1
                windows:
                  dev.planner:
                    session_id: "11111111-1111-1111-1111-111111111111"
                    label: "demo/dev/planner"
                    agent: "claude"
                    slot: "dev"
                    window: "planner"
                    launch_fingerprint: "sha256:old"
                """,
            )

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.runtime.sync._tmux_has_session", return_value=True),
                patch("cc_branch.runtime.sync._list_window_names", return_value={"planner", "extra"}),
                patch("cc_branch.application.workspace_actions._restart_runtime_workspace", return_value=[]) as restart_workspace,
                patch("cc_branch.application.workspace_actions.stop_extra_windows", return_value=["demo-dev:extra"]) as stop_extra_windows,
                redirect_stdout(stdout),
            ):
                exit_code = main(["sync", "--yes", "--stop-removed"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(restart_workspace.call_args.args[2], "dev:planner")
            self.assertTrue(restart_workspace.call_args.kwargs["detach"])
            self.assertEqual(stop_extra_windows.call_args.args[1], None)
            self.assertIn("stopped 1 extra window", stdout.getvalue())

    def test_sync_yes_restarts_untracked_running_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)
            self._write(
                root / ".cc-branch/state.yaml",
                """
                version: 1
                windows:
                  dev.planner:
                    session_id: "11111111-1111-1111-1111-111111111111"
                    label: "demo/dev/planner"
                    agent: "claude"
                    slot: "dev"
                    window: "planner"
                """,
            )

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.runtime.sync._tmux_has_session", return_value=True),
                patch("cc_branch.runtime.sync._list_window_names", return_value={"planner"}),
                patch("cc_branch.application.workspace_actions._restart_runtime_workspace", return_value=[]) as restart_workspace,
            ):
                exit_code = main(["sync", "--yes"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(restart_workspace.call_args.args[2], "dev:planner")

    def test_sync_rechecks_state_to_avoid_restarting_newly_created_missing_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "planner"
                        command: "echo planner"
                      - name: "review"
                        command: "echo review"
                """,
            )
            self._write(root / ".cc-branch/state.yaml", "version: 1")

            from cc_branch.models import AppliedWindowResult

            restart_results = [
                AppliedWindowResult(
                    slot="dev",
                    window="planner",
                    key="dev.planner",
                    runtime="tmux",
                    tmux_session="demo-dev",
                    action="recreated",
                ),
                AppliedWindowResult(
                    slot="dev",
                    window="review",
                    key="dev.review",
                    runtime="tmux",
                    tmux_session="demo-dev",
                    action="recreated",
                ),
            ]

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.runtime.sync._tmux_has_session", side_effect=[False, False, True]),
                patch("cc_branch.runtime.sync._list_window_names", return_value={"planner", "review"}),
                patch("cc_branch.application.workspace_actions._restart_runtime_workspace", return_value=restart_results) as restart_workspace,
                patch("cc_branch.application.workspace_actions.stop_extra_windows"),
            ):
                exit_code = main(["sync", "--yes"])

            self.assertEqual(exit_code, 0)
            restart_workspace.assert_called_once()
            state = (root / ".cc-branch/state.yaml").read_text(encoding="utf-8")
            self.assertIn("launch_fingerprint", state)
            self.assertIn('window: review', state)


class CLIHelpFormattingTests(unittest.TestCase):
    """Tests for CLI help formatting and display."""

    def test_help_uses_rich_formatting(self):
        with patch("cc_branch.cli.console") as mock_console:
            print_help()
            self.assertGreater(len(mock_console.print.call_args_list), 0)

    def test_command_help_includes_usage(self):
        with patch("cc_branch.cli.console") as mock_console:
            print_command_help("init")
            calls = [str(call) for call in mock_console.print.call_args_list]
            usage_found = any("Usage" in str(call) or "ccb init" in str(call) for call in calls)
            self.assertTrue(usage_found)

    def test_command_help_includes_options(self):
        with patch("cc_branch.cli.console") as mock_console:
            print_command_help("init")
            self.assertGreater(mock_console.print.call_count, 0)


if __name__ == "__main__":
    unittest.main()
