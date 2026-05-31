from __future__ import annotations

import re


def session_key(slot_name: str, window_name: str) -> str:
    """Return the canonical state key for a window."""
    return f"{slot_name}.{window_name}"


def _safe_name(value: str) -> str:
    """Sanitise a string for use in tmux session names."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "workspace"


def tmux_session_name(project: str, slot_name: str) -> str:
    """Generate the tmux session name for a slot."""
    return f"{_safe_name(project)}-{_safe_name(slot_name)}"
