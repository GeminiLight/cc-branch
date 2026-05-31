"""Runtime sync data contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

LAUNCH_SPEC_VERSION = 1
SyncStatus = Literal["current", "changed", "missing", "extra", "orphaned", "untracked", "external"]


@dataclass
class WindowSyncStatus:
    """Synchronization state for one planned or extra window."""

    name: str
    key: str
    runtime_status: str
    sync_status: SyncStatus
    needs_restart: bool = False
    desired_fingerprint: str | None = None
    applied_fingerprint: str | None = None
    change_reason: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "key": self.key,
            "runtime_status": self.runtime_status,
            "sync_status": self.sync_status,
            "needs_restart": self.needs_restart,
            "desired_fingerprint": self.desired_fingerprint,
            "applied_fingerprint": self.applied_fingerprint,
            "change_reason": self.change_reason,
        }


@dataclass
class SlotSyncStatus:
    """Synchronization state for a slot."""

    name: str
    runtime: str
    tmux_session: str
    sync_status: SyncStatus
    windows: list[WindowSyncStatus] = field(default_factory=list)
    extra_windows: list[WindowSyncStatus] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "runtime": self.runtime,
            "tmux_session": self.tmux_session,
            "sync_status": self.sync_status,
            "windows": [window.to_dict() for window in self.windows],
            "extra_windows": [window.to_dict() for window in self.extra_windows],
        }


@dataclass
class RuntimeSyncReport:
    """Workspace-level synchronization report."""

    summary: dict[str, int]
    slots: list[SlotSyncStatus]
    orphaned_state: list[dict] = field(default_factory=list)
    historical_sessions: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "slots": [slot.to_dict() for slot in self.slots],
            "orphaned_state": self.orphaned_state,
            "historical_sessions": self.historical_sessions,
        }
