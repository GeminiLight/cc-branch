"""Starter configuration generation for workspace bootstrap."""

from __future__ import annotations

from .models import ConfigSummary


def generate_starter_config(
    project_name: str,
    available_agents: list[str],
    profile: str = "development",
    tmux_available: bool = True,
) -> str:
    """Generate YAML config based on available agents."""
    from ..profiles import get_profile_config

    return get_profile_config(
        project_name,
        available_agents,
        profile,
        tmux_available=tmux_available,
    )


def summarize_config(config_content: str) -> ConfigSummary:
    """Summarize generated config content for UI output."""
    import yaml

    config_data = yaml.safe_load(config_content) or {}
    tabs = list(config_data.get("tabs", []))
    panes = [
        pane
        for tab in tabs
        if isinstance(tab, dict)
        for pane in tab.get("panes", [])
        if isinstance(pane, dict)
    ]
    referenced_agents = {
        agent
        for pane in panes
        for agent in [
            pane.get("agent"),
            *(window.get("agent") for window in pane.get("windows", []) if isinstance(window, dict)),
        ]
        if agent
    }
    pane_count = sum(
        max(1, len(pane.get("windows", []))) if isinstance(pane.get("windows"), list) else 1
        for pane in panes
    )
    return ConfigSummary(
        slots=len(tabs),
        windows=pane_count,
        agents=len(referenced_agents),
    )
