"""Canonical data models for cc-branch workspace configuration and plans.

This module provides typed dataclasses that replace the previous bare
``dict[str, Any]`` approach. All internal logic should operate on these
models; dict compatibility is handled at module boundaries.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Config models (what the user declares in .cc-branch.yaml)
# ---------------------------------------------------------------------------

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
class AgentSpec:
    """Reusable agent definition."""

    command: str = ""
    resume_mode: str = "none"
    resume_template: str = ""
    create_mode: str = "none"
    create_template: str = ""
    label_template: str = ""
    label_mode: str = "metadata"
    rename_template: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentSpec:
        return cls(
            command=data.get("command", ""),
            resume_mode=data.get("resume_mode", "none"),
            resume_template=data.get("resume_template", ""),
            create_mode=data.get("create_mode", "none"),
            create_template=data.get("create_template", ""),
            label_template=data.get("label_template", ""),
            label_mode=data.get("label_mode", "metadata"),
            rename_template=data.get("rename_template", ""),
        )


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
    """Slot definition (maps to a tmux session at runtime)."""

    name: str = ""
    backend: str = "tmux"
    cwd: str = "."
    env: dict[str, Any] = field(default_factory=dict)
    windows: list[WindowConfig] = field(default_factory=list)
    # Shell-slot shorthand fields
    command: str | None = None
    window_name: str | None = None
    agent: str | None = None
    session_id: str | None = None
    label: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SlotConfig:
        raw_windows = data.get("windows", [])
        windows = [WindowConfig.from_dict(w) for w in raw_windows] if raw_windows else []
        return cls(
            name=data.get("name", ""),
            backend=data.get("backend", "tmux"),
            cwd=data.get("cwd", "."),
            env=dict(data.get("env") or {}),
            windows=windows,
            command=data.get("command"),
            window_name=data.get("window_name"),
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
    slots: list[SlotConfig] = field(default_factory=list)
    _config_path: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceConfig:
        raw_agents = data.get("agents", {})
        agents = {k: AgentSpec.from_dict(v) for k, v in raw_agents.items()} if raw_agents else {}
        raw_slots = data.get("slots", [])
        slots = [SlotConfig.from_dict(s) for s in raw_slots] if raw_slots else []
        return cls(
            version=data.get("version", 1),
            project=data.get("project", ""),
            root=data.get("root", "."),
            display=DisplayConfig.from_dict(data.get("display") or {}),
            agents=agents,
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


# ---------------------------------------------------------------------------
# Plan models (what the planner resolves)
# ---------------------------------------------------------------------------

@dataclass
class WindowPlan:
    """Resolved, executable plan for a single window."""

    name: str
    key: str
    agent: str | None
    backend: str
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
            "backend": self.backend,
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
    backend: str
    tmux_session: str
    cwd: str
    windows: list[WindowPlan] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "backend": self.backend,
            "tmux_session": self.tmux_session,
            "cwd": self.cwd,
            "windows": [w.to_dict() for w in self.windows],
        }


@dataclass
class WorkspacePlan:
    """Fully resolved workspace plan."""

    project: str
    root: str
    slots: list[SlotPlan] = field(default_factory=list)
    state_updates: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "root": self.root,
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
                        backend=w.get("backend", "tmux"),
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
                    backend=slot.get("backend", "tmux"),
                    tmux_session=slot.get("tmux_session", ""),
                    cwd=slot.get("cwd", "."),
                    windows=windows,
                )
            )
        return cls(
            project=data.get("project", ""),
            root=data.get("root", "."),
            slots=slots,
            state_updates=dict(data.get("state_updates", {})),
        )


# ---------------------------------------------------------------------------
# State models (runtime metadata persisted to .cc-branch.state.toml)
# ---------------------------------------------------------------------------

@dataclass
class WindowState:
    """Per-window persisted metadata."""

    session_id: str | None = None
    label: str | None = None
    agent: str | None = None
    slot: str | None = None
    window: str | None = None

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
        return result


@dataclass
class WorkspaceState:
    """Top-level runtime state."""

    version: int = 1
    windows: dict[str, WindowState] = field(default_factory=dict)

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
                )
        return cls(version=int(data.get("version", 1)), windows=windows)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "windows": {k: v.to_dict() for k, v in self.windows.items()},
        }

    def get_window(self, key: str) -> WindowState | None:
        """Return the window state for *key* or None."""
        return self.windows.get(key)

    def set_window(self, key: str, entry: WindowState) -> None:
        """Persist *entry* under *key*."""
        self.windows[key] = entry


# ---------------------------------------------------------------------------
# Doctor models (structured diagnostics)
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    """A single diagnosed issue."""

    issue_type: str
    severity: str  # "error" | "warning" | "info"
    message: str
    target: str = ""  # e.g. "dev.planner" or "tmux"
    context: dict[str, Any] = field(default_factory=dict)
    fixable: bool = False


@dataclass
class DoctorReport:
    """Structured result of a workspace health check."""

    project: str
    issues: list[Issue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == "warning" for i in self.issues)

    @property
    def fixable_issues(self) -> list[Issue]:
        return [i for i in self.issues if i.fixable]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _as_legacy_dict(obj: Any) -> Any:
    """Recursively convert dataclasses to plain dicts for legacy compatibility."""
    if is_dataclass(obj) and not isinstance(obj, type):
        result: dict[str, Any] = {}
        for k, v in asdict(obj).items():
            if k.startswith("_"):
                continue
            if v in (None, "", [], {}):
                # Preserve behaviour of old load_workspace: keep explicit overrides
                # but omit empty defaults
                if k in ("env", "windows", "agents") and not v:
                    result[k] = v if k == "env" else v
                continue
            result[k] = _as_legacy_dict(v)
        return result
    if isinstance(obj, list):
        return [_as_legacy_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _as_legacy_dict(v) for k, v in obj.items()}
    return obj
