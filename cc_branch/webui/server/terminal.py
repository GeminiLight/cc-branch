"""Terminal helper compatibility for Web UI actions."""

from __future__ import annotations

import os
import shlex
import shutil
import sys
from pathlib import Path

from ...openers import OpenIntent, _powershell_single_quote, open_with
from ...runtime.backends import get_backend


def _slot_exists(session_name: str) -> bool:
    """Check if a tmux session exists."""
    return get_backend().has_session(session_name)


def _open_terminal(cwd: Path, command: str) -> None:
    """Open a system terminal and run a cc-branch command in *cwd*."""
    if command.endswith(" dashboard"):
        cli = command[: -len(" dashboard")]
        intent = OpenIntent(kind="workspace_dashboard")
    elif " attach " in command:
        cli, target_fragment = command.rsplit(" attach ", 1)
        try:
            target = shlex.split(target_fragment)[0]
        except (IndexError, ValueError):
            target = target_fragment
        intent = OpenIntent(kind="attach_target", target=target)
    else:
        from ...openers import _open_system_terminal

        _open_system_terminal(cwd, command)
        return
    open_with("auto-terminal", cwd=cwd, cli=cli, intent=intent)


def _cli_command() -> str:
    """Return a shell-safe cc-branch command for a new terminal process."""
    invoked = Path(sys.argv[0]).expanduser()
    if invoked.exists() and invoked.suffix.lower() not in {".py", ".pyc"}:
        resolved = str(invoked.resolve())
        if _uses_powershell_commands():
            return f"& {_powershell_single_quote(resolved)}"
        return shlex.quote(resolved)
    repo_cli = Path(__file__).resolve().parents[3] / "bin" / "cc-branch"
    if repo_cli.exists():
        resolved = str(repo_cli.resolve())
        if _uses_powershell_commands():
            return f"& {_powershell_single_quote(resolved)}"
        return shlex.quote(resolved)
    discovered = shutil.which("cc-branch")
    if discovered:
        if _uses_powershell_commands():
            return f"& {_powershell_single_quote(discovered)}"
        return shlex.quote(discovered)
    return "cc-branch"


def _uses_powershell_commands() -> bool:
    return os.name == "nt" or sys.platform.startswith("win")
