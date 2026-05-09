"""Local application openers for Web UI workspace actions."""

from __future__ import annotations

from .commands import (
    _intent_command,
    _powershell_single_quote,
)
from .dispatcher import (
    OpenerDispatcher,
    open_command,
    open_command_layout,
    open_with,
    open_workspace_file,
)
from .editors import EditorWorkspaceOpener
from .registry import OpenerRegistry, list_openers, opener_label, opener_supports
from .terminal import TerminalLauncher, _open_system_terminal, _open_windows_terminal
from .types import (
    EDITOR_WORKSPACE_CAPABILITIES,
    PROJECT_CAPABILITIES,
    TERMINAL_CAPABILITIES,
    WARP_CAPABILITIES,
    OpenCommandSpec,
    OpenIntent,
    OpenIntentKind,
    OpenerError,
    OpenerInfo,
    OpenerKind,
)
from .warp import WarpLauncher

__all__ = [
    "EDITOR_WORKSPACE_CAPABILITIES",
    "PROJECT_CAPABILITIES",
    "TERMINAL_CAPABILITIES",
    "WARP_CAPABILITIES",
    "OpenCommandSpec",
    "OpenIntent",
    "OpenIntentKind",
    "OpenerError",
    "OpenerInfo",
    "OpenerKind",
    "OpenerDispatcher",
    "EditorWorkspaceOpener",
    "OpenerRegistry",
    "TerminalLauncher",
    "WarpLauncher",
    "list_openers",
    "opener_label",
    "opener_supports",
    "open_command",
    "open_command_layout",
    "open_with",
    "open_workspace_file",
    "_intent_command",
    "_open_system_terminal",
    "_open_windows_terminal",
    "_powershell_single_quote",
]
