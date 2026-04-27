"""First-run bootstrap experience for CC Branch.

This module provides environment checking, config generation, and session
bootstrapping for new users starting with an empty directory.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .agent_registry import load_agent_registry
from .config import load_workspace
from .models import WorkspaceConfig, WorkspaceState
from .runtime import which


@dataclass
class AgentStatus:
    """Status of a single agent CLI."""

    name: str
    command: str
    status: Literal["ok", "missing", "not_authenticated"]
    path: str | None
    install_hint: str


@dataclass
class EnvironmentReport:
    """Complete environment check report."""

    tmux_available: bool
    tmux_path: str | None
    agents: list[AgentStatus]
    config_exists: bool
    state_exists: bool
    has_write_permission: bool

    @property
    def available_agents(self) -> list[str]:
        """Return list of available agent names."""
        return [a.name for a in self.agents if a.status == "ok"]

    @property
    def can_proceed(self) -> bool:
        """Check if init can proceed."""
        return self.has_write_permission

    @property
    def has_blockers(self) -> bool:
        """Check if there are blocking issues."""
        return not self.tmux_available or not self.has_write_permission


@dataclass(frozen=True)
class ConfigSummary:
    """Counts extracted from a generated config."""

    slots: int
    windows: int
    agents: int


@dataclass(frozen=True)
class WorkspaceInitResult:
    """Artifacts produced by workspace initialization."""

    config_path: Path
    state_path: Path
    config_summary: ConfigSummary
    state: WorkspaceState
    gitignore_created: bool
    gitignore_updated: bool





def check_environment(
    target_dir: Path,
    timeout: float = 2.0,
) -> EnvironmentReport:
    """
    Check tmux and agent CLI availability.

    Args:
        target_dir: Directory to check for config/state files
        timeout: Maximum time in seconds for all checks (default 2.0s)

    Returns:
        EnvironmentReport with status of all components

    Note:
        Individual checks timeout after timeout/num_checks to prevent hanging.
        If a check times out, it's marked as "missing" with a timeout note.
    """
    from .constants import DEFAULT_CONFIG, DEFAULT_STATE

    # Check tmux
    tmux_path = which("tmux")
    tmux_available = tmux_path is not None

    # Check agent CLIs
    agents: list[AgentStatus] = []

    registry = load_agent_registry(cwd=target_dir)
    for name, definition in registry.items():
        command = definition.command
        try:
            agent_path = which(command)
            if agent_path:
                status = AgentStatus(
                    name=name,
                    command=command,
                    status="ok",
                    path=agent_path,
                    install_hint=definition.install_hint,
                )
            else:
                status = AgentStatus(
                    name=name,
                    command=command,
                    status="missing",
                    path=None,
                    install_hint=definition.install_hint,
                )
        except Exception:
            status = AgentStatus(
                name=name,
                command=command,
                status="missing",
                path=None,
                install_hint=definition.install_hint,
            )
        agents.append(status)

    # Check config and state files
    config_path = target_dir / DEFAULT_CONFIG
    state_path = target_dir / DEFAULT_STATE
    config_exists = config_path.exists()
    state_exists = state_path.exists()

    # Check write permission
    has_write_permission = os.access(target_dir, os.W_OK)

    return EnvironmentReport(
        tmux_available=tmux_available,
        tmux_path=tmux_path,
        agents=agents,
        config_exists=config_exists,
        state_exists=state_exists,
        has_write_permission=has_write_permission,
    )


def generate_starter_config(
    project_name: str,
    available_agents: list[str],
    profile: str = "solo-dev",
) -> str:
    """
    Generate YAML config based on available agents.

    Args:
        project_name: Name of the project (used in config)
        available_agents: List of agent names that are actually available
        profile: Profile template to use

    Returns:
        YAML config string

    Note:
        If available_agents is empty, generates shell-only config.
        Only includes agent definitions for available agents.
        Windows for unavailable agents are omitted from the config.
    """
    from .profiles import get_profile_config

    return get_profile_config(project_name, available_agents, profile)


def bootstrap_sessions(
    workspace: WorkspaceConfig,
    state: WorkspaceState,
) -> WorkspaceState:
    """Generate UUIDs for agents with create_mode=generated_uuid.

    Returns an updated state with generated session IDs.
    """
    from .planner import plan_workspace
    from .state import merge_state

    plan = plan_workspace(workspace, state, bootstrap_missing=True)
    return merge_state(state, plan.state_updates)


def summarize_config(config_content: str) -> ConfigSummary:
    """Summarize generated config content for UI output."""
    import yaml

    config_data = yaml.safe_load(config_content) or {}
    slots = list(config_data.get("slots", []))
    return ConfigSummary(
        slots=len(slots),
        windows=sum(
            len(slot.get("windows", []))
            for slot in slots
            if slot.get("backend", "tmux") == "tmux"
        ),
        agents=len(config_data.get("agents", {})),
    )


def ensure_state_gitignored(target_dir: Path, state_filename: str) -> tuple[bool, bool]:
    """Ensure the local state file is ignored without clobbering existing edits."""
    gitignore_path = target_dir / ".gitignore"
    block = f"# CC Branch state (machine-specific)\n{state_filename}\n"

    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        if state_filename in content:
            return False, False
        with gitignore_path.open("a", encoding="utf-8") as handle:
            prefix = "" if content.endswith("\n") or not content else "\n"
            handle.write(f"{prefix}{block}")
        return False, True

    gitignore_path.write_text(block, encoding="utf-8")
    return True, False


def initialize_workspace_files(
    target_dir: Path,
    *,
    profile: str,
    available_agents: list[str],
    bootstrap_sessions_requested: bool,
) -> WorkspaceInitResult:
    """Create config, state, and gitignore entries for a new workspace."""
    from .constants import DEFAULT_CONFIG, DEFAULT_STATE
    from .state import save_state

    config_content = generate_starter_config(target_dir.name, available_agents, profile)
    config_path = target_dir / DEFAULT_CONFIG
    config_path.write_text(config_content, encoding="utf-8")

    summary = summarize_config(config_content)
    workspace = load_workspace(config_path)
    state = WorkspaceState()

    if bootstrap_sessions_requested or available_agents:
        state = bootstrap_sessions(workspace, state)

    state_path = target_dir / DEFAULT_STATE
    save_state(state_path, state)
    gitignore_created, gitignore_updated = ensure_state_gitignored(target_dir, DEFAULT_STATE)

    return WorkspaceInitResult(
        config_path=config_path,
        state_path=state_path,
        config_summary=summary,
        state=state,
        gitignore_created=gitignore_created,
        gitignore_updated=gitignore_updated,
    )
