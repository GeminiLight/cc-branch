from __future__ import annotations

import os
from pathlib import Path
from shutil import which as shutil_which


def _windows_shell() -> str:
    for candidate in ("pwsh", "powershell"):
        if shutil_which(candidate):
            return candidate
    return "cmd"


def default_shell_command() -> str:
    """Return a platform-appropriate interactive shell command."""
    if os.name == "nt":
        return _windows_shell()

    configured_shell = os.environ.get("SHELL")
    if configured_shell:
        return Path(configured_shell).name or configured_shell

    for candidate in ("zsh", "bash", "sh"):
        if shutil_which(candidate):
            return candidate
    return "sh"


def wrap_login_shell(command: str) -> list[str]:
    """Wrap a command so tmux launches it in a login-capable shell."""
    if os.name == "nt":
        shell = _windows_shell()
        if shell == "cmd":
            return [shell, "/C", command]
        return [shell, "-NoLogo", "-Command", command]

    configured_shell = os.environ.get("SHELL")
    shell = configured_shell or shutil_which("sh") or "sh"
    return [shell, "-lc", command]


def tmux_attach_shell_command(target: str) -> list[str]:
    """Return a shell command that attaches a pane to another tmux session."""
    if os.name == "nt":
        return wrap_login_shell(f'$env:TMUX=""; tmux attach-session -t "{target}"')
    return wrap_login_shell(f'TMUX= tmux attach-session -t "{target}"')


def tmux_install_hint() -> str:
    """Return an OS-aware tmux installation hint."""
    return (
        "Install tmux (macOS: brew install tmux, Linux: apt-get install tmux, "
        "Windows: use WSL/MSYS2/Cygwin and ensure tmux is on PATH)"
    )
