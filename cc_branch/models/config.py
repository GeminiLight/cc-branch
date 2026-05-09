from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .agents import AgentSpec
from .common import _as_legacy_dict
from .openers import OpenerSpec


@dataclass
class DisplayConfig:
    """Display / dashboard settings."""

    mode: str = "grid"
    columns: int = 2
    dashboard: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DisplayConfig:
        return cls(
            mode=data.get("mode", "grid"),
            columns=data.get("columns", 2),
            dashboard=data.get("dashboard", False),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"mode": self.mode, "columns": self.columns, "dashboard": self.dashboard}


@dataclass
class WindowConfig:
    """Window definition inside a slot."""

    name: str = ""
    agent: str | None = None
    command: str | None = None
    cwd: str | None = None
    env: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None
    label: str | None = None
    # Window-level overrides for agent behaviour
    label_template: str | None = None
    resume_mode: str | None = None
    resume_template: str | None = None
    create_mode: str | None = None
    create_template: str | None = None
    label_mode: str | None = None
    rename_template: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WindowConfig:
        return cls(
            name=data.get("name", ""),
            agent=data.get("agent"),
            command=data.get("command"),
            cwd=data.get("cwd"),
            env=dict(data.get("env") or {}),
            session_id=data.get("session_id"),
            label=data.get("label"),
            label_template=data.get("label_template"),
            resume_mode=data.get("resume_mode"),
            resume_template=data.get("resume_template"),
            create_mode=data.get("create_mode"),
            create_template=data.get("create_template"),
            label_mode=data.get("label_mode"),
            rename_template=data.get("rename_template"),
        )


@dataclass
class SlotConfig:
    """Slot definition."""

    name: str = ""
    runtime: str = "tmux"
    opener: str | None = None
    cwd: str = "."
    env: dict[str, Any] = field(default_factory=dict)
    windows: list[WindowConfig] = field(default_factory=list)
    # Single-window runtime fields.
    command: str | None = None
    title: str | None = None
    agent: str | None = None
    session_id: str | None = None
    label: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SlotConfig:
        raw_windows = data.get("windows", [])
        windows = [WindowConfig.from_dict(w) for w in raw_windows] if raw_windows else []
        return cls(
            name=data.get("name", ""),
            runtime=data.get("runtime", "tmux"),
            opener=data.get("opener"),
            cwd=data.get("cwd", "."),
            env=dict(data.get("env") or {}),
            windows=windows,
            command=data.get("command"),
            title=data.get("title"),
            agent=data.get("agent"),
            session_id=data.get("session_id"),
            label=data.get("label"),
        )


@dataclass
class WorkspaceConfig:
    """Top-level workspace configuration."""

    version: int = 1
    project: str = ""
    root: str = "."
    display: DisplayConfig = field(default_factory=DisplayConfig)
    agents: dict[str, AgentSpec] = field(default_factory=dict)
    openers: dict[str, OpenerSpec] = field(default_factory=dict)
    default_opener: str | None = None
    slots: list[SlotConfig] = field(default_factory=list)
    _config_path: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceConfig:
        raw_agents = data.get("agents", {})
        agents = {k: AgentSpec.from_dict(v) for k, v in raw_agents.items()} if raw_agents else {}
        raw_openers = data.get("openers", {})
        default_opener = data.get("default_opener")
        if isinstance(raw_openers, dict) and (
            "items" in raw_openers or "default" in raw_openers
        ):
            default_opener = raw_openers.get("default", default_opener)
            raw_openers = raw_openers.get("items", {})
        openers = {
            k: OpenerSpec.from_dict(v)
            for k, v in raw_openers.items()
            if isinstance(v, dict)
        } if raw_openers else {}
        raw_slots = data.get("slots", [])
        slots = [SlotConfig.from_dict(s) for s in raw_slots] if raw_slots else []
        return cls(
            version=data.get("version", 1),
            project=data.get("project", ""),
            root=data.get("root", "."),
            display=DisplayConfig.from_dict(data.get("display") or {}),
            agents=agents,
            openers=openers,
            default_opener=default_opener,
            slots=slots,
            _config_path=data.get("_config_path", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a dict compatible with the legacy API."""
        return {
            "version": self.version,
            "project": self.project,
            "root": self.root,
            "display": self.display.to_dict(),
            "agents": {k: _as_legacy_dict(v) for k, v in self.agents.items()},
            "openers": {k: _as_legacy_dict(v) for k, v in self.openers.items()},
            "default_opener": self.default_opener,
            "slots": [_as_legacy_dict(s) for s in self.slots],
            "_config_path": self._config_path,
        }

    def get_agent(self, name: str | None) -> AgentSpec | None:
        """Return the agent spec for *name* or None."""
        if name is None:
            return None
        return self.agents.get(name)

    def get_slot(self, name: str) -> SlotConfig | None:
        """Return the slot config for *name* or None."""
        for slot in self.slots:
            if slot.name == name:
                return slot
        return None

