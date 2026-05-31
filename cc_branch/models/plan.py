from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .common import _as_public_dict
from .config import RemoteConfig
from .openers import OpenerSpec


@dataclass
class WindowPlan:
    """Resolved, executable plan for a single window."""

    name: str
    key: str
    enabled: bool
    agent: str | None
    runtime: str
    opener: str | None
    cwd: str
    env: dict[str, Any]
    remote: RemoteConfig | None
    resolved_session_id: str | None
    resolved_label: str | None
    launch_command: str
    command_binary: str
    post_launch_commands: list[str]
    bootstrapped: bool
    session_mode: str
    resume_mode: str
    create_mode: str
    agent_declared: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "key": self.key,
            "enabled": self.enabled,
            "agent": self.agent,
            "runtime": self.runtime,
            "opener": self.opener,
            "cwd": self.cwd,
            "env": self.env,
            "remote": self.remote.to_dict() if self.remote else None,
            "resolved_session_id": self.resolved_session_id,
            "resolved_label": self.resolved_label,
            "launch_command": self.launch_command,
            "command_binary": self.command_binary,
            "post_launch_commands": self.post_launch_commands,
            "bootstrapped": self.bootstrapped,
            "session_mode": self.session_mode,
            "resume_mode": self.resume_mode,
            "create_mode": self.create_mode,
            "agent_declared": self.agent_declared,
        }


@dataclass
class SlotPlan:
    """Resolved plan for a slot."""

    name: str
    runtime: str
    layout: str
    opener: str | None
    split_group: str | None
    tmux_session: str
    cwd: str
    windows: list[WindowPlan] = field(default_factory=list)

    def launchable_windows(self) -> list[WindowPlan]:
        """Return windows that should be opened by workspace launch/restart."""
        return [window for window in self.windows if window.enabled]

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "runtime": self.runtime,
            "layout": self.layout,
            "opener": self.opener,
            "tmux_session": self.tmux_session,
            "cwd": self.cwd,
            "windows": [w.to_dict() for w in self.windows],
        }
        if self.split_group:
            payload["split_group"] = self.split_group
        return payload


@dataclass
class WorkspacePlan:
    """Fully resolved workspace plan."""

    project: str
    root: str
    openers: dict[str, OpenerSpec] = field(default_factory=dict)
    open_with: str | None = None
    slots: list[SlotPlan] = field(default_factory=list)
    state_updates: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "root": self.root,
            "openers": {k: _as_public_dict(v) for k, v in self.openers.items()},
            "open_with": self.open_with,
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
        """Best-effort conversion from a serialized plan dict."""
        slots: list[SlotPlan] = []
        for slot in data.get("slots", []):
            windows: list[WindowPlan] = []
            for w in slot.get("windows", []):
                windows.append(
                    WindowPlan(
                        name=w.get("name", ""),
                        key=w.get("key", ""),
                        enabled=w.get("enabled") is not False,
                        agent=w.get("agent"),
                        runtime=w.get("runtime", "tmux"),
                        opener=w.get("opener"),
                        cwd=w.get("cwd", "."),
                        env=w.get("env", {}),
                        remote=RemoteConfig.from_dict(w.get("remote")),
                        resolved_session_id=w.get("resolved_session_id"),
                        resolved_label=w.get("resolved_label"),
                        launch_command=w.get("launch_command", ""),
                        command_binary=w.get("command_binary", ""),
                        post_launch_commands=w.get("post_launch_commands", []),
                        bootstrapped=w.get("bootstrapped", False),
                        session_mode=w.get("session_mode", "auto"),
                        resume_mode=w.get("resume_mode", "none"),
                        create_mode=w.get("create_mode", "none"),
                        agent_declared=w.get("agent_declared", True),
                    )
                )
            slots.append(
                SlotPlan(
                    name=slot.get("name", ""),
                    runtime=slot.get("runtime", "tmux"),
                    layout=slot.get("layout", "auto"),
                    opener=slot.get("opener"),
                    split_group=slot.get("split_group"),
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
            open_with=data.get("open_with"),
            slots=slots,
            state_updates=dict(data.get("state_updates", {})),
        )
