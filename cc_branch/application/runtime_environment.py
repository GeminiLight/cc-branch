"""Runtime availability queries shared by CLI and Web UI surfaces."""

from __future__ import annotations

from ..runtime.backends import get_backend


def runtime_availability() -> dict[str, dict[str, object]]:
    """Return local runtime availability for presentation surfaces."""
    tmux_available = get_backend().available()
    tmux: dict[str, object] = {"available": tmux_available}
    if not tmux_available:
        tmux["reason"] = "tmux was not found on PATH"
    return {
        "tmux": tmux,
        "terminal": {"available": True},
    }
