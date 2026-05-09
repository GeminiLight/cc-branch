"""Runtime sync report construction."""

from __future__ import annotations

from ...models import WorkspaceConfig, WorkspacePlan, WorkspaceState
from ..capabilities import is_external_process_runtime, is_managed_runtime
from .models import RuntimeSyncReport, SlotSyncStatus, SyncStatus, WindowSyncStatus


def build_runtime_sync_report(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    state: WorkspaceState,
) -> RuntimeSyncReport:
    """Compare desired plan, local state, and tmux presence."""
    import cc_branch.runtime.sync as sync

    summary = dict.fromkeys(("current", "changed", "missing", "extra", "orphaned", "untracked", "external"), 0)
    slot_reports: list[SlotSyncStatus] = []
    plan_keys: set[str] = set()
    current_sessions = {slot.tmux_session for slot in plan.slots if is_managed_runtime(slot.runtime)}

    for slot in plan.slots:
        present_windows = (
            sync._list_window_names(slot.tmux_session)
            if is_managed_runtime(slot.runtime) and sync._tmux_has_session(slot.tmux_session)
            else set()
        )
        window_reports: list[WindowSyncStatus] = []

        for window in slot.windows:
            plan_keys.add(window.key)
            desired = sync.desired_fingerprint(workspace, slot, window)
            state_entry = state.get_window(window.key)
            applied = state_entry.launch_fingerprint if state_entry else None
            sync_status, runtime_status = _window_sync_status(slot.runtime, window.name, present_windows, applied, desired)

            summary[sync_status] += 1
            window_reports.append(
                WindowSyncStatus(
                    name=window.name,
                    key=window.key,
                    runtime_status=runtime_status,
                    sync_status=sync_status,
                    needs_restart=sync_status in {"changed", "missing", "untracked"},
                    desired_fingerprint=desired,
                    applied_fingerprint=applied,
                    change_reason=[] if sync_status != "changed" else ["launch_spec"],
                )
            )

        extra_reports = _extra_window_reports(slot, present_windows)
        summary["extra"] += len(extra_reports)
        slot_reports.append(
            SlotSyncStatus(
                name=slot.name,
                runtime=slot.runtime,
                tmux_session=slot.tmux_session,
                sync_status=_slot_sync_status(slot.runtime, window_reports, extra_reports),
                windows=window_reports,
                extra_windows=extra_reports,
            )
        )

    orphaned_state = _orphaned_state_entries(state, plan_keys, summary)
    historical_sessions = _historical_sessions(state, current_sessions)
    return RuntimeSyncReport(
        summary=summary,
        slots=slot_reports,
        orphaned_state=orphaned_state,
        historical_sessions=historical_sessions,
    )


def _window_sync_status(
    runtime: str,
    window_name: str,
    present_windows: set[str],
    applied: str | None,
    desired: str,
) -> tuple[SyncStatus, str]:
    if is_external_process_runtime(runtime):
        return "external", "external"
    if window_name not in present_windows:
        return "missing", "missing"
    if not applied:
        return "untracked", "present"
    if applied == desired:
        return "current", "present"
    return "changed", "present"


def _extra_window_reports(slot, present_windows: set[str]) -> list[WindowSyncStatus]:
    if not is_managed_runtime(slot.runtime):
        return []
    planned_window_names = {window.name for window in slot.windows}
    return [
        WindowSyncStatus(
            name=name,
            key=f"{slot.name}.{name}",
            runtime_status="present",
            sync_status="extra",
        )
        for name in sorted(present_windows - planned_window_names)
    ]


def _slot_sync_status(
    runtime: str,
    window_reports: list[WindowSyncStatus],
    extra_reports: list[WindowSyncStatus],
) -> SyncStatus:
    if is_external_process_runtime(runtime):
        return "external"
    for report in [*window_reports, *extra_reports]:
        if report.sync_status in {"changed", "missing", "extra", "untracked"}:
            return report.sync_status
    return "current"


def _orphaned_state_entries(
    state: WorkspaceState,
    plan_keys: set[str],
    summary: dict[str, int],
) -> list[dict]:
    orphaned_state: list[dict] = []
    for key, entry in sorted(state.windows.items()):
        if key in plan_keys:
            continue
        summary["orphaned"] += 1
        orphaned_state.append(
            {
                "key": key,
                "slot": entry.slot,
                "window": entry.window,
                "agent": entry.agent,
                "session_id": entry.session_id,
                "label": entry.label,
                "tmux_session": entry.tmux_session,
            }
        )
    return orphaned_state


def _historical_sessions(state: WorkspaceState, current_sessions: set[str]) -> list[dict]:
    import cc_branch.runtime.sync as sync

    historical_sessions: list[dict] = []
    for key, entry in sorted(state.slots.items()):
        if not entry.tmux_session or entry.tmux_session in current_sessions:
            continue
        if sync._tmux_has_session(entry.tmux_session):
            historical_sessions.append(
                {
                    "key": key,
                    "name": entry.name,
                    "runtime": entry.runtime,
                    "tmux_session": entry.tmux_session,
                    "last_seen_at": entry.last_seen_at,
                    "status": "running",
                }
            )
    return historical_sessions
