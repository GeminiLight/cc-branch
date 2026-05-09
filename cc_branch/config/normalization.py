"""Workspace config normalization."""

from __future__ import annotations

from pathlib import Path

from ..agent_registry import load_agent_registry


def effective_agent_profiles(raw_agents: object, cwd: Path) -> dict:
    """Return registry profiles merged with project agent overrides."""
    profiles = {
        name: definition.to_agent_spec()
        for name, definition in load_agent_registry(cwd=cwd).items()
    }
    if isinstance(raw_agents, dict):
        for name, spec in raw_agents.items():
            if not isinstance(spec, dict):
                continue
            profiles[name] = {
                **profiles.get(name, {}),
                **spec,
            }
    return profiles


def normalize_raw_config(data: dict, path: Path) -> dict:
    """Apply defaults and resolve paths on a raw config dict."""
    data.setdefault("version", 1)
    data.setdefault("project", path.parent.name)
    data.setdefault("display", {})
    raw_agents = data.get("agents", {})
    data["agents"] = effective_agent_profiles(raw_agents, path.parent)
    data.setdefault("slots", [])
    data["display"].setdefault("mode", "grid")
    data["display"].setdefault("columns", 2)
    data["display"].setdefault("dashboard", False)

    root_value = data.get("root", ".")
    root_path = (path.parent / root_value).resolve()
    data["root"] = str(root_path)
    data["_config_path"] = str(path.resolve())
    return data
