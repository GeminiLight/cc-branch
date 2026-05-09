"""Tests for configurable workspace openers."""

from __future__ import annotations

import importlib
import unittest
from pathlib import Path
from unittest.mock import patch

from cc_branch.models import OpenerSpec
from cc_branch.openers import (
    OpenCommandSpec,
    OpenerError,
    OpenIntent,
    _intent_command,
    _open_windows_terminal,
    _powershell_single_quote,
    list_openers,
    open_command,
    open_command_layout,
    open_with,
)


class OpenerTests(unittest.TestCase):
    """Tests for local opener detection and dispatch."""

    def test_openers_module_is_package_facade(self):
        """The opener implementation should be split behind the public facade."""
        import cc_branch.openers as openers

        self.assertTrue(hasattr(openers, "__path__"))
        for module_name in [
            "commands",
            "dispatcher",
            "editors",
            "platform",
            "registry",
            "terminal",
            "types",
            "warp",
        ]:
            importlib.import_module(f"cc_branch.openers.{module_name}")

        self.assertIs(openers.OpenIntent, OpenIntent)
        self.assertTrue(callable(openers.open_with))

    def test_openers_expose_explicit_adapter_objects(self):
        """Opener internals should be structured as explicit adapters, not function piles."""
        from cc_branch.openers.dispatcher import OpenerDispatcher
        from cc_branch.openers.editors import EditorWorkspaceOpener
        from cc_branch.openers.registry import OpenerRegistry
        from cc_branch.openers.terminal import TerminalLauncher
        from cc_branch.openers.warp import WarpLauncher

        for adapter in [
            OpenerDispatcher,
            EditorWorkspaceOpener,
            OpenerRegistry,
            TerminalLauncher,
            WarpLauncher,
        ]:
            self.assertTrue(adapter.__doc__)

    def test_list_openers_reports_editor_capabilities(self):
        """Editor openers should be discoverable as project-folder openers."""
        def fake_which(name: str) -> str | None:
            return { "code": "/usr/local/bin/code" }.get(name)

        with patch("cc_branch.openers.registry.shutil.which", side_effect=fake_which):
            payload = list_openers()

        openers = {opener["id"]: opener for opener in payload["openers"]}
        self.assertEqual(payload["default"], "auto-terminal")
        self.assertIn("auto-terminal", openers)
        self.assertIn("open_project", openers["auto-terminal"]["capabilities"])
        self.assertEqual(openers["vscode"]["capabilities"], ["open_project", "workspace_file"])
        self.assertTrue(openers["vscode"]["available"])
        self.assertFalse(openers["cursor"]["available"])
        self.assertIn("cursor CLI not found", openers["cursor"]["reason"])

    def test_macos_terminal_app_detection_checks_system_location(self):
        """Terminal.app lives under /System/Applications/Utilities on modern macOS."""
        def fake_exists(path: Path) -> bool:
            return str(path) == "/System/Applications/Utilities/Terminal.app"

        with (
            patch("cc_branch.openers.registry.sys.platform", "darwin"),
            patch("cc_branch.openers.registry.shutil.which", return_value="/usr/bin/osascript"),
            patch("cc_branch.openers.platform.Path.exists", fake_exists),
        ):
            payload = list_openers()

        openers = {opener["id"]: opener for opener in payload["openers"]}
        self.assertTrue(openers["terminal-app"]["available"])
        self.assertEqual(
            openers["terminal-app"]["executable"],
            "/System/Applications/Utilities/Terminal.app",
        )

    def test_macos_project_openers_do_not_require_osascript(self):
        """Project-folder macOS openers should only require their app bundle."""
        def fake_exists(path: Path) -> bool:
            return str(path) == "/Applications/Warp.app"

        def fake_which(name: str) -> str | None:
            return None

        with (
            patch("cc_branch.openers.registry.sys.platform", "darwin"),
            patch("cc_branch.openers.registry.shutil.which", side_effect=fake_which),
            patch("cc_branch.openers.platform.Path.exists", fake_exists),
        ):
            payload = list_openers()

        openers = {opener["id"]: opener for opener in payload["openers"]}
        self.assertTrue(openers["warp"]["available"])
        self.assertEqual(openers["warp"]["executable"], "/Applications/Warp.app")
        self.assertEqual(openers["warp"]["kind"], "terminal")
        self.assertIn("dashboard", openers["warp"]["capabilities"])
        self.assertIn("layout", openers["warp"]["capabilities"])

    def test_macos_terminal_app_opens_project_with_system_open(self):
        """Terminal.app project opens should use LaunchServices, not execute the .app bundle."""
        def fake_exists(path: Path) -> bool:
            return str(path) == "/System/Applications/Utilities/Terminal.app"

        def fake_which(name: str) -> str | None:
            return {
                "open": "/usr/bin/open",
                "osascript": "/usr/bin/osascript",
            }.get(name)

        with (
            patch("cc_branch.openers.registry.sys.platform", "darwin"),
            patch("cc_branch.openers.platform.Path.exists", fake_exists),
            patch("cc_branch.openers.registry.shutil.which", side_effect=fake_which),
            patch("cc_branch.openers.terminal.shutil.which", side_effect=fake_which),
            patch("cc_branch.openers.terminal._popen") as popen,
        ):
            open_with(
                "terminal-app",
                cwd=Path("/tmp/demo"),
                cli="cc-branch",
                intent=OpenIntent(kind="project_folder"),
            )

        self.assertEqual(popen.call_args.args[0], ["/usr/bin/open", "-a", "Terminal", str(Path("/tmp/demo").resolve())])

    def test_list_openers_includes_configured_openers(self):
        """Workspace config can register additional local terminal apps."""
        custom = {
            "wezterm-custom": OpenerSpec(
                label="WezTerm Custom",
                kind="terminal",
                command="wezterm",
                args=["start", "--cwd", "{cwd}", "--", "sh", "-lc", "{command}"],
            )
        }

        with patch("cc_branch.openers.registry.shutil.which", return_value="/opt/bin/wezterm"):
            payload = list_openers(default="wezterm-custom", custom_openers=custom)

        openers = {opener["id"]: opener for opener in payload["openers"]}
        self.assertEqual(payload["default"], "wezterm-custom")
        self.assertEqual(openers["wezterm-custom"]["source"], "config")
        self.assertEqual(openers["wezterm-custom"]["capabilities"], ["run_command", "dashboard", "attach_target", "open_project"])

    def test_open_command_renders_configured_opener_args(self):
        """Configured openers should receive cwd and command through explicit argv templates."""
        custom = {
            "wezterm-custom": OpenerSpec(
                label="WezTerm Custom",
                kind="terminal",
                command="wezterm",
                args=["start", "--cwd", "{cwd}", "--", "sh", "-lc", "{command}"],
            )
        }

        with (
            patch("cc_branch.openers.registry.shutil.which", return_value="/opt/bin/wezterm"),
            patch("cc_branch.openers.dispatcher.shutil.which", return_value="/opt/bin/wezterm"),
            patch("cc_branch.openers.dispatcher._popen") as popen,
        ):
            open_command(
                "wezterm-custom",
                cwd=Path("/tmp/demo"),
                command="npm run dev",
                custom_openers=custom,
            )

        self.assertEqual(
            popen.call_args.args[0],
            ["/opt/bin/wezterm", "start", "--cwd", str(Path("/tmp/demo").resolve()), "--", "sh", "-lc", "npm run dev"],
        )

    def test_powershell_single_quote_escapes_embedded_quotes(self):
        """PowerShell single-quoted strings escape apostrophes by doubling them."""
        self.assertEqual(_powershell_single_quote(r"C:\Users\O'Neil\demo"), r"'C:\Users\O''Neil\demo'")

    def test_windows_attach_command_uses_powershell_safe_target_quoting(self):
        """Windows attach commands should not use POSIX quote fragments."""
        with patch("cc_branch.openers.commands.os.name", "nt"):
            command = _intent_command(
                "& 'C:\\Program Files\\cc-branch.exe'",
                OpenIntent(kind="attach_target", target="dev O'Neil"),
            )

        self.assertEqual(command, "& 'C:\\Program Files\\cc-branch.exe' attach 'dev O''Neil'")

    def test_windows_terminal_uses_powershell_literal_path_quoting(self):
        """PowerShell launch commands should preserve spaces and apostrophes in cwd."""
        with (
            patch("cc_branch.openers.terminal.shutil.which", return_value="C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"),
            patch("cc_branch.openers.terminal._popen") as popen,
        ):
            _open_windows_terminal("powershell", Path("C:/Users/O'Neil/demo project"), "cc-branch dashboard")

        popen_args = popen.call_args.args[0]
        self.assertIn("Set-Location -LiteralPath '", popen_args[-1])
        self.assertIn("O''Neil", popen_args[-1])
        self.assertIn("demo project", popen_args[-1])

    def test_editor_opener_opens_project_folder(self):
        """VS Code opener should open the project folder without shell command injection."""
        with (
            patch("cc_branch.openers.registry.shutil.which", return_value="/usr/local/bin/code"),
            patch("cc_branch.openers.dispatcher._popen") as popen,
        ):
            open_with(
                "vscode",
                cwd=Path("/tmp/demo"),
                cli="cc-branch",
                intent=OpenIntent(kind="project_folder"),
            )

        self.assertEqual(popen.call_args.args[0], ["/usr/local/bin/code", str(Path("/tmp/demo").resolve())])

    def test_system_file_manager_opens_project_folder(self):
        """The dedicated directory opener should use the OS file manager, not a shell."""
        with (
            patch("cc_branch.openers.registry.sys.platform", "darwin"),
            patch("cc_branch.openers.registry.shutil.which", return_value="/usr/bin/open"),
            patch("cc_branch.openers.dispatcher._open_path") as open_path,
        ):
            open_with(
                "system-file-manager",
                cwd=Path("/tmp/demo"),
                cli="cc-branch",
                intent=OpenIntent(kind="project_folder"),
            )

        self.assertEqual(open_path.call_args.args[0], Path("/tmp/demo").resolve())

    def test_editor_opener_rejects_attach_intent(self):
        """Editors must not be treated as attach-capable terminals."""
        with patch("cc_branch.openers.registry.shutil.which", return_value="/usr/local/bin/code"):
            with self.assertRaisesRegex(OpenerError, "does not support attach_target"):
                open_with(
                    "vscode",
                    cwd=Path("/tmp/demo"),
                    cli="cc-branch",
                    intent=OpenIntent(kind="attach_target", target="dev"),
                )

    def test_editor_workspace_file_opens_tasks_workspace(self):
        """VS Code/Cursor workspace opens should expose cc-branch windows as tasks."""
        import tempfile

        from cc_branch.openers import open_workspace_file

        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            with (
                patch("cc_branch.openers.registry.shutil.which", return_value="/usr/local/bin/code"),
                patch("cc_branch.openers.editors._cache_dir", return_value=cache_dir),
                patch("cc_branch.openers.editors._popen") as popen,
            ):
                open_workspace_file(
                    "vscode",
                    cwd=Path("/tmp/demo"),
                    commands=[
                        OpenCommandSpec("dev:planner", Path("/tmp/demo"), "cc-branch attach dev:planner"),
                        OpenCommandSpec("scratch:main", Path("/tmp/demo"), "zsh"),
                    ],
                )

            workspace_file = next((cache_dir / "editor-workspaces").glob("*.code-workspace"))
            content = workspace_file.read_text(encoding="utf-8")
            self.assertIn('"folders"', content)
            self.assertIn('"runOn": "folderOpen"', content)
            self.assertIn("cc-branch attach dev:planner", content)
            self.assertIn("zsh", content)
            self.assertEqual(popen.call_args.args[0], ["/usr/local/bin/code", "-n", str(workspace_file)])

    def test_editor_workspace_file_removes_stale_workspace_for_same_project(self):
        """Old generated workspace files should not keep obsolete auto-run tasks around."""
        import json
        import tempfile

        from cc_branch.openers import open_workspace_file

        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            workspace_dir = cache_dir / "editor-workspaces"
            workspace_dir.mkdir()
            stale = workspace_dir / "demo-vscode-old.code-workspace"
            stale.write_text(
                json.dumps({
                    "folders": [{"path": "/tmp/demo"}],
                    "tasks": {"version": "2.0.0", "tasks": [{"label": "cc-branch: dev:old"}]},
                }),
                encoding="utf-8",
            )
            unrelated = workspace_dir / "demo-vscode-other.code-workspace"
            unrelated.write_text(
                json.dumps({
                    "folders": [{"path": "/tmp/other/demo"}],
                    "tasks": {"version": "2.0.0", "tasks": [{"label": "cc-branch: keep"}]},
                }),
                encoding="utf-8",
            )
            malformed = workspace_dir / "demo-vscode-malformed.code-workspace"
            malformed.write_text(
                json.dumps({
                    "folders": [{"path": ""}],
                    "tasks": {"version": "2.0.0", "tasks": [{"label": "cc-branch: keep"}]},
                }),
                encoding="utf-8",
            )

            with (
                patch("cc_branch.openers.registry.shutil.which", return_value="/usr/local/bin/code"),
                patch("cc_branch.openers.editors._cache_dir", return_value=cache_dir),
                patch("cc_branch.openers.editors._popen"),
            ):
                open_workspace_file(
                    "vscode",
                    cwd=Path("/tmp/demo"),
                    commands=[
                        OpenCommandSpec("dev", Path("/tmp/demo"), "cc-branch attach dev"),
                    ],
                )

            workspace_files = sorted(workspace_dir.glob("demo-vscode-*.code-workspace"))
            self.assertFalse(stale.exists())
            self.assertTrue(unrelated.exists())
            self.assertTrue(malformed.exists())
            self.assertEqual(len(workspace_files), 3)

    def test_cursor_workspace_file_opens_new_window(self):
        """Cursor should receive the generated workspace file, not just the project folder."""
        import tempfile

        from cc_branch.openers import open_workspace_file

        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            with (
                patch("cc_branch.openers.registry.shutil.which", return_value="/usr/local/bin/cursor"),
                patch("cc_branch.openers.editors._cache_dir", return_value=cache_dir),
                patch("cc_branch.openers.editors._popen") as popen,
            ):
                open_workspace_file(
                    "cursor",
                    cwd=Path("/tmp/demo"),
                    commands=[
                        OpenCommandSpec("dev:planner", Path("/tmp/demo"), "/repo/bin/cc-branch attach dev:planner"),
                    ],
                )

            workspace_file = next((cache_dir / "editor-workspaces").glob("*.code-workspace"))
            content = workspace_file.read_text(encoding="utf-8")
            self.assertIn('"label": "cc-branch: dev:planner"', content)
            self.assertIn("/repo/bin/cc-branch attach dev:planner", content)
            self.assertEqual(popen.call_args.args[0], ["/usr/local/bin/cursor", "-n", str(workspace_file)])

    def test_warp_workspace_dashboard_uses_launch_configuration_uri(self):
        """Warp should run workspace commands through a launch configuration."""
        with (
            patch("cc_branch.openers.dispatcher._opener_info") as opener_info,
            patch("cc_branch.openers.warp._warp_launch_config_dir", return_value=Path("/tmp/cc-branch-test-cache")),
            patch("cc_branch.openers.warp.WarpLauncher.open_uri") as open_uri,
        ):
            opener_info.return_value = type(
                "Info",
                (),
                {
                    "id": "warp",
                    "available": True,
                    "reason": None,
                    "capabilities": ["run_command", "dashboard", "attach_target", "open_project", "layout"],
                },
            )()
            open_with(
                "warp",
                cwd=Path("/tmp/demo"),
                cli="cc-branch",
                intent=OpenIntent(kind="workspace_dashboard"),
            )

        uri = open_uri.call_args.args[0]
        self.assertTrue(uri.startswith("warp://launch/"))
        self.assertIn("cc-branch-test-cache", uri)
        self.assertNotIn("%2Ftmp", uri)

    def test_warp_launch_uri_uses_app_bundle_on_macos(self):
        """macOS should open Warp launch URIs with the detected app bundle."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            app_path = Path(tmp) / "Warp.app"
            app_path.mkdir()
            cache_dir = Path(tmp) / "launch_configurations"
            with (
                patch("cc_branch.openers.dispatcher._opener_info") as opener_info,
                patch("cc_branch.openers.warp.sys.platform", "darwin"),
                patch("cc_branch.openers.warp._find_macos_app", return_value=app_path),
                patch("cc_branch.openers.warp._warp_launch_config_dir", return_value=cache_dir),
                patch("cc_branch.openers.warp._popen") as popen,
            ):
                opener_info.return_value = type(
                    "Info",
                    (),
                    {
                        "id": "warp",
                        "available": True,
                        "reason": None,
                        "capabilities": ["run_command", "layout"],
                    },
                )()
                open_command_layout(
                    "warp",
                    [OpenCommandSpec("dev", Path("/tmp/demo"), "npm run dev")],
                )

            args = popen.call_args.args[0]
            self.assertEqual(args[0:3], ["open", "-a", str(app_path)])
            self.assertTrue(args[3].startswith("warp://launch/"))

    def test_warp_layout_writes_multiple_commands_into_one_launch_config(self):
        """Pure terminal workspaces should be one Warp layout, not many windows."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            with (
                patch("cc_branch.openers.warp._warp_launch_config_dir", return_value=cache_dir),
                patch("cc_branch.openers.dispatcher._opener_info") as opener_info,
                patch("cc_branch.openers.warp.WarpLauncher.open_uri") as open_uri,
            ):
                opener_info.return_value = type(
                    "Info",
                    (),
                    {
                        "available": True,
                        "reason": None,
                        "capabilities": ["run_command", "layout"],
                    },
                )()
                open_command_layout(
                    "warp",
                    [
                        OpenCommandSpec("dev", Path("/tmp/demo"), "npm run dev"),
                        OpenCommandSpec("worker", Path("/tmp/demo"), "python worker.py"),
                        OpenCommandSpec("logs", Path("/tmp/demo"), "tail -f app.log"),
                    ],
                )

            uri = open_uri.call_args.args[0]
            self.assertTrue(uri.startswith("warp://launch/"))
            config_path = next(cache_dir.glob("*.yaml"))
            content = config_path.read_text(encoding="utf-8")
            self.assertIn("panes:", content)
            self.assertEqual(content.count("split_direction:"), 2)
            self.assertIn('exec: "npm run dev"', content)
            self.assertIn('exec: "python worker.py"', content)
            self.assertIn('exec: "tail -f app.log"', content)

    def test_unknown_opener_is_rejected(self):
        """API callers should only reference registered openers."""
        with self.assertRaisesRegex(OpenerError, "Unknown opener"):
            open_with(
                "not-real",
                cwd=Path("/tmp/demo"),
                cli="cc-branch",
                intent=OpenIntent(kind="project_folder"),
            )


if __name__ == "__main__":
    unittest.main()
