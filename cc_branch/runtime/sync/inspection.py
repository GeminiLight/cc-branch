"""Runtime inspection for sync reports."""

from __future__ import annotations


def tmux_has_session(session: str) -> bool:
    """Return whether a tmux session exists."""
    import cc_branch.runtime.sync as sync

    return sync.get_backend().has_session(session)


def list_window_names(session: str) -> set[str]:
    """Return window names in a tmux session."""
    import cc_branch.runtime.sync as sync

    return sync.get_backend().list_windows(session)
