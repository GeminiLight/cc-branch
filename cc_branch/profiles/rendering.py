"""Render workspace profile templates to config YAML."""

from __future__ import annotations

from typing import Any

from ..runtime.shells import default_shell_command
from .definitions import PROFILES


def get_profile_config(
    project_name: str,
    available_agents: list[str],
    profile: str = "development",
    *,
    tmux_available: bool = True,
) -> str:
    """Generate YAML config from a profile template."""
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}. Available: {', '.join(PROFILES.keys())}")

    template = PROFILES[profile]
    tabs_yaml = build_tabs_section(
        template["tabs"],
        set(available_agents),
        tmux_available=tmux_available,
    )

    return f"""version: 2
project: "{project_name}"
root: "."
openWith: "auto-terminal"

display:
  mode: "grid"
  columns: 2
  dashboard: true

{tabs_yaml}"""


def build_tabs_section(
    tabs_template: list[dict[str, Any]],
    available_agents: set[str],
    *,
    tmux_available: bool = True,
) -> str:
    """Build the tabs section of YAML config."""
    lines = ["tabs:"]
    shell_command = default_shell_command()
    emitted_names: set[str] = set()

    for tab in tabs_template:
        tab_name = tab["name"]
        layout_backend = tab.get("layoutBackend") or tab.get("runtime", "tmux")

        if layout_backend in {"direct", "terminal"} or not tmux_available:
            if layout_backend in {"direct", "terminal"}:
                selected_agent = None
                terminal_name = _unique_tab_name(tab_name, emitted_names)
            else:
                panes = tab.get("panes") or tab.get("windows", [])
                if panes:
                    for pane in panes:
                        pane_name = pane["name"]
                        selected_agent = _first_available(
                            pane.get("preferred_agents", []),
                            available_agents,
                        )
                        terminal_name = _unique_tab_name(pane_name, emitted_names)
                        lines.extend(_terminal_tab_lines(terminal_name, shell_command=shell_command, agent=selected_agent))
                    continue
                selected_agent = None
                terminal_name = _unique_tab_name(tab_name, emitted_names)

            lines.extend(
                _terminal_tab_lines(
                    terminal_name,
                    shell_command=shell_command,
                    agent=selected_agent,
                )
            )
            continue

        emitted_names.add(tab_name)
        lines.append(f'  - name: "{tab_name}"')
        lines.append('    layoutBackend: "tmux"')
        lines.append('    cwd: "."')
        lines.append("    panes:")

        panes = tab.get("panes") or tab.get("windows", [])
        for pane in panes:
            pane_name = pane["name"]
            selected_agent = _first_available(pane.get("preferred_agents", []), available_agents)
            lines.append(f'      - name: "{pane_name}"')
            if selected_agent:
                lines.append(f'        agent: "{selected_agent}"')
            else:
                lines.append(f'        command: "{shell_command}"')

        if not panes:
            lines.append('      - name: "shell"')
            lines.append(f'        command: "{shell_command}"')

    return "\n".join(lines)


def build_slots_section(
    slots_template: list[dict[str, Any]],
    available_agents: set[str],
    *,
    tmux_available: bool = True,
) -> str:
    """Compatibility alias for older internal callers."""
    return build_tabs_section(slots_template, available_agents, tmux_available=tmux_available)


def _terminal_tab_lines(
    tab_name: str,
    *,
    shell_command: str,
    agent: str | None,
) -> list[str]:
    lines = [
        f'  - name: "{tab_name}"',
        '    cwd: "."',
        "    panes:",
        f'      - name: "{tab_name}"',
    ]
    if agent:
        lines.append(f'        agent: "{agent}"')
    else:
        lines.append(f'        command: "{shell_command}"')
    return lines


def _unique_tab_name(name: str, used: set[str]) -> str:
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
