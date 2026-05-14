"""Tests for configurable workspace openers."""

from __future__ import annotations

import importlib
import json
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

    def test_iterm2_is_not_advertised_for_command_start(self):
        """iTerm2 project opens are supported, but command start is not reliable enough to expose."""
        def fake_exists(path: Path) -> bool:
            return str(path) == "/Applications/iTerm.app"

        def fake_which(name: str) -> str | None:
            return "/usr/bin/osascript" if name == "osascript" else None

        with (
            patch("cc_branch.openers.registry.sys.platform", "darwin"),
            patch("cc_branch.openers.registry.shutil.which", side_effect=fake_which),
            patch("cc_branch.openers.platform.Path.exists", fake_exists),
        ):
            payload = list_openers()

        openers = {opener["id"]: opener for opener in payload["openers"]}
        self.assertEqual(openers["iterm2"]["capabilities"], ["open_project"])
        self.assertNotIn("run_command", openers["iterm2"]["capabilities"])

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

    def test_linux_warp_detection_uses_warp_terminal_binary(self):
        """Linux builds should expose Warp when the warp-terminal binary is installed."""
        def fake_which(name: str) -> str | None:
            return "/usr/bin/warp-terminal" if name == "warp-terminal" else None

        with (
            patch("cc_branch.openers.registry.sys.platform", "linux"),
            patch("cc_branch.openers.registry.shutil.which", side_effect=fake_which),
        ):
            payload = list_openers()

        openers = {opener["id"]: opener for opener in payload["openers"]}
        self.assertTrue(openers["warp"]["available"])
        self.assertEqual(openers["warp"]["executable"], "/usr/bin/warp-terminal")
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

    def test_iterm2_waits_for_new_window_before_writing_command(self):
        """iTerm2 needs a short delay before sending text to a new session."""
        from cc_branch.openers.terminal import _open_iterm2

        with (
            patch("cc_branch.openers.terminal.shutil.which", return_value="/usr/bin/osascript"),
            patch("cc_branch.openers.terminal.subprocess.run") as run,
        ):
            run.return_value.returncode = 0
            run.return_value.stderr = ""
            run.return_value.stdout = ""
            _open_iterm2(Path("/tmp/demo"), "npm run dev")

        args = run.call_args.args[0]
        script = "\n".join(args[index + 1] for index, arg in enumerate(args) if arg == "-e")
        self.assertEqual(args[0], "osascript")
        self.assertIn('tell application "iTerm2"', script)
        self.assertIn("create window with default profile", script)
        self.assertIn("repeat 20 times", script)
        self.assertIn("delay 0.5", script)
        self.assertIn("current session of current window", script)
        self.assertIn("write text", script)
        self.assertEqual(run.call_args.kwargs["timeout"], 30)

    def test_osascript_timeout_is_reported_as_opener_error(self):
        """AppleScript timeouts should surface as user-facing opener errors."""
        import subprocess

        from cc_branch.openers.terminal import _run_osascript

        with patch("cc_branch.openers.terminal.subprocess.run", side_effect=subprocess.TimeoutExpired(["osascript"], 10)):
            with self.assertRaisesRegex(OpenerError, "AppleScript timed out"):
                _run_osascript("tell application \"Terminal\" to activate", "Cannot open Terminal")

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

    def test_vscode_workspace_open_creates_project_tasks_bridge(self):
        """VS Code should open the real folder and expose cc-branch tasks without GUI automation."""
        import tempfile

        from cc_branch.openers import open_workspace_file

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subdir = root / "subdir"
            subdir.mkdir()
            with (
                patch("cc_branch.openers.registry.shutil.which", return_value="/usr/local/bin/code"),
                patch("cc_branch.openers.editors._popen") as popen,
            ):
                open_workspace_file(
                    "vscode",
                    cwd=root,
                    commands=[
                        OpenCommandSpec("dev:planner", root, "cc-branch attach dev:planner"),
                        OpenCommandSpec("scratch:main", subdir, "zsh"),
                    ],
                )

            self.assertEqual(popen.call_args.args[0], ["/usr/local/bin/code", "-n", str(root.resolve())])
            sidecar = root / ".cc-branch" / ".generated" / "vscode-tasks.json"
            bridge = root / ".vscode" / "tasks.json"
            self.assertTrue(sidecar.exists())
            self.assertTrue(bridge.exists())
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual(payload["version"], "2.0.0")
            self.assertEqual([task["label"] for task in payload["tasks"]], [
                "cc-branch: dev:planner",
                "cc-branch: scratch:main",
            ])
            self.assertEqual(payload["tasks"][0]["presentation"]["group"], "cc-branch:dev")
            self.assertEqual(payload["tasks"][1]["presentation"]["group"], "cc-branch:scratch")
            self.assertEqual(payload["tasks"][0]["runOptions"], {"runOn": "folderOpen"})
            self.assertEqual(payload["tasks"][1]["options"]["cwd"], str(subdir.resolve()))
            if bridge.is_symlink():
                self.assertEqual(bridge.resolve(), sidecar.resolve())
            else:
                self.assertEqual(json.loads(bridge.read_text(encoding="utf-8")), payload)

    def test_vscode_task_split_groups_only_panes_inside_the_same_tab(self):
        """VS Code split groups should not merge panes from different CC Branch tabs."""
        from cc_branch.openers.editors import editor_workspace_opener

        payload = editor_workspace_opener.tasks_payload(
            [
                OpenCommandSpec("dev:frontend", Path("/tmp/demo"), "npm run dev"),
                OpenCommandSpec("dev:backend", Path("/tmp/demo"), "python api.py"),
                OpenCommandSpec("docs:writer", Path("/tmp/demo"), "codex"),
            ]
        )

        groups = [task["presentation"]["group"] for task in payload["tasks"]]
        self.assertEqual(groups, ["cc-branch:dev", "cc-branch:dev", "cc-branch:docs"])

    def test_vscode_task_split_uses_explicit_group_over_title_shape(self):
        """Split grouping is carried by command metadata, not inferred from labels."""
        from cc_branch.openers.editors import editor_workspace_opener

        payload = editor_workspace_opener.tasks_payload(
            [
                OpenCommandSpec("Frontend", Path("/tmp/demo"), "npm run dev", split_group="dev"),
                OpenCommandSpec("Backend", Path("/tmp/demo"), "python api.py", split_group="dev"),
                OpenCommandSpec("Writer", Path("/tmp/demo"), "codex", split_group="docs"),
            ]
        )

        groups = [task["presentation"]["group"] for task in payload["tasks"]]
        self.assertEqual(groups, ["cc-branch:dev", "cc-branch:dev", "cc-branch:docs"])

    def test_vscode_workspace_open_does_not_create_generated_workspace_file_on_macos(self):
        """The Explorer should show the real folder, not a generated .code-workspace wrapper."""
        import tempfile

        from cc_branch.openers import open_workspace_file

        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            workspace_dir = cache_dir / "editor-workspaces"
            workspace_dir.mkdir()
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

            self.assertEqual(list(workspace_dir.glob("*.code-workspace")), [])

    def test_vscode_workspace_open_merges_existing_user_tasks(self):
        """Existing user-owned .vscode/tasks.json should keep user tasks and run cc-branch tasks."""
        import tempfile

        from cc_branch.openers import open_workspace_file

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_tasks = root / ".vscode" / "tasks.json"
            user_tasks.parent.mkdir()
            user_content = '{"version":"2.0.0","tasks":[{"label":"user task","type":"shell","command":"echo user"}]}\n'
            user_tasks.write_text(user_content, encoding="utf-8")
            with (
                patch("cc_branch.openers.registry.shutil.which", return_value="/usr/local/bin/code"),
                patch("cc_branch.openers.editors._popen") as popen,
            ):
                open_workspace_file(
                    "vscode",
                    cwd=root,
                    commands=[
                        OpenCommandSpec("dev", root, "cc-branch attach dev"),
                    ],
                )

            self.assertEqual(popen.call_args.args[0], ["/usr/local/bin/code", "-n", str(root.resolve())])
            payload = json.loads(user_tasks.read_text(encoding="utf-8"))
            self.assertEqual([task["label"] for task in payload["tasks"]], ["user task", "cc-branch: dev"])
            self.assertEqual(payload["tasks"][0]["command"], "echo user")
            self.assertEqual(payload["tasks"][1]["command"], "cc-branch attach dev")
            self.assertTrue((root / ".cc-branch" / ".generated" / "vscode-tasks.json").exists())

    def test_vscode_workspace_open_replaces_previous_generated_tasks_in_user_tasks(self):
        """Regenerating project tasks should not duplicate old cc-branch task entries."""
        import tempfile

        from cc_branch.openers import open_workspace_file

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_tasks = root / ".vscode" / "tasks.json"
            user_tasks.parent.mkdir()
            user_tasks.write_text(
                json.dumps(
                    {
                        "version": "2.0.0",
                        "tasks": [
                            {"label": "user task", "type": "shell", "command": "echo user"},
                            {"label": "cc-branch: old", "type": "shell", "command": "old"},
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with (
                patch("cc_branch.openers.registry.shutil.which", return_value="/usr/local/bin/code"),
                patch("cc_branch.openers.editors._popen"),
            ):
                open_workspace_file(
                    "vscode",
                    cwd=root,
                    commands=[
                        OpenCommandSpec("dev:ui", root, "npm run dev"),
                        OpenCommandSpec("dev:api", root, "python api.py"),
                    ],
                )

            payload = json.loads(user_tasks.read_text(encoding="utf-8"))
            self.assertEqual([task["label"] for task in payload["tasks"]], [
                "user task",
                "cc-branch: dev:ui",
                "cc-branch: dev:api",
            ])

    def test_vscode_workspace_open_leaves_unparseable_user_tasks_untouched(self):
        """JSONC or broken user tasks are left untouched instead of being rewritten."""
        import tempfile

        from cc_branch.openers import open_workspace_file

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_tasks = root / ".vscode" / "tasks.json"
            user_tasks.parent.mkdir()
            user_content = '{\n  // user comment\n  "version": "2.0.0",\n  "tasks": []\n}\n'
            user_tasks.write_text(user_content, encoding="utf-8")
            with (
                patch("cc_branch.openers.registry.shutil.which", return_value="/usr/local/bin/code"),
                patch("cc_branch.openers.editors._popen"),
            ):
                open_workspace_file(
                    "vscode",
                    cwd=root,
                    commands=[
                        OpenCommandSpec("dev", root, "cc-branch attach dev"),
                    ],
                )

            self.assertEqual(user_tasks.read_text(encoding="utf-8"), user_content)
            self.assertTrue((root / ".cc-branch" / ".generated" / "vscode-tasks.json").exists())

    def test_cursor_workspace_open_creates_project_tasks_bridge(self):
        """Cursor should use the same project tasks bridge as VS Code."""
        import tempfile

        from cc_branch.openers import open_workspace_file

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch("cc_branch.openers.registry.shutil.which", return_value="/usr/local/bin/cursor"),
                patch("cc_branch.openers.editors._popen") as popen,
            ):
                open_workspace_file(
                    "cursor",
                    cwd=root,
                    commands=[
                        OpenCommandSpec("dev:planner", root, "/repo/bin/cc-branch attach dev:planner"),
                    ],
                )

            self.assertEqual(popen.call_args.args[0], ["/usr/local/bin/cursor", "-n", str(root.resolve())])
            sidecar = root / ".cc-branch" / ".generated" / "vscode-tasks.json"
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual(payload["tasks"][0]["command"], "/repo/bin/cc-branch attach dev:planner")

    def test_warp_workspace_dashboard_uses_launch_configuration_uri(self):
        """Warp should run workspace commands through a launch configuration."""
        import tempfile

        with (
            patch("cc_branch.openers.dispatcher._opener_info") as opener_info,
            patch("cc_branch.openers.warp._warp_launch_config_dir") as launch_dir,
            patch("cc_branch.openers.warp.WarpLauncher.open_uri") as open_uri,
        ):
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            launch_dir.return_value = Path(tmp.name) / "launch_configurations"
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

        args = open_uri.call_args.args[0]
        self.assertTrue(args.startswith("warp://launch/"))
        self.assertEqual(args, "warp://launch/CC%20Branch%20Dashboard")
        self.assertNotIn("%C2%B7", args)

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
            self.assertEqual(uri, "warp://launch/CC%20Branch%20demo")
            self.assertNotIn("%C2%B7", uri)
            config_path = next(cache_dir.glob("*.yaml"))
            content = config_path.read_text(encoding="utf-8")
            self.assertEqual(config_path.name, "cc-branch-demo.yaml")
            self.assertIn('name: "CC Branch demo"', content)
            self.assertIn("panes:", content)
            self.assertEqual(content.count("split_direction:"), 2)
            self.assertIn('exec: "npm run dev"', content)
            self.assertIn('exec: "python worker.py"', content)
            self.assertIn('exec: "tail -f app.log"', content)

    def test_warp_layout_balances_four_commands_as_two_by_two_grid(self):
        """Four commands should render as two balanced groups, not a shrinking tail."""
        from cc_branch.openers.warp import _warp_layout_yaml

        specs = [
            OpenCommandSpec("one", Path("/tmp/demo"), "one"),
            OpenCommandSpec("two", Path("/tmp/demo"), "two"),
            OpenCommandSpec("three", Path("/tmp/demo"), "three"),
            OpenCommandSpec("four", Path("/tmp/demo"), "four"),
        ]

        content = _warp_layout_yaml("CC Branch demo", specs)

        self.assertEqual(content.count("split_direction:"), 3)
        self.assertIn(
            """          panes:
            - split_direction: horizontal
              panes:
                - cwd: "/tmp/demo"
                  commands:
                    - exec: "one"
                  is_focused: true
                - cwd: "/tmp/demo"
                  commands:
                    - exec: "two"
            - split_direction: horizontal
              panes:
                - cwd: "/tmp/demo"
                  commands:
                    - exec: "three"
                - cwd: "/tmp/demo"
                  commands:
                    - exec: "four\"""",
            content,
        )

    def test_warp_layout_uses_stable_project_name_and_removes_legacy_hash_configs(self):
        """Repeated Warp opens should reuse a stable launch config instead of visible cache hashes."""
        import tempfile

        from cc_branch.openers.dispatcher import open_command_layout

        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            (cache_dir / "cc-branch-demo-123456789abc.yaml").write_text("old", encoding="utf-8")
            (cache_dir / "cc-branch-demo.yaml-123456789abc.yaml").write_text("old", encoding="utf-8")
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
                        OpenCommandSpec("dev", Path("/tmp/demo"), "cc-branch attach dev"),
                        OpenCommandSpec("scratch", Path("/tmp/demo"), "npm run dev"),
                    ],
                )

            self.assertFalse((cache_dir / "cc-branch-demo-123456789abc.yaml").exists())
            config_path = cache_dir / "cc-branch-demo.yaml"
            self.assertTrue(config_path.exists())
            content = config_path.read_text(encoding="utf-8")
            self.assertIn('name: "CC Branch demo"', content)
            self.assertIn("panes:", content)
            self.assertEqual(open_uri.call_args.args[0], "warp://launch/CC%20Branch%20demo")

    def test_warp_launch_uri_uses_config_name(self):
        """Warp launches execute by configuration name on the local Warp build."""
        import tempfile

        from cc_branch.openers.dispatcher import open_command_layout

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
                    [OpenCommandSpec("dev", Path("/tmp/demo"), "zsh")],
                )

            uri = open_uri.call_args.args[0]
            self.assertEqual(uri, "warp://launch/CC%20Branch%20demo")
            self.assertNotIn("%2F", uri)

    def test_warp_project_open_uses_launch_config_with_cwd(self):
        """Warp project opens should create a real shell in the project directory."""
        with (
            patch("cc_branch.openers.registry.shutil.which", return_value="/usr/bin/open"),
            patch("cc_branch.openers.dispatcher._opener_info") as opener_info,
            patch("cc_branch.openers.warp._warp_launch_config_dir") as launch_dir,
            patch("cc_branch.openers.warp.WarpLauncher.open_uri") as open_uri,
        ):
            import tempfile

            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            launch_dir.return_value = Path(tmp.name)
            opener_info.return_value = type(
                "Info",
                (),
                {
                    "available": True,
                    "reason": None,
                    "capabilities": ["open_project", "run_command", "layout"],
                },
            )()
            open_with(
                "warp",
                cwd=Path("/tmp/demo project"),
                cli="cc-branch",
                intent=OpenIntent(kind="project_folder"),
            )

        uri = open_uri.call_args.args[0]
        self.assertEqual(uri, "warp://launch/CC%20Branch%20Project%20demo%20project")
        config_path = Path(tmp.name) / "cc-branch-project-demo-project.yaml"
        content = config_path.read_text(encoding="utf-8")
        self.assertIn("demo project", content)
        self.assertIn('exec: ":"', content)

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
