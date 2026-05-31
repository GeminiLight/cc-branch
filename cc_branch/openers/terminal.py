"""Terminal opener implementations."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .commands import _powershell_single_quote, _shell_command
from .platform import _popen
from .types import OpenerError


@dataclass(frozen=True)
class TerminalLauncher:
    """Launches supported terminal applications on the local operating system."""

    def open_system(self, cwd: Path, command: str) -> None:
        if sys.platform == "darwin":
            self.open_macos_terminal(cwd, command)
            return
        if os.name == "nt":
            self.open_windows("powershell", cwd, command)
            return
        for opener_id in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm", "wezterm", "alacritty"]:
            if shutil.which(opener_id):
                self.open_linux(opener_id, cwd, command)
                return
        executable = shutil.which("x-terminal-emulator")
        if executable:
            shell = os.environ.get("SHELL") or "/bin/sh"
            command_with_hold = f"{_shell_command(cwd, command)}; exec {shlex.quote(shell)}"
            _popen([executable, "-e", shell, "-lc", command_with_hold])
            return
        raise OpenerError("Cannot open a terminal: no supported terminal emulator was found")

    def open_macos_app_project(self, app_name: str, cwd: Path) -> None:
        executable = shutil.which("open")
        if not executable:
            raise OpenerError(f"Cannot open {app_name}: open is not available")
        _popen([executable, "-a", app_name, str(cwd)])

    def open_macos_terminal(self, cwd: Path, command: str) -> None:
        if shutil.which("osascript") is None:
            raise OpenerError("Cannot open Terminal: osascript is not available")
        script = (
            'tell application "Terminal"\n'
            "activate\n"
            f"do script {json.dumps(_shell_command(cwd, command))}\n"
            "end tell"
        )
        self.run_osascript(script, "Cannot open Terminal")

    def open_iterm2(self, cwd: Path, command: str) -> None:
        if shutil.which("osascript") is None:
            raise OpenerError("Cannot open iTerm2: osascript is not available")
        shell_command = _shell_command(cwd, command)
        script = (
            'tell application "iTerm2"\n'
            "activate\n"
            "create window with default profile\n"
            "repeat 20 times\n"
            "if exists current window then exit repeat\n"
            "delay 0.1\n"
            "end repeat\n"
            "delay 0.5\n"
            f"tell current session of current window to write text {json.dumps(shell_command)}\n"
            "end tell"
        )
        self.run_osascript(script, "Cannot open iTerm2")

    def run_osascript(self, script: str, failure_prefix: str) -> None:
        args = ["osascript"]
        for line in script.splitlines():
            if line.strip():
                args.extend(["-e", line])
        try:
            result = subprocess.run(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=30,
            )
        except subprocess.TimeoutExpired as error:
            raise OpenerError(f"{failure_prefix}: AppleScript timed out") from error
        if result.returncode != 0:
            detail = result.stderr.strip()
            message = failure_prefix
            if detail:
                message = f"{message}: {detail}"
            raise OpenerError(message)

    def open_windows(self, opener_id: str, cwd: Path, command: str) -> None:
        quoted_command = f"Set-Location -LiteralPath {_powershell_single_quote(str(cwd))}; {command}"
        if opener_id == "windows-terminal" and shutil.which("wt"):
            _popen(["wt", "powershell", "-NoExit", "-Command", quoted_command])
            return
        if shutil.which("powershell") is None:
            raise OpenerError("Cannot open PowerShell: powershell is not available")
        _popen([
            "powershell",
            "-NoProfile",
            "-Command",
            f"Start-Process powershell -ArgumentList @('-NoExit', '-Command', {json.dumps(quoted_command)})",
        ])

    def open_linux(self, opener_id: str, cwd: Path, command: str) -> None:
        shell = os.environ.get("SHELL") or "/bin/sh"
        command_with_hold = f"{_shell_command(cwd, command)}; exec {shlex.quote(shell)}"
        args_by_id = {
            "gnome-terminal": ["gnome-terminal", "--", shell, "-lc", command_with_hold],
            "konsole": ["konsole", "-e", shell, "-lc", command_with_hold],
            "xfce4-terminal": ["xfce4-terminal", "--command", f"{shell} -lc {shlex.quote(command_with_hold)}"],
            "xterm": ["xterm", "-e", shell, "-lc", command_with_hold],
            "wezterm": ["wezterm", "start", "--cwd", str(cwd), "--", shell, "-lc", command_with_hold],
            "alacritty": ["alacritty", "--working-directory", str(cwd), "-e", shell, "-lc", command_with_hold],
        }
        args = args_by_id.get(opener_id)
        if not args:
            raise OpenerError(f"Unknown terminal opener: {opener_id}")
        executable = shutil.which(args[0])
        if not executable:
            raise OpenerError(f"Cannot open {opener_id}: {args[0]} CLI not found")
        args[0] = executable
        _popen(args)


terminal_launcher = TerminalLauncher()


def _open_system_terminal(cwd: Path, command: str) -> None:
    terminal_launcher.open_system(cwd, command)


def _open_macos_app_project(app_name: str, cwd: Path) -> None:
    terminal_launcher.open_macos_app_project(app_name, cwd)


def _open_macos_terminal(cwd: Path, command: str) -> None:
    terminal_launcher.open_macos_terminal(cwd, command)


def _open_iterm2(cwd: Path, command: str) -> None:
    terminal_launcher.open_iterm2(cwd, command)


def _run_osascript(script: str, failure_prefix: str) -> None:
    terminal_launcher.run_osascript(script, failure_prefix)


def _open_windows_terminal(opener_id: str, cwd: Path, command: str) -> None:
    terminal_launcher.open_windows(opener_id, cwd, command)


def _open_linux_terminal(opener_id: str, cwd: Path, command: str) -> None:
    terminal_launcher.open_linux(opener_id, cwd, command)
