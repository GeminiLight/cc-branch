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
class WorkspaceDefaults:
    """Workspace-level defaults inherited by panes unless overridden."""

    shell: Any | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceDefaults:
        return cls(shell=data.get("shell"))

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.shell is not None:
            out["shell"] = self.shell
        return out


@dataclass
class WindowConfig:
    """Internal pane definition inside a tab-backed slot."""

    name: str = ""
    agent: str | None = None
    command: str | None = None
    cwd: str | None = None
    env: dict[str, Any] = field(default_factory=dict)
    session: str | None = None
    session_id: str | None = None
    shell: Any | None = None
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
            session=data.get("session") or data.get("session_id"),
            session_id=data.get("session_id"),
            shell=data.get("shell"),
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
    """Internal tab definition.

    The public config schema calls this a tab. The internal name remains SlotConfig
    while runtime/state/planner code is being migrated.
    """

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
    session: str | None = None
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
            session=data.get("session") or data.get("session_id"),
            session_id=data.get("session_id"),
            label=data.get("label"),
        )


def _pane_runtime(data: dict[str, Any]) -> str:
    runtime = str(data.get("runtime") or "terminal")
    return runtime if runtime in {"terminal", "tmux"} else "terminal"


def _layout_backend(value: Any, default: str = "direct") -> str:
    raw = str(value or "").strip()
    if raw in {"tmux", "direct"}:
        return raw
    if raw == "terminal":
        return "direct"
    return default


def _runtime_for_layout_backend(layout_backend: str) -> str:
    return "tmux" if layout_backend == "tmux" else "terminal"


def _pane_layout_backend(data: dict[str, Any], default: str) -> str:
    if "layoutBackend" in data:
        return _layout_backend(data.get("layoutBackend"), default)
    if "runtime" in data:
        return _layout_backend(data.get("runtime"), default)
    return default


def _pane_to_window(data: dict[str, Any]) -> WindowConfig:
    return WindowConfig.from_dict(data)


def _tabs_to_slots(raw_tabs: list[Any], default_layout_backend: str) -> list[SlotConfig]:
    slots: list[SlotConfig] = []
    for raw_tab in raw_tabs:
        if not isinstance(raw_tab, dict):
            continue

        tab_name = str(raw_tab.get("name") or "")
        tab_layout = str(raw_tab.get("layout") or "auto")
        tab_opener = raw_tab.get("opener")
        tab_cwd = str(raw_tab.get("cwd") or ".")
        tab_env = dict(raw_tab.get("env") or {})
        tab_layout_backend = _layout_backend(raw_tab.get("layoutBackend"), default_layout_backend)
        panes = raw_tab.get("panes") or []
        raw_panes = [pane for pane in panes if isinstance(pane, dict)] if isinstance(panes, list) else []

        direct_panes = [
            pane for pane in raw_panes
            if _pane_layout_backend(pane, tab_layout_backend) == "direct"
        ]
        tmux_panes = [
            pane for pane in raw_panes
            if _pane_layout_backend(pane, tab_layout_backend) == "tmux"
        ]

        if direct_panes or (not raw_panes and tab_layout_backend == "direct"):
            slots.append(
                SlotConfig(
                    name=tab_name,
                    runtime="terminal",
                    layout=tab_layout,
                    opener=tab_opener if isinstance(tab_opener, str) else None,
                    cwd=tab_cwd,
                    env=tab_env,
                    session=str(direct_panes[0].get("session")) if len(direct_panes) == 1 and direct_panes[0].get("session") is not None else None,
                    windows=[_pane_to_window(pane) for pane in direct_panes],
                )
            )

        if tmux_panes or (not raw_panes and tab_layout_backend == "tmux"):
            windows: list[WindowConfig] = []
            for pane in tmux_panes:
                raw_windows = pane.get("windows") or []
                if isinstance(raw_windows, list) and raw_windows:
                    windows.extend(
                        WindowConfig.from_dict(window)
                        for window in raw_windows
                        if isinstance(window, dict)
                    )
                else:
                    windows.append(WindowConfig.from_dict(pane))
            pane_name = str(tmux_panes[0].get("name") or "tmux") if tmux_panes else "tmux"
            slot_name = (
                tab_name
                if not direct_panes and tab_layout_backend == "tmux"
                else tab_name if len(tmux_panes) <= 1 and not direct_panes
                else f"{tab_name}-{pane_name}"
            )
            slots.append(
                SlotConfig(
                    name=slot_name,
                    runtime="tmux",
                    layout=str(tmux_panes[0].get("layout") or tab_layout) if tmux_panes else tab_layout,
                    opener=str(tmux_panes[0].get("opener") or tab_opener) if tmux_panes and (tmux_panes[0].get("opener") or tab_opener) else (tab_opener if isinstance(tab_opener, str) else None),
                    cwd=str(tmux_panes[0].get("cwd") or tab_cwd) if tmux_panes else tab_cwd,
                    env={**tab_env, **dict(tmux_panes[0].get("env") or {})} if tmux_panes else tab_env,
                    session=str(tmux_panes[0].get("session")) if tmux_panes and tmux_panes[0].get("session") is not None else None,
                    windows=windows,
                )
            )
    return slots


