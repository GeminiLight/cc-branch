"""Backend operation helpers for runtime execution."""

from __future__ import annotations


def which(name: str) -> str | None:
    """Return the path to executable *name* or None."""
    import shutil

    return shutil.which(name)


def tmux_has_session(name: str) -> bool:
    """Check whether tmux session *name* exists."""
    import cc_branch.runtime.execution as execution

    return execution.get_backend().has_session(name)


def tmux_has_window(session: str, window: str) -> bool:
    """Check whether *window* exists inside tmux *session*."""
    import cc_branch.runtime.execution as execution

    return execution.get_backend().has_window(session, window)


def send_keys(target: str, command: str) -> None:
    """Send *command* followed by Enter to a tmux target."""
    if not command:
        return
    import cc_branch.runtime.execution as execution

    execution.get_backend().send_keys(target, command)
