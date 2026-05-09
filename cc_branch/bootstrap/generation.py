"""Starter configuration generation for workspace bootstrap."""

from __future__ import annotations

from .models import ConfigSummary


def generate_starter_config(
    project_name: str,
    available_agents: list[str],
    profile: str = "solo-dev",
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
    slots = list(config_data.get("slots", []))
    referenced_agents = {
        agent
        for slot in slots
        for agent in [
            slot.get("agent"),
            *(window.get("agent") for window in slot.get("windows", []) if isinstance(window, dict)),
        ]
        if agent
    }
    return ConfigSummary(
        slots=len(slots),
        windows=sum(
            len(slot.get("windows", []))
            for slot in slots
            if slot.get("runtime", "tmux") == "tmux"
        ),
        agents=len(referenced_agents),
    )
