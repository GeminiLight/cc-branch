"""Workspace planner facade."""

from __future__ import annotations

from .commands import _build_label, _build_window_plan, _resolve_agent_field
from .naming import _safe_name, session_key, tmux_session_name
from .paths import _apply_env, _resolve_slot_cwd, _resolve_window_cwd
from .slots import _slot_windows
from .workspace import format_plan, plan_workspace

__all__ = [
    "format_plan",
    "plan_workspace",
    "session_key",
    "tmux_session_name",
    "_apply_env",
    "_build_label",
    "_build_window_plan",
    "_resolve_agent_field",
    "_resolve_slot_cwd",
    "_resolve_window_cwd",
    "_safe_name",
    "_slot_windows",
]