def _slot_to_tab(slot: SlotConfig, default_layout_backend: str) -> dict[str, Any]:
    tab: dict[str, Any] = {
        "name": slot.name,
        "layout": slot.layout,
        "cwd": slot.cwd,
    }
    if slot.opener is not None:
        tab["opener"] = slot.opener
    if slot.env:
        tab["env"] = slot.env
    slot_layout_backend = "tmux" if slot.runtime == "tmux" else "direct"
    if slot_layout_backend != default_layout_backend:
        tab["layoutBackend"] = slot_layout_backend
    tab["panes"] = [_as_legacy_dict(window) for window in slot.windows]
    return tab


@dataclass
class WorkspaceConfig:
    """Top-level workspace configuration."""

    version: int = 2
    project: str = ""
    root: str = "."
    display: DisplayConfig = field(default_factory=DisplayConfig)
    defaults: WorkspaceDefaults = field(default_factory=WorkspaceDefaults)
    agents: dict[str, AgentSpec] = field(default_factory=dict)
    openers: dict[str, OpenerSpec] = field(default_factory=dict)
    default_opener: str | None = None
    layout_backend: str = "direct"
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
        default_opener = data.get("openWith", default_opener)
        layout_backend = _layout_backend(data.get("layoutBackend"), "direct")
        openers = {
            k: OpenerSpec.from_dict(v)
            for k, v in raw_openers.items()
            if isinstance(v, dict)
        } if raw_openers else {}
        raw_tabs = data.get("tabs")
        if isinstance(raw_tabs, list):
            slots = _tabs_to_slots(raw_tabs, layout_backend)
        else:
            raw_slots = data.get("slots", [])
            slots = [SlotConfig.from_dict(s) for s in raw_slots] if raw_slots else []
        return cls(
            version=data.get("version", 2),
            project=data.get("project", ""),
            root=data.get("root", "."),
            display=DisplayConfig.from_dict(data.get("display") or {}),
            defaults=WorkspaceDefaults.from_dict(data.get("defaults") or {}),
            agents=agents,
            openers=openers,
            default_opener=default_opener,
            layout_backend=layout_backend,
            slots=slots,
            _config_path=data.get("_config_path", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a dict compatible with the public v2 config schema."""
        out: dict[str, Any] = {
            "version": self.version,
            "project": self.project,
            "root": self.root,
            "display": self.display.to_dict(),
            "agents": {k: _as_legacy_dict(v) for k, v in self.agents.items()},
            "openers": {k: _as_legacy_dict(v) for k, v in self.openers.items()},
            "tabs": [_slot_to_tab(s, self.layout_backend) for s in self.slots],
            "_config_path": self._config_path,
        }
        if self.default_opener:
            out["openWith"] = self.default_opener
        if self.layout_backend != "direct":
            out["layoutBackend"] = self.layout_backend
        defaults = self.defaults.to_dict()
        if defaults:
            out["defaults"] = defaults
        return out

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
