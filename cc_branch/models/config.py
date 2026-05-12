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
    layout: str = "auto"
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
            layout=data.get("layout", "auto"),
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


def _pane_runtime(data: dict[str, Any]) -> str:
    runtime = str(data.get("runtime") or "terminal")
    return runtime if runtime in {"terminal", "tmux"} else "terminal"


def _pane_to_window(data: dict[str, Any]) -> WindowConfig:
    return WindowConfig.from_dict(data)


def _tabs_to_slots(raw_tabs: list[Any]) -> list[SlotConfig]:
    slots: list[SlotConfig] = []
    for raw_tab in raw_tabs:
        if not isinstance(raw_tab, dict):
            continue

        tab_name = str(raw_tab.get("name") or "")
        tab_layout = str(raw_tab.get("layout") or "auto")
        tab_opener = raw_tab.get("opener")
        tab_cwd = str(raw_tab.get("cwd") or ".")
        tab_env = dict(raw_tab.get("env") or {})
        panes = raw_tab.get("panes") or []
        raw_panes = [pane for pane in panes if isinstance(pane, dict)] if isinstance(panes, list) else []

        terminal_panes = [pane for pane in raw_panes if _pane_runtime(pane) == "terminal"]
        if terminal_panes or not raw_panes:
            slots.append(
                SlotConfig(
                    name=tab_name,
                    runtime="terminal",
                    layout=tab_layout,
                    opener=tab_opener if isinstance(tab_opener, str) else None,
                    cwd=tab_cwd,
                    env=tab_env,
                    windows=[_pane_to_window(pane) for pane in terminal_panes],
                )
            )

        tmux_panes = [pane for pane in raw_panes if _pane_runtime(pane) == "tmux"]
        for pane in tmux_panes:
            pane_name = str(pane.get("name") or "tmux")
            raw_windows = pane.get("windows") or []
            windows = (
                [WindowConfig.from_dict(window) for window in raw_windows if isinstance(window, dict)]
                if isinstance(raw_windows, list)
                else []
            )
            if not windows:
                windows = [WindowConfig.from_dict({**pane, "runtime": None})]
            slots.append(
                SlotConfig(
                    name=tab_name if len(tmux_panes) == 1 and not terminal_panes else f"{tab_name}-{pane_name}",
                    runtime="tmux",
                    layout=str(pane.get("layout") or tab_layout),
                    opener=str(pane.get("opener") or tab_opener) if pane.get("opener") or tab_opener else None,
                    cwd=str(pane.get("cwd") or tab_cwd),
                    env={**tab_env, **dict(pane.get("env") or {})},
                    windows=windows,
                )
            )
    return slots


def _slot_to_tab(slot: SlotConfig) -> dict[str, Any]:
    tab: dict[str, Any] = {
        "name": slot.name,
        "layout": slot.layout,
        "cwd": slot.cwd,
    }
    if slot.opener is not None:
        tab["opener"] = slot.opener
    if slot.env:
        tab["env"] = slot.env
    if slot.runtime == "tmux":
        tab["panes"] = [
            {
                "name": slot.name,
                "runtime": "tmux",
                "windows": [_as_legacy_dict(window) for window in slot.windows],
            }
        ]
    else:
        tab["panes"] = [_as_legacy_dict(window) for window in slot.windows]
    return tab


@dataclass
class WorkspaceConfig:
    """Top-level workspace configuration."""

    version: int = 2
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
        raw_tabs = data.get("tabs")
        if isinstance(raw_tabs, list):
            slots = _tabs_to_slots(raw_tabs)
        else:
            raw_slots = data.get("slots", [])
            slots = [SlotConfig.from_dict(s) for s in raw_slots] if raw_slots else []
        return cls(
            version=data.get("version", 2),
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
        """Return a dict compatible with the public v2 config schema."""
        return {
            "version": self.version,
            "project": self.project,
            "root": self.root,
            "display": self.display.to_dict(),
            "agents": {k: _as_legacy_dict(v) for k, v in self.agents.items()},
            "openers": {k: _as_legacy_dict(v) for k, v in self.openers.items()},
            "default_opener": self.default_opener,
            "tabs": [_slot_to_tab(s) for s in self.slots],
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
