"""Render workspace profile templates to config YAML."""

from __future__ import annotations

from typing import Any

from ..runtime.shells import default_shell_command
from .definitions import PROFILES


def get_profile_config(
    project_name: str,
    available_agents: list[str],
    profile: str = "solo-dev",
    *,
    tmux_available: bool = True,
) -> str:
    """Generate YAML config from a profile template."""
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}. Available: {', '.join(PROFILES.keys())}")

    template = PROFILES[profile]
    slots_yaml = build_slots_section(
        template["slots"],
        set(available_agents),
        tmux_available=tmux_available,
    )

    return f"""version: 1
project: "{project_name}"
root: "."

display:
  mode: "grid"
  columns: 2
  dashboard: true

{slots_yaml}"""


def build_slots_section(
    slots_template: list[dict[str, Any]],
    available_agents: set[str],
    *,
    tmux_available: bool = True,
) -> str:
    """Build the slots section of YAML config."""
    lines = ["slots:"]
    shell_command = default_shell_command()
    emitted_names: set[str] = set()

    for slot in slots_template:
        slot_name = slot["name"]
        runtime = slot.get("runtime", "tmux")

        if runtime == "terminal" or not tmux_available:
            if runtime == "terminal":
                selected_agent = None
                terminal_name = _unique_slot_name(slot_name, emitted_names)
                title = slot.get("title", slot_name)
            else:
                windows = slot.get("windows", [])
                if windows:
                    for window in windows:
                        window_name = window["name"]
                        selected_agent = _first_available(
                            window.get("preferred_agents", []),
                            available_agents,
                        )
                        terminal_name = _unique_slot_name(window_name, emitted_names)
                        lines.extend(
                            _terminal_slot_lines(
                                terminal_name,
                                title=window_name,
                                shell_command=shell_command,
                                agent=selected_agent,
                            )
                        )
                    continue
                selected_agent = None
                terminal_name = _unique_slot_name(slot_name, emitted_names)
                title = slot_name

            lines.extend(
                _terminal_slot_lines(
                    terminal_name,
                    title=title,
                    shell_command=shell_command,
                    agent=selected_agent,
                )
            )
            continue

        emitted_names.add(slot_name)
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


def _terminal_slot_lines(
    slot_name: str,
    *,
    title: str,
    shell_command: str,
    agent: str | None,
) -> list[str]:
    lines = [
        f'  - name: "{slot_name}"',
        '    runtime: "terminal"',
        '    cwd: "."',
        f'    title: "{title}"',
    ]
    if agent:
        lines.append(f'    agent: "{agent}"')
    else:
        lines.append(f'    command: "{shell_command}"')
    return lines


def _unique_slot_name(name: str, used: set[str]) -> str:
    candidate = name
    index = 2
    while candidate in used:
        candidate = f"{name}-{index}"
        index += 1
    used.add(candidate)
    return candidate


def _first_available(preferred_agents: list[str], available_agents: set[str]) -> str | None:
    for agent in preferred_agents:
        if agent in available_agents:
            return agent
    return None
