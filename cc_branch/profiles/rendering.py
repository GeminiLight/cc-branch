"""Render workspace profile templates to config YAML."""

from __future__ import annotations

from typing import Any

from ..runtime.shells import default_shell_command
from .definitions import PROFILES


def get_profile_config(
    project_name: str,
    available_agents: list[str],
    profile: str = "solo-dev",
) -> str:
    """Generate YAML config from a profile template."""
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}. Available: {', '.join(PROFILES.keys())}")

    template = PROFILES[profile]
    slots_yaml = build_slots_section(template["slots"], set(available_agents))

    return f"""version: 1
project: "{project_name}"
root: "."

display:
  mode: "grid"
  columns: 2
  dashboard: true

{slots_yaml}"""


def build_slots_section(slots_template: list[dict[str, Any]], available_agents: set[str]) -> str:
    """Build the slots section of YAML config."""
    lines = ["slots:"]
    shell_command = default_shell_command()

    for slot in slots_template:
        slot_name = slot["name"]
        runtime = slot.get("runtime", "tmux")

        if runtime == "terminal":
            lines.append(f'  - name: "{slot_name}"')
            lines.append('    runtime: "terminal"')
            lines.append('    cwd: "."')
            lines.append('    title: "scratch"')
            lines.append(f'    command: "{shell_command}"')
            continue

        lines.append(f'  - name: "{slot_name}"')
        lines.append('    runtime: "tmux"')
        lines.append('    cwd: "."')
        lines.append("    windows:")

        added_windows = 0
        for window in slot.get("windows", []):
            window_name = window["name"]
            selected_agent = _first_available(window.get("preferred_agents", []), available_agents)
            if selected_agent:
                lines.append(f'      - name: "{window_name}"')
                lines.append(f'        agent: "{selected_agent}"')
                added_windows += 1

        if added_windows == 0:
            lines.append('      - name: "shell"')
            lines.append(f'        command: "{shell_command}"')

    return "\n".join(lines)


def _first_available(preferred_agents: list[str], available_agents: set[str]) -> str | None:
    for agent in preferred_agents:
        if agent in available_agents:
            return agent
    return None
