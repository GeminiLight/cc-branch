from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class WindowState:
    """Per-window persisted metadata."""

    session_id: str | None = None
    label: str | None = None
    agent: str | None = None
    slot: str | None = None
    window: str | None = None
    launch_fingerprint: str | None = None
    launch_spec_version: int | None = None
    applied_at: str | None = None
    managed_runtime: str | None = None
    tmux_session: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.session_id is not None:
            result["session_id"] = self.session_id
        if self.label is not None:
            result["label"] = self.label
        if self.agent is not None:
            result["agent"] = self.agent
        if self.slot is not None:
            result["slot"] = self.slot
        if self.window is not None:
            result["window"] = self.window
        if self.launch_fingerprint is not None:
            result["launch_fingerprint"] = self.launch_fingerprint
        if self.launch_spec_version is not None:
            result["launch_spec_version"] = self.launch_spec_version
        if self.applied_at is not None:
            result["applied_at"] = self.applied_at
        if self.managed_runtime is not None:
            result["managed_runtime"] = self.managed_runtime
        if self.tmux_session is not None:
            result["tmux_session"] = self.tmux_session
        return result


@dataclass
class SlotState:
    """Per-slot runtime metadata used to identify previous tmux sessions."""

    name: str | None = None
    tmux_session: str | None = None
    runtime: str | None = None
    last_seen_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.name is not None:
            result["name"] = self.name
        if self.tmux_session is not None:
            result["tmux_session"] = self.tmux_session
        if self.runtime is not None:
            result["runtime"] = self.runtime
        if self.last_seen_at is not None:
            result["last_seen_at"] = self.last_seen_at
        return result


@dataclass
class WorkspaceState:
    """Top-level runtime state."""

    version: int = 1
    windows: dict[str, WindowState] = field(default_factory=dict)
    slots: dict[str, SlotState] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceState:
        raw_windows = data.get("windows", {})
        windows: dict[str, WindowState] = {}
        for key, entry in raw_windows.items():
            if isinstance(entry, dict):
                windows[key] = WindowState(
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
        slots: dict[str, SlotState] = {}
        for key, entry in raw_slots.items():
            if isinstance(entry, dict):
                slots[key] = SlotState(
                    name=entry.get("name"),
                    tmux_session=entry.get("tmux_session"),
                    runtime=entry.get("runtime"),
                    last_seen_at=entry.get("last_seen_at"),
                )
        return cls(version=int(data.get("version", 1)), windows=windows, slots=slots)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "windows": {k: v.to_dict() for k, v in self.windows.items()},
            "slots": {k: v.to_dict() for k, v in self.slots.items()},
        }

    def get_window(self, key: str) -> WindowState | None:
        """Return the window state for *key* or None."""
        return self.windows.get(key)

    def set_window(self, key: str, entry: WindowState) -> None:
        """Persist *entry* under *key*."""
        self.windows[key] = entry


@dataclass
class AppliedWindowResult:
    """A runtime operation result for one planned window."""

    slot: str
    window: str
    key: str
    runtime: str
    tmux_session: str
    action: Literal["created", "recreated", "already_present", "opened_external", "skipped"]
    launch_fingerprint: str | None = None

