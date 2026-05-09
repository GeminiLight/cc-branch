"""Public opener dispatch operations."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from ..models import OpenerSpec
from .commands import (
    _intent_command,
    _intent_title,
    _project_shell_command,
    _validate_capability,
)
from .editors import EditorWorkspaceOpener, editor_workspace_opener
from .platform import _open_path, _popen
from .registry import _opener_info
from .terminal import (
    TerminalLauncher,
    terminal_launcher,
)
from .types import OpenCommandSpec, OpenerError, OpenerInfo, OpenIntent
from .warp import WarpLauncher, warp_launcher


@dataclass(frozen=True)
class OpenerDispatcher:
    """Routes high-level opener requests to the right concrete opener adapter."""

    custom_openers: dict[str, OpenerSpec] | None = None
    terminal: TerminalLauncher = terminal_launcher
    editor: EditorWorkspaceOpener = editor_workspace_opener
    warp: WarpLauncher = warp_launcher

    def open_with(self, opener_id: str, *, cwd: Path, cli: str, intent: OpenIntent) -> None:
        opener_id = opener_id or "auto-terminal"
        info = self.available_opener(opener_id)

        _validate_capability(info, intent)
        cwd = cwd.expanduser().resolve()

        if intent.kind == "project_folder":
            self.open_project(opener_id, info, cwd)
            return

        command = _intent_command(cli, intent)
        if opener_id in (self.custom_openers or {}):
            self.open_custom(opener_id, cwd=cwd, command=command)
            return
        self.open_builtin_command(opener_id, cwd, command, title=_intent_title(intent))

    def open_command(self, opener_id: str, *, cwd: Path, command: str) -> None:
        opener_id = opener_id or "auto-terminal"
        info = self.available_opener(opener_id)
        if "run_command" not in info.capabilities:
            raise OpenerError(f"Opener {opener_id} does not support running commands")
        cwd = cwd.expanduser().resolve()
        if opener_id in (self.custom_openers or {}):
            self.open_custom(opener_id, cwd=cwd, command=command)
            return
        self.open_builtin_command(opener_id, cwd, command, title="CC Branch")

    def open_command_layout(self, opener_id: str, commands: list[OpenCommandSpec]) -> None:
        if not commands:
            return
        opener_id = opener_id or "auto-terminal"
        info = self.available_opener(opener_id)
        if "run_command" not in info.capabilities:
            raise OpenerError(f"Opener {opener_id} does not support running commands")

        resolved = [
            OpenCommandSpec(title=spec.title, cwd=spec.cwd.expanduser().resolve(), command=spec.command)
            for spec in commands
        ]
        if opener_id == "warp":
            self.warp.open_layout(resolved)
            return

        for spec in resolved:
            self.open_command(opener_id, cwd=spec.cwd, command=spec.command)

    def open_workspace_file(self, opener_id: str, *, cwd: Path, commands: list[OpenCommandSpec]) -> None:
        opener_id = opener_id or "auto-terminal"
        info = self.available_opener(opener_id)
        if "workspace_file" not in info.capabilities:
            raise OpenerError(f"Opener {opener_id} does not support workspace files")

        cwd = cwd.expanduser().resolve()
        resolved = [
            OpenCommandSpec(title=spec.title, cwd=spec.cwd.expanduser().resolve(), command=spec.command)
            for spec in commands
        ]
        self.editor.open(opener_id, info, cwd, resolved)

    def available_opener(self, opener_id: str) -> OpenerInfo:
        info = _opener_info(opener_id, self.custom_openers)
        if info is None:
            raise OpenerError(f"Unknown opener: {opener_id}")
        if not info.available:
            detail = f": {info.reason}" if info.reason else ""
            raise OpenerError(f"Opener {opener_id} is not available{detail}")
        return info

    def open_builtin_command(self, opener_id: str, cwd: Path, command: str, *, title: str) -> None:
        if opener_id == "auto-terminal":
            self.terminal.open_system(cwd, command)
        elif opener_id == "terminal-app":
            self.terminal.open_macos_terminal(cwd, command)
        elif opener_id == "iterm2":
            self.terminal.open_iterm2(cwd, command)
        elif opener_id == "warp":
            self.warp.open_command(cwd, command, title=title)
        elif opener_id in {"windows-terminal", "powershell"}:
            self.terminal.open_windows(opener_id, cwd, command)
        elif opener_id in {"gnome-terminal", "konsole", "xfce4-terminal", "xterm", "wezterm", "alacritty"}:
            self.terminal.open_linux(opener_id, cwd, command)
        else:
            raise OpenerError(f"Opener {opener_id} does not support command execution")

    def open_project(self, opener_id: str, info: OpenerInfo, cwd: Path) -> None:
        if opener_id == "system-file-manager":
            _open_path(cwd)
            return
        if opener_id in (self.custom_openers or {}):
            self.open_custom(opener_id, cwd=cwd, command="")
            return
        if opener_id == "warp":
            self.warp.open_uri(f"warp://action/new_window?path={quote(str(cwd), safe='')}")
            return
        if opener_id == "auto-terminal":
            self.terminal.open_system(cwd, _project_shell_command())
            return
        if opener_id == "terminal-app":
            self.terminal.open_macos_app_project("Terminal", cwd)
            return
        if opener_id == "iterm2":
            self.terminal.open_macos_app_project("iTerm", cwd)
            return
        if opener_id in {"windows-terminal", "powershell"}:
            self.terminal.open_windows(opener_id, cwd, "")
            return
        if opener_id in {"gnome-terminal", "konsole", "xfce4-terminal", "xterm", "wezterm", "alacritty"}:
            self.terminal.open_linux(opener_id, cwd, _project_shell_command())
            return
        executable = info.executable
        if not executable:
            raise OpenerError(f"Opener {opener_id} is not available")
        _popen([executable, str(cwd)])

    def open_custom(self, opener_id: str, *, cwd: Path, command: str) -> None:
        spec = (self.custom_openers or {}).get(opener_id)
        if spec is None:
            raise OpenerError(f"Unknown opener: {opener_id}")
        executable = shutil.which(spec.command)
        if not executable:
            raise OpenerError(f"Cannot open {opener_id}: {spec.command or opener_id} CLI not found")
        args = [executable, *_render_custom_args(spec.args, cwd=cwd, command=command)]
        _popen(args)


def open_with(
    opener_id: str,
    *,
    cwd: Path,
    cli: str,
    intent: OpenIntent,
    custom_openers: dict[str, OpenerSpec] | None = None,
) -> None:
    """Open *intent* using the registered opener."""
    OpenerDispatcher(custom_openers).open_with(opener_id, cwd=cwd, cli=cli, intent=intent)


def open_command(
    opener_id: str,
    *,
    cwd: Path,
    command: str,
    custom_openers: dict[str, OpenerSpec] | None = None,
) -> None:
    """Open a visible terminal and run an already-resolved command."""
    OpenerDispatcher(custom_openers).open_command(opener_id, cwd=cwd, command=command)


def open_command_layout(
    opener_id: str,
    commands: list[OpenCommandSpec],
    *,
    custom_openers: dict[str, OpenerSpec] | None = None,
) -> None:
    """Open multiple visible terminal commands using a native layout when available."""
    OpenerDispatcher(custom_openers).open_command_layout(opener_id, commands)


def open_workspace_file(
    opener_id: str,
    *,
    cwd: Path,
    commands: list[OpenCommandSpec],
    custom_openers: dict[str, OpenerSpec] | None = None,
) -> None:
    """Open an editor workspace file that exposes workspace commands as tasks."""
    OpenerDispatcher(custom_openers).open_workspace_file(opener_id, cwd=cwd, commands=commands)


def _available_opener(
    opener_id: str,
    custom_openers: dict[str, OpenerSpec] | None,
) -> OpenerInfo:
    return OpenerDispatcher(custom_openers).available_opener(opener_id)


def _open_builtin_command(opener_id: str, cwd: Path, command: str, *, title: str) -> None:
    OpenerDispatcher().open_builtin_command(opener_id, cwd, command, title=title)


def _open_project(
    opener_id: str,
    info: OpenerInfo,
    cwd: Path,
    custom_openers: dict[str, OpenerSpec] | None = None,
) -> None:
    OpenerDispatcher(custom_openers).open_project(opener_id, info, cwd)


def _render_custom_args(args: list[str], *, cwd: Path, command: str) -> list[str]:
    context = {
        "cwd": str(cwd),
        "command": command,
        "target": str(cwd),
    }
    return [arg.format(**context) for arg in args]


def _open_custom(
    opener_id: str,
    custom_openers: dict[str, OpenerSpec],
    *,
    cwd: Path,
    command: str,
) -> None:
    OpenerDispatcher(custom_openers).open_custom(opener_id, cwd=cwd, command=command)
