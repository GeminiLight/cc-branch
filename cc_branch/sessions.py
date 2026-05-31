"""Compatibility facade for session lifecycle APIs."""

from __future__ import annotations

from .runtime.sessions import (
    SessionInfo,
    inspect_session,
    list_sessions,
    prune_sessions,
    restore_session,
)

__all__ = [
    "SessionInfo",
    "inspect_session",
    "list_sessions",
    "prune_sessions",
    "restore_session",
]
