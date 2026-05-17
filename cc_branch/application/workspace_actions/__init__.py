"""Shared workspace action use cases."""

from __future__ import annotations

from pathlib import Path

from ...openers import (
    OpenCommandSpec,
    OpenerError,
    OpenIntent,
    open_command_layout,
    open_with,
    open_workspace_file,
    opener_label,
    opener_supports,
)
from ...runtime import (
    apply_workspace,
    attach_slot,
    ensure_slot,
    open_dashboard,
    stop_extra_windows,
)
from ...runtime import (
    restart_workspace as _restart_runtime_workspace,
)
from ...runtime import (
    stop_workspace as _stop_runtime_workspace,
)
from .command_specs import (
    WorkspaceCommandSpecs,
    _attach_target_specs,
    _terminal_command_specs,
    _tmux_slot_attach_specs,
    _tmux_window_attach_specs,
)
from .dependencies import WorkspaceActionDependencies
from .executor import WorkspaceActionExecutor
from .lifecycle import WorkspaceLifecycleActions
from .open import WorkspaceOpenActions
from .persistence import AppliedResultPersistence, _persist_applied_results
from .sync import WorkspaceSyncActions
from .targets import (
    WorkspaceTargetResolver,
    _normalize_action_target,
    _resolve_open_intent,
    _resolve_target,
    _target_slot,
    _terminal_slots,
    _tmux_slots,
)


def _dependencies() -> WorkspaceActionDependencies:
    return WorkspaceActionDependencies(
        apply_workspace=apply_workspace,
        attach_slot=attach_slot,
        ensure_slot=ensure_slot,
        open_dashboard=open_dashboard,
        restart_runtime_workspace=_restart_runtime_workspace,
        stop_extra_windows=stop_extra_windows,
        stop_runtime_workspace=_stop_runtime_workspace,
        open_command_layout=open_command_layout,
        open_with=open_with,
        open_workspace_file=open_workspace_file,
        opener_label=opener_label,
        opener_supports=opener_supports,
    )


def _lifecycle() -> WorkspaceLifecycleActions:
    return WorkspaceLifecycleActions(_dependencies())


def _open_actions() -> WorkspaceOpenActions:
    return WorkspaceOpenActions(_dependencies())


def _sync_actions() -> WorkspaceSyncActions:
    return WorkspaceSyncActions(_dependencies())


def stop_workspace(*args, **kwargs):
    """Stop a workspace, tmux slot, or tmux window."""
    return _lifecycle().stop_workspace(*args, **kwargs)


def restart_workspace(*args, **kwargs):
    """Restart a tmux workspace, slot, or window and persist applied metadata."""
    return _lifecycle().restart_workspace(*args, **kwargs)


def launch_workspace(*args, **kwargs):
    """Launch tmux runtime slots in the background and persist applied metadata."""
    return _lifecycle().launch_workspace(*args, **kwargs)


def start_workspace(*args, **kwargs):
    """Start the full workspace and persist applied runtime metadata."""
    return _lifecycle().start_workspace(*args, **kwargs)


def attach_workspace(*args, **kwargs):
    """Attach to a tmux target or open an external terminal-runtime target."""
    return _lifecycle().attach_workspace(*args, **kwargs)


def open_dashboard_workspace(*args, **kwargs):
    """Open the tmux dashboard and persist any created slot metadata."""
    return _lifecycle().open_dashboard_workspace(*args, **kwargs)


def open_workspace(*args, **kwargs):
    """Open a workspace, project folder, or target through a configured opener."""
    return _open_actions().open_workspace(*args, **kwargs)


def sync_workspace(*args, **kwargs):
    """Reconcile changed, missing, or untracked runtime targets."""
    return _sync_actions().sync_workspace(*args, **kwargs)


def execute_workspace_action(
    config_path: Path,
    state_path: Path,
    *,
    action: str | None,
    target: str | None = None,
    opener: str | None = None,
    intent: str | None = None,
    stop_removed: bool = False,
    cli: str = "cc-branch",
):
    """Load a workspace and execute a user-facing action request."""
    return WorkspaceActionExecutor(_dependencies()).execute(
        config_path,
        state_path,
        action=action,
        target=target,
        opener=opener,
        intent=intent,
        stop_removed=stop_removed,
        cli=cli,
    )


__all__ = [
    "AppliedResultPersistence",
    "OpenCommandSpec",
    "OpenerError",
    "OpenIntent",
    "WorkspaceActionDependencies",
    "WorkspaceActionExecutor",
    "WorkspaceCommandSpecs",
    "WorkspaceLifecycleActions",
    "WorkspaceOpenActions",
    "WorkspaceSyncActions",
    "WorkspaceTargetResolver",
    "attach_workspace",
    "execute_workspace_action",
    "launch_workspace",
    "open_dashboard_workspace",
    "open_workspace",
    "restart_workspace",
    "start_workspace",
    "stop_workspace",
    "sync_workspace",
]
