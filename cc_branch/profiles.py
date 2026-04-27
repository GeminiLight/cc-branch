"""Profile templates for workspace initialization."""

from __future__ import annotations

from typing import Any

from .shells import default_shell_command

# Profile definitions with preferred agent priority lists
PROFILES = {
    "solo-dev": {
        "description": "Single developer workspace with planner, builder, review, and scratch",
        "slots": [
            {
                "name": "dev",
                "windows": [
                    {"name": "planner", "preferred_agents": ["codex", "claude", "gemini"]},
                    {"name": "builder", "preferred_agents": ["codex", "claude", "gemini"]},
                    {"name": "review", "preferred_agents": ["claude", "codex", "gemini"]},
                ],
            },
            {"name": "scratch", "backend": "shell"},
        ],
    },
    "ai-pair": {
        "description": "AI coding pair workflow with separate coder and reviewer",
        "slots": [
            {
                "name": "coder",
                "windows": [
                    {"name": "implement", "preferred_agents": ["codex", "claude", "gemini"]},
                ],
            },
            {
                "name": "reviewer",
                "windows": [
                    {"name": "review", "preferred_agents": ["claude", "codex", "gemini"]},
                ],
            },
            {"name": "scratch", "backend": "shell"},
        ],
    },
    "minimal": {
        "description": "Minimal workspace with single agent window and scratch",
        "slots": [
            {
                "name": "main",
                "windows": [
                    {"name": "agent", "preferred_agents": ["claude", "codex", "gemini"]},
                ],
            },
            {"name": "scratch", "backend": "shell"},
        ],
    },
}


def get_available_profiles() -> list[str]:
    """Return list of available profile names."""
    return list(PROFILES.keys())


def get_profile_description(profile: str) -> str:
    """Get description for a profile."""
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
    return PROFILES[profile]["description"]


def get_profile_config(
    project_name: str,
    available_agents: list[str],
    profile: str = "solo-dev",
) -> str:
    """
    Generate YAML config from profile template.

    Args:
        project_name: Name of the project
        available_agents: List of agent names that are actually available
        profile: Profile template to use

    Returns:
        YAML config string

    Note:
        - Uses first available agent from preferred_agents list for each window
        - Skips windows if no preferred agents are available
        - Always keeps at least one shell window per slot
        - If no agents available, generates shell-only config
    """
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}. Available: {', '.join(PROFILES.keys())}")

    template = PROFILES[profile]
    available_set = set(available_agents)

    # Build agent definitions section (only for available agents)
    agents_yaml = _build_agents_section(available_agents)

    # Build slots section
    slots_yaml = _build_slots_section(template["slots"], available_set)

    # Assemble full config
    config = f"""version: 1
project: "{project_name}"
root: "."

display:
  mode: "grid"
  columns: 2
  dashboard: true

{agents_yaml}

{slots_yaml}"""

    return config


def _build_agents_section(available_agents: list[str]) -> str:
    """Build the agents section of YAML config from the registry."""
    if not available_agents:
        return "agents: {}"

    from .agent_registry import load_agent_registry

    registry = load_agent_registry()
    lines = ["agents:"]
    for agent_name in available_agents:
        definition = registry.get(agent_name)
        if definition is not None:
            lines.append(definition.to_yaml_block())

    return "\n".join(lines)


def _build_slots_section(slots_template: list[dict[str, Any]], available_agents: set[str]) -> str:
    """Build the slots section of YAML config."""
    lines = ["slots:"]
    shell_command = default_shell_command()

    for slot in slots_template:
        slot_name = slot["name"]
        backend = slot.get("backend", "tmux")

        if backend == "shell":
            # Shell slot - no agent needed
            lines.append(f'  - name: "{slot_name}"')
            lines.append('    backend: "shell"')
            lines.append('    cwd: "."')
            lines.append(f'    command: "{shell_command}"')
        else:
            # Tmux slot with windows
            lines.append(f'  - name: "{slot_name}"')
            lines.append('    backend: "tmux"')
            lines.append('    cwd: "."')
            lines.append("    windows:")

            windows = slot.get("windows", [])
            added_windows = 0

            for window in windows:
                window_name = window["name"]
                preferred = window.get("preferred_agents", [])

                # Find first available agent from preferred list
                selected_agent = None
                for agent in preferred:
                    if agent in available_agents:
                        selected_agent = agent
                        break

                # Only add window if we have an agent for it
                if selected_agent:
                    lines.append(f'      - name: "{window_name}"')
                    lines.append(f'        agent: "{selected_agent}"')
                    added_windows += 1

            # If no windows were added (no agents available), add a shell window
            if added_windows == 0:
                lines.append('      - name: "shell"')
                lines.append(f'        command: "{shell_command}"')

    return "\n".join(lines)
