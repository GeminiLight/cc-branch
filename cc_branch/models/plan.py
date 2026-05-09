from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .common import _as_legacy_dict
from .openers import OpenerSpec


@dataclass
class WindowPlan:
    """Resolved, executable plan for a single window."""

    name: str
    key: str
    agent: str | None
    runtime: str
    opener: str | None
    cwd: str
    env: dict[str, Any]
    resolved_session_id: str | None
    resolved_label: str | None
    launch_command: str
    command_binary: str
    post_launch_commands: list[str]
    bootstrapped: bool
    resume_mode: str
    create_mode: str
    agent_declared: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "key": self.key,
            "agent": self.agent,
            "runtime": self.runtime,
            "opener": self.opener,
            "cwd": self.cwd,
            "env": self.env,
            "resolved_session_id": self.resolved_session_id,
            "resolved_label": self.resolved_label,
            "launch_command": self.launch_command,
            "command_binary": self.command_binary,
            "post_launch_commands": self.post_launch_commands,
            "bootstrapped": self.bootstrapped,
            "resume_mode": self.resume_mode,
            "create_mode": self.create_mode,
            "agent_declared": self.agent_declared,
        }


@dataclass
class SlotPlan:
    """Resolved plan for a slot."""

    name: str
    runtime: str
    opener: str | None
    tmux_session: str
    cwd: str
    windows: list[WindowPlan] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "runtime": self.runtime,
            "opener": self.opener,
            "tmux_session": self.tmux_session,
            "cwd": self.cwd,
            "windows": [w.to_dict() for w in self.windows],
        }


@dataclass
class WorkspacePlan:
    """Fully resolved workspace plan."""

    project: str
    root: str
    openers: dict[str, OpenerSpec] = field(default_factory=dict)
    default_opener: str | None = None
    slots: list[SlotPlan] = field(default_factory=list)
    state_updates: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "root": self.root,
            "openers": {k: _as_legacy_dict(v) for k, v in self.openers.items()},
            "default_opener": self.default_opener,
            "slots": [s.to_dict() for s in self.slots],
            "state_updates": self.state_updates,
        }

    def get_slot(self, name: str) -> SlotPlan | None:
        """Return the slot plan for *name* or None."""
        for slot in self.slots:
            if slot.name == name:
                return slot
        return None

    def get_window(self, slot_name: str, window_name: str) -> WindowPlan | None:
        """Return the window plan or None."""
        slot = self.get_slot(slot_name)
        if slot is None:
            return None
        for window in slot.windows:
            if window.name == window_name:
                return window
        return None

    def iter_windows(self):
        """Yield (slot, window) pairs across all slots."""
        for slot in self.slots:
            for window in slot.windows:
                yield slot, window

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspacePlan:
        """Best-effort conversion from a legacy plan dict."""
        slots: list[SlotPlan] = []
        for slot in data.get("slots", []):
            windows: list[WindowPlan] = []
            for w in slot.get("windows", []):
                windows.append(
                    WindowPlan(
                        name=w.get("name", ""),
                        key=w.get("key", ""),
                        agent=w.get("agent"),
                        runtime=w.get("runtime", "tmux"),
                        opener=w.get("opener"),
                        cwd=w.get("cwd", "."),
                        env=w.get("env", {}),
                        resolved_session_id=w.get("resolved_session_id"),
                        resolved_label=w.get("resolved_label"),
                        launch_command=w.get("launch_command", ""),
                        command_binary=w.get("command_binary", ""),
                        post_launch_commands=w.get("post_launch_commands", []),
                        bootstrapped=w.get("bootstrapped", False),
                        resume_mode=w.get("resume_mode", "none"),
                        create_mode=w.get("create_mode", "none"),
                        agent_declared=w.get("agent_declared", True),
                    )
                )
            slots.append(
                SlotPlan(
                    name=slot.get("name", ""),
                    runtime=slot.get("runtime", "tmux"),
                    opener=slot.get("opener"),
                    tmux_session=slot.get("tmux_session", ""),
                    cwd=slot.get("cwd", "."),
                    windows=windows,
                )
            )
        return cls(
            project=data.get("project", ""),
            root=data.get("root", "."),
            openers={
                k: OpenerSpec.from_dict(v)
                for k, v in dict(data.get("openers", {})).items()
                if isinstance(v, dict)
            },
            default_opener=data.get("default_opener"),
            slots=slots,
            state_updates=dict(data.get("state_updates", {})),
        )

