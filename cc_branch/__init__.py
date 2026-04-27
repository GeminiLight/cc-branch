"""cc-branch — Multi-agent workspace orchestrator."""

from __future__ import annotations

from .adapters import AgentAdapter, get_adapter
from .backends import Backend, TmuxBackend, get_backend, set_backend
from .config import init_workspace, load_workspace
from .context import WorkspaceContext
from .exceptions import (
    CcbError,
    ConfigError,
    RuntimeError,
    SlotNotFoundError,
    StateError,
    WindowNotFoundError,
    WorkspaceError,
)
from .models import (
    AgentSpec,
    DisplayConfig,
    DoctorReport,
    Issue,
    SlotConfig,
    SlotPlan,
    WindowConfig,
    WindowPlan,
    WorkspaceConfig,
    WorkspacePlan,
    WorkspaceState,
)
from .planner import plan_workspace
from .repository import StateRepository
from .sessions import inspect_session, list_sessions, prune_sessions, restore_session
from .state import load_state, merge_state, save_state


def main(argv: list[str] | None = None) -> int:
    from .cli import main as cli_main

    return cli_main(argv)


__all__ = [
    "init_workspace",
    "load_state",
    "load_workspace",
    "main",
    "merge_state",
    "plan_workspace",
    "save_state",
    "AgentAdapter",
    "AgentSpec",
    "DisplayConfig",
    "DoctorReport",
    "get_adapter",
    "get_backend",
    "inspect_session",
    "Issue",
    "list_sessions",
    "prune_sessions",
    "restore_session",
    "set_backend",
    "SlotConfig",
    "SlotPlan",
    "WindowConfig",
    "WindowPlan",
    "WorkspaceConfig",
    "WorkspaceContext",
    "WorkspacePlan",
    "WorkspaceState",
    "StateRepository",
    "TmuxBackend",
]
