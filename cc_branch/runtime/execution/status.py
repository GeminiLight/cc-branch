"""Runtime status query and formatting."""

from __future__ import annotations

from ...models import WorkspaceConfig, WorkspacePlan
from ..capabilities import is_external_process_runtime, supports_attach


def list_window_names(session: str) -> set[str]:
    """Return the set of window names inside a tmux session."""
    import cc_branch.runtime.execution as execution

    return execution.get_backend().list_windows(session)


def build_status_data(workspace: WorkspaceConfig, plan: WorkspacePlan) -> dict:
    """Return structured status data without formatting."""
    import cc_branch.runtime.execution as execution

    slots: list[dict] = []
    for slot in plan.slots:
        if supports_attach(slot.runtime):
            running = execution.tmux_has_session(slot.tmux_session)
            status = "running" if running else "stopped"
            present_windows = execution._list_window_names(slot.tmux_session) if running else set()
        else:
            running = False
            status = "external"
            present_windows = set()
        windows: list[dict] = []
        for window in slot.windows:
            window_status = "present" if window.name in present_windows else "missing"
            if is_external_process_runtime(slot.runtime):
                window_status = "external"
            windows.append(
                {
                    "name": window.name,
                    "agent": window.agent,
                    "session_id": window.resolved_session_id,
                    "label": window.resolved_label,
                    "present": window.name in present_windows,
                    "status": window_status,
                }
            )
        slots.append(
            {
                "name": slot.name,
                "runtime": slot.runtime,
                "session": slot.tmux_session,
                "running": running,
                "status": status,
                "windows": windows,
            }
        )
    return {"project": workspace.project, "root": workspace.root, "slots": slots}


def format_status(workspace: WorkspaceConfig, plan: WorkspacePlan, state=None) -> str:
    """Format workspace status as plain text."""
    import cc_branch.runtime.execution as execution

    data = execution.build_status_data(workspace, plan)
    sync_by_key = {}
    slot_sync = {}
    if state is not None:
        from ..sync import build_runtime_sync_report

        sync_report = build_runtime_sync_report(workspace, plan, state)
        for slot_report in sync_report.slots:
            slot_sync[slot_report.name] = slot_report.sync_status
            for window_report in slot_report.windows:
                sync_by_key[window_report.key] = window_report.sync_status
    lines = [f"workspace {data['project']} @ {data['root']}"]
    for slot in data["slots"]:
        status = slot["status"]
        sync_suffix = f" sync={slot_sync[slot['name']]}" if slot["name"] in slot_sync else ""
        lines.append(
            f"- {slot['name']} [{slot['runtime']}] session={slot['session']} status={status}{sync_suffix}"
        )
        for window in slot["windows"]:
            session_id = window.get("session_id") or "-"
            label = window.get("label") or "-"
            agent = window.get("agent") or "command"
            window_status = window.get("status") or ("present" if window.get("present") else "missing")
            key = f"{slot['name']}.{window['name']}"
            sync = sync_by_key.get(key)
            sync_text = f" sync={sync}" if sync else ""
            lines.append(
                f"  - {window['name']}: agent={agent} "
                f"window={window_status}{sync_text} session_id={session_id} label={label}"
            )
    return "\n".join(lines)
