"""Workspace profile facade."""

from __future__ import annotations

from ..runtime.shells import default_shell_command
from . import rendering as _rendering
from .definitions import PROFILES
from .queries import get_available_profiles, get_profile_description
from .rendering import build_slots_section, build_tabs_section


def get_profile_config(
    project_name: str,
    available_agents: list[str],
    profile: str = "development",
    *,
    tmux_available: bool = True,
) -> str:
    """Generate YAML config from a profile template."""
    _rendering.default_shell_command = default_shell_command
    return _rendering.get_profile_config(
        project_name,
        available_agents,
        profile,
        tmux_available=tmux_available,
    )


_build_slots_section = build_slots_section
_build_tabs_section = build_tabs_section

__all__ = [
    "PROFILES",
    "build_slots_section",
    "build_tabs_section",
    "default_shell_command",
    "get_available_profiles",
    "get_profile_config",
    "get_profile_description",
]
