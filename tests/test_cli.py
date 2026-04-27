import json
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from cc_branch.cli import build_parser, main, print_command_help, print_help


class CLITests(unittest.TestCase):
    """Tests for the CLI interface and the real non-Web command seam."""

    def _write(self, path: Path, content: str) -> None:
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def _write_workspace(self, root: Path, *, dashboard: bool = False) -> None:
        self._write(
            root / ".cc-branch.yaml",
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
                backend: "tmux"
                windows:
                  - name: "planner"
                    agent: "claude"
            """,
        )

    def test_main_with_no_args_shows_help(self):
        with patch("cc_branch.cli.console") as mock_console:
            exit_code = main([])
            self.assertEqual(exit_code, 0)
            mock_console.print.assert_called()

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

    def test_print_help_displays_all_commands(self):
        with patch("cc_branch.cli.console") as mock_console:
            print_help()
            self.assertGreater(mock_console.print.call_count, 0)

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
                self.assertTrue((root / ".cc-branch.yaml").exists())
                self.assertTrue((root / ".cc-branch.state.toml").exists())

    def test_init_command_with_force_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch.yaml"
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
            self.assertIn("cc-branch init", stdout.getvalue())

    def test_debug_mode_preserves_traceback_for_unexpected_diagnosis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("cc_branch.cli.Path.cwd", return_value=root):
                with self.assertRaises(FileNotFoundError):
                    main(["--debug", "plan"])

    def test_plan_bootstrap_if_missing_persists_generated_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            with patch("cc_branch.cli.Path.cwd", return_value=root):
                exit_code = main(["plan", "--bootstrap-if-missing"])

            self.assertEqual(exit_code, 0)
            state = (root / ".cc-branch.state.toml").read_text(encoding="utf-8")
            self.assertIn('dev.planner', state)
            self.assertIn('session_id = "', state)

    def test_status_uses_runtime_status_formatting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.runtime.tmux_has_session", return_value=False),
                patch("cc_branch.runtime.tmux_has_window", return_value=False),
                redirect_stdout(stdout),
            ):
                exit_code = main(["status", "--bootstrap-if-missing"])

            self.assertEqual(exit_code, 0)
            rendered = stdout.getvalue()
            self.assertIn("workspace demo @", rendered)
            self.assertIn("status=stopped", rendered)

    def test_attach_routes_through_runtime_attach_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.cli.attach_slot") as attach_slot_mock,
            ):
                exit_code = main(["attach", "dev"])

            self.assertEqual(exit_code, 0)
            plan = attach_slot_mock.call_args.args[0]
            self.assertEqual(plan.slots[0].name, "dev")
            self.assertEqual(attach_slot_mock.call_args.args[1], "dev")

    def test_stop_routes_through_runtime_stop_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.cli.stop_workspace") as stop_workspace_mock,
            ):
                exit_code = main(["stop", "dev"])

            self.assertEqual(exit_code, 0)
            workspace, plan, target = stop_workspace_mock.call_args.args
            self.assertEqual(workspace.project, "demo")
            self.assertEqual(plan.slots[0].name, "dev")
            self.assertEqual(target, "dev")

    def test_start_routes_through_runtime_apply_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.cli.apply_workspace") as apply_workspace_mock,
            ):
                exit_code = main(["start", "--detach", "--bootstrap-if-missing"])

            self.assertEqual(exit_code, 0)
            plan = apply_workspace_mock.call_args.args[0]
            self.assertEqual(plan.slots[0].name, "dev")
            self.assertTrue(apply_workspace_mock.call_args.kwargs["detach"])

    def test_up_is_not_registered_as_a_command(self):
        parser = build_parser()

        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["up"])

    def test_start_does_not_open_dashboard_implicitly_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root, dashboard=True)

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.cli.open_dashboard") as open_dashboard_mock,
                patch("cc_branch.cli.apply_workspace") as apply_workspace_mock,
            ):
                exit_code = main(["start"])

            self.assertEqual(exit_code, 0)
            open_dashboard_mock.assert_not_called()
            apply_workspace_mock.assert_called_once()

    def test_start_dashboard_flag_opens_dashboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.cli.open_dashboard") as open_dashboard_mock,
                patch("cc_branch.cli.apply_workspace") as apply_workspace_mock,
            ):
                exit_code = main(["start", "--dashboard"])

            self.assertEqual(exit_code, 0)
            open_dashboard_mock.assert_called_once()
            apply_workspace_mock.assert_not_called()

    def test_restart_routes_through_runtime_restart_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.cli.restart_workspace") as restart_workspace_mock,
            ):
                exit_code = main(["restart", "dev", "--detach", "--bootstrap-if-missing"])

            self.assertEqual(exit_code, 0)
            workspace, plan, target = restart_workspace_mock.call_args.args[:3]
            self.assertEqual(workspace.project, "demo")
            self.assertEqual(plan.slots[0].name, "dev")
            self.assertEqual(target, "dev")
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
        self.assertIn("bootstrapped automatically", rendered)

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
                root / ".cc-branch.yaml",
                root / ".cc-branch.state.toml",
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
            state_path = project / "custom-state.toml"
            state_path.write_text("version = 1\n", encoding="utf-8")

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=elsewhere),
                redirect_stdout(stdout),
            ):
                exit_code = main([
                    "--config",
                    str(project / ".cc-branch.yaml"),
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
                patch("cc_branch.runtime.tmux_has_session", return_value=False),
                patch("cc_branch.runtime.tmux_has_window", return_value=False),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--format", "json", "status"])

            self.assertEqual(exit_code, 0)
            data = json.loads(stdout.getvalue())
            self.assertEqual(data["project"], "demo")
            self.assertEqual(data["slots"][0]["status"], "stopped")

    def test_session_alias_accepts_colon_target_for_inspect(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.sessions.tmux_has_session", return_value=False),
                redirect_stdout(stdout),
            ):
                exit_code = main(["session", "inspect", "dev:planner"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Session:", stdout.getvalue())
            self.assertIn("dev.planner", stdout.getvalue())

    def test_sessions_compat_accepts_colon_target_for_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                redirect_stdout(stdout),
            ):
                exit_code = main(["sessions", "command", "dev:planner"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Launch command", stdout.getvalue())

    def test_grouped_workspace_plan_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            stdout = StringIO()
            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                redirect_stdout(stdout),
            ):
                exit_code = main(["workspace", "plan"])

            self.assertEqual(exit_code, 0)
            self.assertIn("workspace demo plan", stdout.getvalue())

    def test_grouped_workspace_start_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.cli.apply_workspace") as apply_workspace_mock,
            ):
                exit_code = main(["workspace", "start", "--detach"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(apply_workspace_mock.call_args.args[0].slots[0].name, "dev")
            self.assertTrue(apply_workspace_mock.call_args.kwargs["detach"])

    def test_grouped_target_attach_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            with (
                patch("cc_branch.cli.Path.cwd", return_value=root),
                patch("cc_branch.cli.attach_slot") as attach_slot_mock,
            ):
                exit_code = main(["target", "attach", "dev:planner"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(attach_slot_mock.call_args.args[1], "dev:planner")

    def test_state_bootstrap_writes_missing_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            with patch("cc_branch.cli.Path.cwd", return_value=root):
                exit_code = main(["state", "bootstrap"])

            self.assertEqual(exit_code, 0)
            state = (root / ".cc-branch.state.toml").read_text(encoding="utf-8")
            self.assertIn("dev.planner", state)

    def test_state_bootstrap_dry_run_does_not_write_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_workspace(root)

            with patch("cc_branch.cli.Path.cwd", return_value=root):
                exit_code = main(["state", "bootstrap", "--dry-run"])

            self.assertEqual(exit_code, 0)
            self.assertFalse((root / ".cc-branch.state.toml").exists())

    def test_help_targets_explains_public_target_syntax(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["help", "targets"])

        self.assertEqual(exit_code, 0)
        rendered = stdout.getvalue()
        self.assertIn("dev:planner", rendered)
        self.assertIn("legacy compatibility", rendered)


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
