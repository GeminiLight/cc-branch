"""Tests for configurable workspace openers."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from cc_branch.openers import (
    OpenerError,
    OpenIntent,
    _intent_command,
    _open_windows_terminal,
    _powershell_single_quote,
    list_openers,
    open_with,
)


class OpenerTests(unittest.TestCase):
    """Tests for local opener detection and dispatch."""

    def test_list_openers_reports_editor_capabilities(self):
        """Editor openers should be discoverable as project-folder openers."""
        def fake_which(name: str) -> str | None:
            return { "code": "/usr/local/bin/code" }.get(name)

        with patch("cc_branch.openers.shutil.which", side_effect=fake_which):
            payload = list_openers()

        openers = {opener["id"]: opener for opener in payload["openers"]}
        self.assertEqual(payload["default"], "auto-terminal")
        self.assertIn("auto-terminal", openers)
        self.assertEqual(openers["vscode"]["capabilities"], ["open_project"])
        self.assertTrue(openers["vscode"]["available"])
        self.assertFalse(openers["cursor"]["available"])
        self.assertIn("cursor CLI not found", openers["cursor"]["reason"])

    def test_macos_terminal_app_detection_checks_system_location(self):
        """Terminal.app lives under /System/Applications/Utilities on modern macOS."""
        def fake_exists(path: Path) -> bool:
            return str(path) == "/System/Applications/Utilities/Terminal.app"

        with (
            patch("cc_branch.openers.sys.platform", "darwin"),
            patch("cc_branch.openers.shutil.which", return_value="/usr/bin/osascript"),
            patch("cc_branch.openers.Path.exists", fake_exists),
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
            patch("cc_branch.openers.sys.platform", "darwin"),
            patch("cc_branch.openers.shutil.which", side_effect=fake_which),
            patch("cc_branch.openers.Path.exists", fake_exists),
        ):
            payload = list_openers()

        openers = {opener["id"]: opener for opener in payload["openers"]}
        self.assertTrue(openers["warp"]["available"])
        self.assertEqual(openers["warp"]["executable"], "/Applications/Warp.app")

    def test_powershell_single_quote_escapes_embedded_quotes(self):
        """PowerShell single-quoted strings escape apostrophes by doubling them."""
        self.assertEqual(_powershell_single_quote(r"C:\Users\O'Neil\demo"), r"'C:\Users\O''Neil\demo'")

    def test_windows_attach_command_uses_powershell_safe_target_quoting(self):
        """Windows attach commands should not use POSIX quote fragments."""
        with patch("cc_branch.openers.os.name", "nt"):
            command = _intent_command(
                "& 'C:\\Program Files\\cc-branch.exe'",
                OpenIntent(kind="attach_target", target="dev O'Neil"),
            )

        self.assertEqual(command, "& 'C:\\Program Files\\cc-branch.exe' attach 'dev O''Neil'")

    def test_windows_terminal_uses_powershell_literal_path_quoting(self):
        """PowerShell launch commands should preserve spaces and apostrophes in cwd."""
        with (
            patch("cc_branch.openers.shutil.which", return_value="C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"),
            patch("cc_branch.openers._popen") as popen,
        ):
            _open_windows_terminal("powershell", Path("C:/Users/O'Neil/demo project"), "cc-branch dashboard")

        popen_args = popen.call_args.args[0]
        self.assertIn("Set-Location -LiteralPath '", popen_args[-1])
        self.assertIn("O''Neil", popen_args[-1])
        self.assertIn("demo project", popen_args[-1])

    def test_editor_opener_opens_project_folder(self):
        """VS Code opener should open the project folder without shell command injection."""
        with (
            patch("cc_branch.openers.shutil.which", return_value="/usr/local/bin/code"),
            patch("cc_branch.openers.subprocess.Popen") as popen,
        ):
            open_with(
                "vscode",
                cwd=Path("/tmp/demo"),
                cli="cc-branch",
                intent=OpenIntent(kind="project_folder"),
            )

        self.assertEqual(popen.call_args.args[0], ["/usr/local/bin/code", str(Path("/tmp/demo").resolve())])

    def test_editor_opener_rejects_attach_intent(self):
        """Editors must not be treated as attach-capable terminals."""
        with patch("cc_branch.openers.shutil.which", return_value="/usr/local/bin/code"):
            with self.assertRaisesRegex(OpenerError, "does not support attach_target"):
                open_with(
                    "vscode",
                    cwd=Path("/tmp/demo"),
                    cli="cc-branch",
                    intent=OpenIntent(kind="attach_target", target="dev"),
                )

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
