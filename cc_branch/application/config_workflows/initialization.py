"""Workspace initialization workflows."""

from __future__ import annotations

from pathlib import Path

from ..results import ActionResult


def inspect_workspace_environment(project_dir: Path) -> ActionResult:
    """Return the environment report used before initializing a workspace."""
    import cc_branch.application.config_workflows as workflows

    env = workflows.check_environment(project_dir)
    return ActionResult(
        ok=env.can_proceed,
        code="environment_ready" if env.can_proceed else "environment_blocked",
        message="Environment checked",
        exit_code=0 if env.can_proceed else 1,
        payload={"environment": env},
    )


def init_payload(result, *, agents_detected: list[str] | None = None) -> dict:
    """Return Web/CLI init payload from a bootstrap result."""
    raw_windows = getattr(getattr(result, "state", None), "windows", {})
    windows = raw_windows if isinstance(raw_windows, dict) else {}
    state_windows = [
        {"key": key, "session_id": entry.session_id}
        for key, entry in windows.items()
        if entry and entry.session_id
    ]
    return {
        "config_path": str(result.config_path),
        "state_path": str(result.state_path),
        "summary": {
            "slots": result.config_summary.slots,
            "windows": result.config_summary.windows,
            "agents": result.config_summary.agents,
        },
        "agents_detected": agents_detected or [],
        "state_windows": state_windows,
        "gitignore_created": result.gitignore_created,
        "gitignore_updated": result.gitignore_updated,
    }


def initialize_workspace_from_environment(
    project_dir: Path,
    *,
    profile: str,
    available_agents: list[str],
    bootstrap_sessions: bool,
) -> ActionResult:
    """Create workspace files using an already-inspected environment."""
    import cc_branch.application.config_workflows as workflows

    result = workflows.initialize_workspace_files(
        project_dir,
        profile=profile,
        available_agents=available_agents,
        bootstrap_sessions_requested=bootstrap_sessions,
    )
    return ActionResult(
        ok=True,
        code="workspace_initialized",
        message="Workspace initialized",
        payload=init_payload(result, agents_detected=available_agents),
    )


def initialize_minimal_workspace(
    project_dir: Path,
    *,
    force: bool,
    bootstrap_sessions: bool,
) -> ActionResult:
    """Create the minimal built-in workspace config and state files."""
    import cc_branch.application.config_workflows as workflows

    config_path, state_path = workflows.init_minimal_workspace(project_dir, force, bootstrap_sessions)
    return ActionResult(
        ok=True,
        code="workspace_initialized",
        message="Workspace initialized",
        payload={"config_path": str(config_path), "state_path": str(state_path)},
    )


def initialize_workspace(
    project_dir: Path,
    *,
    profile: str,
    bootstrap_sessions: bool,
) -> ActionResult:
    """Initialize workspace files and return a transport-neutral payload."""
    import cc_branch.application.config_workflows as workflows

    env = workflows.check_environment(project_dir)
    result = workflows.initialize_workspace_files(
        project_dir,
        profile=profile,
        available_agents=env.available_agents,
        bootstrap_sessions_requested=bootstrap_sessions,
    )
    return ActionResult(
        ok=True,
        code="workspace_initialized",
        message="Workspace initialized",
        payload=init_payload(result, agents_detected=env.available_agents),
    )
