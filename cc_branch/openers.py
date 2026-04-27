"""Local application openers for Web UI workspace actions."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

OpenIntentKind = Literal["workspace_dashboard", "attach_target", "project_folder"]
OpenerKind = Literal["terminal", "editor"]


class OpenerError(RuntimeError):
    """Raised when an opener cannot handle the requested action."""


@dataclass(frozen=True)
class OpenIntent:
    """A user-level intent for opening a workspace target."""

    kind: OpenIntentKind
    target: str | None = None


@dataclass(frozen=True)
class OpenerInfo:
    """Serializable metadata for an opener."""

    id: str
    label: str
    kind: OpenerKind
    available: bool
    capabilities: list[str]
    source: str = "builtin"
    executable: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict:
        payload = {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "available": self.available,
            "capabilities": self.capabilities,
            "source": self.source,
        }
        if self.executable:
            payload["executable"] = self.executable
        if self.reason:
            payload["reason"] = self.reason
        return payload


TERMINAL_CAPABILITIES = ["run_command", "dashboard", "attach_target"]
PROJECT_CAPABILITIES = ["open_project"]


def list_openers(default: str = "auto-terminal") -> dict:
    """Return serializable opener metadata for the current machine."""
    return {
        "default": default,
        "openers": [info.to_dict() for info in _builtin_openers()],
    }


def opener_label(opener_id: str) -> str:
    """Return a human-friendly label for *opener_id*."""
    info = _opener_info(opener_id)
    return info.label if info else opener_id


def open_with(opener_id: str, *, cwd: Path, cli: str, intent: OpenIntent) -> None:
    """Open *intent* using the registered opener."""
    opener_id = opener_id or "auto-terminal"
    info = _opener_info(opener_id)
    if info is None:
        raise OpenerError(f"Unknown opener: {opener_id}")
    if not info.available:
        detail = f": {info.reason}" if info.reason else ""
        raise OpenerError(f"Opener {opener_id} is not available{detail}")

    _validate_capability(info, intent)
    cwd = cwd.expanduser().resolve()

    if intent.kind == "project_folder":
        _open_project(opener_id, info, cwd)
        return

    command = _intent_command(cli, intent)
    if opener_id == "auto-terminal":
        _open_system_terminal(cwd, command)
    elif opener_id == "terminal-app":
        _open_macos_terminal(cwd, command)
    elif opener_id == "iterm2":
        _open_iterm2(cwd, command)
    elif opener_id in {"windows-terminal", "powershell"}:
        _open_windows_terminal(opener_id, cwd, command)
    elif opener_id in {"gnome-terminal", "konsole", "xfce4-terminal", "xterm", "wezterm", "alacritty"}:
        _open_linux_terminal(opener_id, cwd, command)
    else:
        raise OpenerError(f"Opener {opener_id} does not support command execution")


def _builtin_openers() -> list[OpenerInfo]:
    openers: list[OpenerInfo] = [_auto_terminal_info()]

    if sys.platform == "darwin":
        openers.extend([
            _macos_app_info("terminal-app", "Terminal.app", "Terminal"),
            _macos_app_info("iterm2", "iTerm2", "iTerm"),
            _macos_app_info("warp", "Warp", "Warp", capabilities=PROJECT_CAPABILITIES, kind="editor"),
        ])
    elif os.name == "nt":
        openers.extend([
            _command_info("windows-terminal", "Windows Terminal", "wt", TERMINAL_CAPABILITIES, kind="terminal"),
            _command_info("powershell", "PowerShell", "powershell", TERMINAL_CAPABILITIES, kind="terminal"),
        ])
    else:
        openers.extend([
            _command_info("gnome-terminal", "GNOME Terminal", "gnome-terminal", TERMINAL_CAPABILITIES, kind="terminal"),
            _command_info("konsole", "Konsole", "konsole", TERMINAL_CAPABILITIES, kind="terminal"),
            _command_info("xfce4-terminal", "XFCE Terminal", "xfce4-terminal", TERMINAL_CAPABILITIES, kind="terminal"),
            _command_info("xterm", "xterm", "xterm", TERMINAL_CAPABILITIES, kind="terminal"),
            _command_info("wezterm", "WezTerm", "wezterm", TERMINAL_CAPABILITIES, kind="terminal"),
            _command_info("alacritty", "Alacritty", "alacritty", TERMINAL_CAPABILITIES, kind="terminal"),
        ])

    openers.extend([
        _command_info("vscode", "VS Code", "code", PROJECT_CAPABILITIES, kind="editor"),
        _command_info("cursor", "Cursor", "cursor", PROJECT_CAPABILITIES, kind="editor"),
    ])
    return openers


def _opener_info(opener_id: str) -> OpenerInfo | None:
    for info in _builtin_openers():
        if info.id == opener_id:
            return info
    return None


def _command_info(
    opener_id: str,
    label: str,
    command: str,
    capabilities: list[str],
    *,
    kind: OpenerKind,
) -> OpenerInfo:
    executable = shutil.which(command)
    return OpenerInfo(
        id=opener_id,
        label=label,
        kind=kind,
        available=executable is not None,
        capabilities=capabilities,
        executable=executable,
        reason=None if executable else f"{command} CLI not found",
    )


def _macos_app_info(
    opener_id: str,
    label: str,
    app_name: str,
    *,
    capabilities: list[str] = TERMINAL_CAPABILITIES,
    kind: OpenerKind = "terminal",
) -> OpenerInfo:
    if "run_command" in capabilities and shutil.which("osascript") is None:
        return OpenerInfo(
            id=opener_id,
            label=label,
            kind=kind,
            available=False,
            capabilities=capabilities,
            reason="osascript is not available",
        )
    app_path = _find_macos_app(app_name)
    if app_path is None:
        return OpenerInfo(
            id=opener_id,
            label=label,
            kind=kind,
            available=False,
            capabilities=capabilities,
            reason=f"{label} not found",
        )
    return OpenerInfo(
        id=opener_id,
        label=label,
        kind=kind,
        available=True,
        capabilities=capabilities,
        executable=str(app_path),
    )


def _find_macos_app(app_name: str) -> Path | None:
    candidates = [
        Path("/Applications") / f"{app_name}.app",
        Path.home() / "Applications" / f"{app_name}.app",
        Path("/System/Applications") / f"{app_name}.app",
        Path("/System/Applications/Utilities") / f"{app_name}.app",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _auto_terminal_info() -> OpenerInfo:
    reason = _auto_terminal_unavailable_reason()
    return OpenerInfo(
        id="auto-terminal",
        label="System Terminal",
        kind="terminal",
        available=reason is None,
        capabilities=TERMINAL_CAPABILITIES,
        reason=reason,
    )


def _auto_terminal_unavailable_reason() -> str | None:
    if sys.platform == "darwin":
        return None if shutil.which("osascript") else "osascript is not available"
    if os.name == "nt":
        return None if shutil.which("powershell") else "powershell is not available"
    candidates = [
        "x-terminal-emulator",
        "gnome-terminal",
        "konsole",
        "xfce4-terminal",
        "xterm",
        "wezterm",
        "alacritty",
    ]
    return None if any(shutil.which(candidate) for candidate in candidates) else "no supported terminal emulator was found"


def _validate_capability(info: OpenerInfo, intent: OpenIntent) -> None:
    required = {
        "workspace_dashboard": "dashboard",
        "attach_target": "attach_target",
        "project_folder": "open_project",
    }[intent.kind]
    if required not in info.capabilities:
        raise OpenerError(
            f"Opener {info.id} does not support {intent.kind}. "
            "Use a compatible opener or choose another intent."
        )
    if intent.kind == "attach_target" and not intent.target:
        raise OpenerError("attach_target requires a target")


def _intent_command(cli: str, intent: OpenIntent) -> str:
    if intent.kind == "workspace_dashboard":
        return f"{cli} dashboard"
    if intent.kind == "attach_target":
        if not intent.target:
            raise OpenerError("attach_target requires a target")
        return f"{cli} attach {_argument_quote(intent.target)}"
    raise OpenerError(f"Intent {intent.kind} does not produce a shell command")


def _argument_quote(value: str) -> str:
    if os.name == "nt":
        return _powershell_single_quote(value)
    return shlex.quote(value)


def _powershell_single_quote(value: str) -> str:
    """Return *value* as a PowerShell single-quoted string literal."""
    return "'" + value.replace("'", "''") + "'"


def _shell_command(cwd: Path, command: str) -> str:
    return f"cd {shlex.quote(str(cwd))} && {command}"


def _open_project(opener_id: str, info: OpenerInfo, cwd: Path) -> None:
    if opener_id == "warp" and sys.platform == "darwin":
        _popen(["open", "-a", "Warp", str(cwd)])
        return
    executable = info.executable
    if not executable:
        raise OpenerError(f"Opener {opener_id} is not available")
    _popen([executable, str(cwd)])


def _open_system_terminal(cwd: Path, command: str) -> None:
    if sys.platform == "darwin":
        _open_macos_terminal(cwd, command)
        return
    if os.name == "nt":
        _open_windows_terminal("powershell", cwd, command)
        return
    for opener_id in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm", "wezterm", "alacritty"]:
        info = _opener_info(opener_id)
        if info and info.available:
            _open_linux_terminal(opener_id, cwd, command)
            return
    executable = shutil.which("x-terminal-emulator")
    if executable:
        shell = os.environ.get("SHELL") or "/bin/sh"
        command_with_hold = f"{_shell_command(cwd, command)}; exec {shlex.quote(shell)}"
        _popen([executable, "-e", shell, "-lc", command_with_hold])
        return
    raise OpenerError("Cannot open a terminal: no supported terminal emulator was found")


def _open_macos_terminal(cwd: Path, command: str) -> None:
    if shutil.which("osascript") is None:
        raise OpenerError("Cannot open Terminal: osascript is not available")
    script = (
        'tell application "Terminal"\n'
        "activate\n"
        f"do script {json.dumps(_shell_command(cwd, command))}\n"
        "end tell"
    )
    _run_osascript(script, "Cannot open Terminal")


def _open_iterm2(cwd: Path, command: str) -> None:
    if shutil.which("osascript") is None:
        raise OpenerError("Cannot open iTerm2: osascript is not available")
    shell_command = _shell_command(cwd, command)
    script = (
        'tell application "iTerm"\n'
        "activate\n"
        "set newWindow to (create window with default profile)\n"
        f"tell current session of newWindow to write text {json.dumps(shell_command)}\n"
        "end tell"
    )
    _run_osascript(script, "Cannot open iTerm2")


def _run_osascript(script: str, failure_prefix: str) -> None:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        message = failure_prefix
        if detail:
            message = f"{message}: {detail}"
        raise OpenerError(message)


def _open_windows_terminal(opener_id: str, cwd: Path, command: str) -> None:
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


def _open_linux_terminal(opener_id: str, cwd: Path, command: str) -> None:
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


def _popen(args: list[str]) -> None:
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
