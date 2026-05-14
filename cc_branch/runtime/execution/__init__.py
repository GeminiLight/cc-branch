"""Runtime execution facade.

Execution is split into backend operations, target resolution, window creation,
lifecycle commands, dashboard handling, and status rendering. This facade keeps
the historical ``cc_branch.runtime.execution`` patch/import surface stable.
"""

from __future__ import annotations

import subprocess  # noqa: F401  # retained for test patch compatibility

from ...openers import open_command
from ..backends import get_backend
from ..shells import tmux_attach_shell_command
from .backend_ops import send_keys, tmux_has_session, tmux_has_window, which
from .dashboard import (
    dashboard_layout as _dashboard_layout,
)
from .dashboard import (
    dashboard_session_name as _dashboard_session_name,
)
from .dashboard import (
    kill_dashboard as _kill_dashboard,
)
from .dashboard import (
    open_dashboard,
)
from .lifecycle import (
    apply_workspace,
    attach_slot,
    restart_workspace,
    stop_extra_windows,
    stop_workspace,
)
from .status import (
    build_status_data,
    format_status,
)
from .status import (
    list_window_names as _list_window_names,
)
from .targets import get_window as _get_window
from .targets import resolve_target as _resolve_target
from .targets import resolve_target_slots as _resolve_target_slots
from .windows import (
    ensure_slot,
)
from .windows import (
    ensure_terminal_slot as _ensure_terminal_slot,
)
from .windows import (
    ensure_window as _ensure_window,
)

POST_LAUNCH_DELAY: float = 0.2

__all__ = [
    "POST_LAUNCH_DELAY",
    "_dashboard_layout",
    "_dashboard_session_name",
    "_ensure_terminal_slot",
    "_ensure_window",
    "_get_window",
    "_kill_dashboard",
    "_list_window_names",
    "_resolve_target",
    "_resolve_target_slots",
    "apply_workspace",
    "attach_slot",
    "build_status_data",
    "ensure_slot",
    "format_status",
    "get_backend",
    "open_command",
    "open_dashboard",
    "restart_workspace",
    "send_keys",
    "stop_extra_windows",
    "stop_workspace",
    "subprocess",
    "tmux_attach_shell_command",
    "tmux_has_session",
    "tmux_has_window",
    "which",
]
