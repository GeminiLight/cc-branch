"""Compatibility facade for shell command helpers."""

from __future__ import annotations

from .runtime.shells import (
    default_shell_command,
    tmux_attach_shell_command,
    tmux_install_hint,
    wrap_login_shell,
)

__all__ = [
    "default_shell_command",
    "tmux_attach_shell_command",
    "tmux_install_hint",
    "wrap_login_shell",
]
