"""First-run bootstrap facade.

The package separates environment probing, starter config generation, session
metadata creation, and file writes while preserving the historical
``cc_branch.bootstrap`` public API.
"""

from __future__ import annotations

from pathlib import Path

from ..runtime import which
from . import environment as _environment
from .files import ensure_state_gitignored, initialize_workspace_files
from .generation import generate_starter_config, summarize_config
from .models import AgentStatus, ConfigSummary, EnvironmentReport, WorkspaceInitResult
from .sessions import bootstrap_sessions


def check_environment(
    target_dir: Path,
    timeout: float = 2.0,
) -> EnvironmentReport:
    """Check runtime and agent CLI availability."""
    _environment.which = which
    return _environment.check_environment(target_dir, timeout)


__all__ = [
    "AgentStatus",
    "ConfigSummary",
    "EnvironmentReport",
    "WorkspaceInitResult",
    "bootstrap_sessions",
    "check_environment",
    "ensure_state_gitignored",
    "generate_starter_config",
    "initialize_workspace_files",
    "summarize_config",
    "which",
]
