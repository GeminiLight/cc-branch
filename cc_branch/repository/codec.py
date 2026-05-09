"""Workspace state YAML codec."""

from __future__ import annotations

from typing import Any

from ..models import SlotState, WindowState, WorkspaceState


def state_data(state: WorkspaceState) -> dict[str, Any]:
    """Return a deterministic mapping for YAML serialization."""
    return {
        "version": state.version,
        "windows": {
            key: state.windows[key].to_dict()
            for key in sorted(state.windows)
        },
        "slots": {
            key: state.slots[key].to_dict()
            for key in sorted(state.slots)
        },
    }


def yaml_to_state(data: dict[str, Any]) -> WorkspaceState:
    """Convert a parsed YAML dict into ``WorkspaceState``."""
    state = WorkspaceState(version=int(data.get("version", 1)))
    raw_windows = data.get("windows", {})
    if isinstance(raw_windows, dict):
        for key, entry in raw_windows.items():
            if not isinstance(entry, dict):
                continue
            state.windows[str(key)] = WindowState(
                session_id=entry.get("session_id"),
                label=entry.get("label"),
                agent=entry.get("agent"),
                slot=entry.get("slot"),
                window=entry.get("window"),
                launch_fingerprint=entry.get("launch_fingerprint"),
                launch_spec_version=entry.get("launch_spec_version"),
                applied_at=entry.get("applied_at"),
                managed_runtime=entry.get("managed_runtime"),
                tmux_session=entry.get("tmux_session"),
            )
    raw_slots = data.get("slots", {})
    if isinstance(raw_slots, dict):
        for key, entry in raw_slots.items():
            if not isinstance(entry, dict):
                continue
            state.slots[str(key)] = SlotState(
                name=entry.get("name"),
                tmux_session=entry.get("tmux_session"),
                runtime=entry.get("runtime"),
                last_seen_at=entry.get("last_seen_at"),
            )
    return state
