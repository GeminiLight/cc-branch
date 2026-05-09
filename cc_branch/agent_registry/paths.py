"""Registry source path resolution."""

from __future__ import annotations

from pathlib import Path

from ..constants import WORKSPACE_AGENT_REGISTRY


def builtin_agents_path() -> Path:
    """Return the package path for built-in agent definitions."""
    from importlib.resources import files

    return files("cc_branch") / "agents.yaml"


def user_override_path() -> Path:
    """Return the user-level registry override path."""
    return Path.home() / ".cc-branch" / "agents.yaml"


def workspace_override_path(cwd: Path | None = None) -> Path:
    """Return the workspace-local registry override path."""
    return (cwd or Path.cwd()) / WORKSPACE_AGENT_REGISTRY
