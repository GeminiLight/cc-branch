"""Shared workspace status query construction."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from ..config import load_workspace
from ..models import WorkspaceConfig, WorkspacePlan, WorkspaceState
from ..planner import plan_workspace
from ..runtime.capabilities import is_external_process_runtime, is_managed_runtime
from ..runtime.sync import build_runtime_sync_report
from ..state import load_state
from .results import ActionResult


SessionExists = Callable[[str], bool]
WindowExists = Callable[[str, str], bool]


def _default_session_exists(session: str) -> bool:
    from ..runtime import tmux_has_session

    return tmux_has_session(session)


def _default_window_exists(session: str, window: str) -> bool:
    from ..runtime import tmux_has_window

    return tmux_has_window(session, window)


def workspace_setup_payload(
    status: str,
    config_path: Path,
    state_path: Path,
    *,
    error: str | None = None,
) -> dict:
    """Return shared setup-state payload for workspace queries."""
    project_dir = config_path.parent
    payload = {
        "status": status,
        "project_path": str(project_dir),
        "config_path": str(config_path),
        "state_path": str(state_path),
        "project_name": project_dir.name or "project",
        "slots": [],
    }
    if error:
        payload["error"] = error
    return payload


def build_workspace_status(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    state: WorkspaceState | None = None,
    *,
    config_path: Path | None = None,
    state_path: Path | None = None,
    session_exists: SessionExists | None = None,
    window_exists: WindowExists | None = None,
) -> dict:
    """Return the shared status payload used by presentation surfaces."""
    session_exists = session_exists or _default_session_exists
    window_exists = window_exists or _default_window_exists
    sync_report = build_runtime_sync_report(workspace, plan, state) if state is not None else None
    sync_slots = {slot.name: slot for slot in sync_report.slots} if sync_report else {}

    slots: list[dict] = []
    for slot in plan.slots:
        slot_running = is_managed_runtime(slot.runtime) and session_exists(slot.tmux_session)
        slot_status = "running" if slot_running else "stopped"
        if is_external_process_runtime(slot.runtime):
            slot_status = "external"

        slot_sync = sync_slots.get(slot.name)
        window_sync = {w.name: w for w in slot_sync.windows} if slot_sync else {}
        windows: list[dict] = []
        for window in slot.windows:
            window_running = (
                slot_running
                and is_managed_runtime(slot.runtime)
                and window_exists(slot.tmux_session, window.name)
            )
            window_status = "running" if window_running else "stopped"
            if is_external_process_runtime(slot.runtime):
                window_status = "external"
            sync = window_sync.get(window.name)
            windows.append(
                {
                    "name": window.name,
                    "agent": window.agent,
                    "command": window.launch_command,
                    "session_id": window.resolved_session_id,
                    "label": window.resolved_label,
                    "cwd": window.cwd,
                    "status": window_status,
                    "sync_status": sync.sync_status if sync else None,
                    "needs_restart": bool(sync and sync.needs_restart),
                }
            )

        slots.append(
            {
                "name": slot.name,
                "runtime": slot.runtime,
                "session_name": slot.tmux_session,
                "status": slot_status,
                "windows": windows,
                "sync_status": slot_sync.sync_status if slot_sync else None,
                "extra_windows": [w.to_dict() for w in slot_sync.extra_windows] if slot_sync else [],
            }
        )

    payload = {
        "status": "ready",
        "project": workspace.project,
        "root": str(workspace.root),
        "slots": slots,
    }
    if config_path is not None:
        payload["config_path"] = str(config_path)
    if state_path is not None:
        payload["state_path"] = str(state_path)
    if sync_report is not None:
        payload["runtime_sync"] = sync_report.to_dict()
    return payload


def get_workspace_status(
    config_path: Path,
    state_path: Path,
    *,
    session_exists: SessionExists | None = None,
    window_exists: WindowExists | None = None,
) -> ActionResult:
    """Load, plan, and inspect a workspace status for presentation surfaces."""
    if not config_path.parent.exists():
        return ActionResult(
            ok=True,
            code="workspace_missing",
            message="Project directory does not exist",
            payload=workspace_setup_payload("missing", config_path, state_path),
        )
    if not config_path.exists():
        return ActionResult(
            ok=True,
            code="workspace_needs_init",
            message="Workspace config not found",
            payload=workspace_setup_payload("needs_init", config_path, state_path),
        )

    try:
        workspace = load_workspace(config_path)
        state = load_state(state_path)
        plan = plan_workspace(workspace, state, False)
        return ActionResult(
            ok=True,
            code="workspace_ready",
            message="Workspace status loaded",
            payload=build_workspace_status(
                workspace,
                plan,
                state,
                config_path=config_path,
                state_path=state_path,
                session_exists=session_exists,
                window_exists=window_exists,
            ),
        )
    except Exception as exc:
        return ActionResult(
            ok=False,
            code="invalid_config",
            message=str(exc),
            exit_code=1,
            payload=workspace_setup_payload(
                "invalid_config",
                config_path,
                state_path,
                error=str(exc),
            ),
        )
