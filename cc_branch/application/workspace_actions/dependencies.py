"""Runtime and opener dependencies for workspace action use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class WorkspaceActionDependencies:
    """Callables used by workspace action use cases to cross infrastructure boundaries."""

    apply_workspace: Callable
    attach_slot: Callable
    ensure_slot: Callable
    open_dashboard: Callable
    restart_runtime_workspace: Callable
    stop_extra_windows: Callable
    stop_runtime_workspace: Callable
    open_command_layout: Callable
    open_with: Callable
    open_workspace_file: Callable
    opener_label: Callable
    opener_supports: Callable
