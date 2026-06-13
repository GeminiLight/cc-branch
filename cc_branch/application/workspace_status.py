"""Shared workspace status query construction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

TRANSCRIPT_TAIL_BYTES = 64 * 1024

from ..config import load_workspace, project_dir_for_config
from ..models import WorkspaceConfig, WorkspacePlan, WorkspaceState
from ..planner import plan_workspace
from ..runtime.capabilities import is_external_process_runtime, is_managed_runtime
from ..runtime.sync import build_runtime_sync_report
from ..state import load_state
from .agent_bus import AgentBusStore
from .agent_worktrees import AgentWorktreeStore, CommandRunner, worktree_status_for_agents
from .results import ActionResult
from .runtime_environment import runtime_availability

SessionExists = Callable[[str], bool]
WindowExists = Callable[[str, str], bool]


def _default_session_exists(session: str) -> bool:
    from ..runtime import tmux_has_session

    return tmux_has_session(session)


def _default_window_exists(session: str, window: str) -> bool:
    from ..runtime import tmux_has_window

    return tmux_has_window(session, window)


def _session_binding_status(window, state_entry) -> str:
    if not window.agent:
        return "none"
    if window.session_mode == "fresh":
        return "fresh"
    if window.resolved_session_id:
        return "bound"
    if state_entry and state_entry.session_binding_status:
        return state_entry.session_binding_status
    if window.session_mode == "auto":
        if window.create_mode == "generated_uuid":
            return "will_bootstrap"
        if window.resume_mode != "none":
            return "will_capture"
        return "will_create"
    return "none"


def _activity_from_transcript(path: str | None) -> dict:
    if not path:
        return {"summary": None, "source": None}
    transcript_path = Path(path)
    if not transcript_path.exists():
        return {"summary": None, "source": "transcript", "path": path}
    try:
        with transcript_path.open("rb") as file:
            file.seek(0, 2)
            size = file.tell()
            file.seek(max(0, size - TRANSCRIPT_TAIL_BYTES))
            chunk = file.read().decode("utf-8", errors="replace")
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
    except OSError:
        return {"summary": None, "source": "transcript", "path": path}
    if not lines:
        return {"summary": None, "source": "transcript", "path": path}
    last = lines[-1]
    try:
        parsed = json.loads(last)
    except json.JSONDecodeError:
        summary = last
    else:
        summary = _summarize_transcript_record(parsed) or last
    return {"summary": summary[-500:], "source": "transcript", "path": path}


def _summarize_transcript_record(record) -> str | None:
    if isinstance(record, str):
        return record
    if not isinstance(record, dict):
        return None
    for key in ("message", "text", "content", "summary"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _agent_status_value(window_status: str, state_entry) -> str:
    if window_status == "disabled":
        return "disabled"
    if state_entry and (
        state_entry.session_hook_event == "error"
        or (
            state_entry.session_exit_code is not None
            and state_entry.session_exit_code != 0
        )
    ):
        return "error"
    if window_status == "running":
        return "busy"
    if state_entry and state_entry.session_runtime_status == "running":
        return "stale"
    if window_status == "external":
        return "external"
    return "stopped"


def _remote_payload(remote) -> dict | None:
    if remote is None:
        return None
    return {
        "host": remote.host,
        "user": remote.user,
        "port": remote.port,
        "cwd": remote.cwd,
        "target": remote.target(),
    }


def _agent_actions(slot_runtime: str, window_status: str) -> list[str]:
    if window_status == "disabled":
        return []
    if is_managed_runtime(slot_runtime):
        if window_status == "running":
            return ["attach", "send", "restart", "stop"]
        return ["attach", "restart"]
    if is_external_process_runtime(slot_runtime):
        return ["open"]
    return []


def _agent_inbox_summary(bus_store: AgentBusStore, target: str) -> dict:
    messages = bus_store.inbox(target=target, unread_only=False, limit=20)
    unread = bus_store.inbox(target=target, unread_only=True)
    last = messages[-1] if messages else None
    return {
        "unread": len(unread),
        "last_message": last.get("message") if last else None,
        "updated_at": last.get("timestamp") if last else None,
    }


def workspace_setup_payload(
    status: str,
    config_path: Path,
    state_path: Path,
    *,
    error: str | None = None,
) -> dict:
    """Return shared setup-state payload for workspace queries."""
    project_dir = project_dir_for_config(config_path)
    payload = {
        "status": status,
        "project_path": str(project_dir),
        "config_path": str(config_path),
        "state_path": str(state_path),
        "project_name": project_dir.name or "project",
        "slots": [],
        "agents": [],
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
    bus_store: AgentBusStore | None = None,
    worktree_store: AgentWorktreeStore | None = None,
    worktree_runner: CommandRunner | None = None,
) -> dict:
    """Return the shared status payload used by presentation surfaces."""
    session_exists = session_exists or _default_session_exists
    window_exists = window_exists or _default_window_exists
    bus_store = bus_store or AgentBusStore()
    worktree_by_target = {
        str(item.get("target")): item
        for item in worktree_status_for_agents(store=worktree_store, runner=worktree_runner)
    }
    sync_report = build_runtime_sync_report(workspace, plan, state) if state is not None else None
    sync_slots = {slot.name: slot for slot in sync_report.slots} if sync_report else {}

    slots: list[dict] = []
    agents: list[dict] = []
    for slot in plan.slots:
        slot_sync = sync_slots.get(slot.name)
        if sync_report is not None and slot_sync is not None:
            slot_running = is_managed_runtime(slot.runtime) and (
                any(window.runtime_status == "present" for window in slot_sync.windows)
                or bool(slot_sync.extra_windows)
            )
        else:
            slot_running = is_managed_runtime(slot.runtime) and session_exists(slot.tmux_session)
        slot_status = "running" if slot_running else "stopped"
        if is_external_process_runtime(slot.runtime):
            slot_status = "external"

        window_sync = {w.name: w for w in slot_sync.windows} if slot_sync else {}
        windows: list[dict] = []
        for window in slot.windows:
            state_entry = state.get_window(window.key) if state is not None else None
            sync = window_sync.get(window.name)
            if sync_report is not None and sync is not None:
                window_running = is_managed_runtime(slot.runtime) and sync.runtime_status == "present"
            else:
                window_running = (
                    slot_running
                    and is_managed_runtime(slot.runtime)
                    and window_exists(slot.tmux_session, window.name)
                )
            window_status = "running" if window_running else "stopped"
            if not window.enabled:
                window_status = "disabled"
            if is_external_process_runtime(slot.runtime):
                window_status = "disabled" if not window.enabled else "external"
            window_payload = (
                {
                    "name": window.name,
                    "enabled": window.enabled,
                    "agent": window.agent,
                    "command": window.launch_command,
                    "session_id": window.resolved_session_id,
                    "session_intent": window.session_mode,
                    "session_binding_status": _session_binding_status(window, state_entry),
                    "session_binding_source": state_entry.session_binding_source if state_entry else None,
                    "session_binding_updated_at": state_entry.session_binding_updated_at if state_entry else None,
                    "session_hook_event": state_entry.session_hook_event if state_entry else None,
                    "session_hook_updated_at": state_entry.session_hook_updated_at if state_entry else None,
                    "session_runtime_status": state_entry.session_runtime_status if state_entry else None,
                    "session_transcript_path": state_entry.session_transcript_path if state_entry else None,
                    "session_pid": state_entry.session_pid if state_entry else None,
                    "session_exit_code": state_entry.session_exit_code if state_entry else None,
                    "label": window.resolved_label,
                    "cwd": window.cwd,
                    "status": window_status,
                    "sync_status": sync.sync_status if sync else None,
                    "needs_restart": bool(sync and sync.needs_restart),
                }
            )
            windows.append(window_payload)

            if window.agent:
                remote = window.remote
                target = f"{slot.name}:{window.name}"
                agent_spec = workspace.agents.get(window.agent)
                agents.append(
                    {
                        "target": target,
                        "name": window.resolved_label or window.agent or window.name,
                        "agent": window.agent,
                        "cli": agent_spec.command if agent_spec else window.command_binary,
                        "command": window.launch_command,
                        "location": "ssh" if remote else "local",
                        "remote": _remote_payload(remote),
                        "cwd": remote.cwd if remote and remote.cwd else window.cwd,
                        "runtime": slot.runtime,
                        "slot": slot.name,
                        "window": window.name,
                        "tmux_session": slot.tmux_session if is_managed_runtime(slot.runtime) else None,
                        "tmux_window": window.name if is_managed_runtime(slot.runtime) else None,
                        "session_id": window.resolved_session_id,
                        "transcript_path": state_entry.session_transcript_path if state_entry else None,
                        "status": _agent_status_value(window_status, state_entry),
                        "activity": _activity_from_transcript(
                            state_entry.session_transcript_path if state_entry else None
                        ),
                        "inbox": _agent_inbox_summary(bus_store, target),
                        "worktree": worktree_by_target.get(target),
                        "actions": _agent_actions(slot.runtime, window_status),
                    }
                )

        slots.append(
            {
                "name": slot.name,
                "runtime": slot.runtime,
                "layout": slot.layout,
                "split_group": slot.split_group,
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
        "runtimes": runtime_availability(),
        "slots": slots,
        "agents": agents,
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
    project_dir = project_dir_for_config(config_path)
    if not project_dir.exists():
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
