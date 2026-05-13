"""Persisting applied runtime sync metadata."""

from __future__ import annotations

from datetime import datetime, timezone

from ...models import (
    AppliedWindowResult,
    SlotState,
    WindowState,
    WorkspaceConfig,
    WorkspacePlan,
    WorkspaceState,
)
from .models import LAUNCH_SPEC_VERSION


def record_applied_results(
    state: WorkspaceState,
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    results: list[AppliedWindowResult] | None,
) -> WorkspaceState:
    """Return state updated with fingerprints for windows actually launched."""
    if not results:
        return state

    import cc_branch.runtime.sync as sync

    next_state = WorkspaceState(version=state.version)
    next_state.windows.update(state.windows)
    next_state.slots.update(state.slots)
    applied_at = now_iso()

    for result in results:
        slot = plan.get_slot(result.slot)
        window = plan.get_window(result.slot, result.window)
        if slot is None:
            continue
        next_state.slots[slot.name] = SlotState(
            name=slot.name,
            tmux_session=slot.tmux_session,
            runtime=slot.runtime,
            last_seen_at=applied_at,
        )
        if window is None or result.action not in {"created", "recreated"}:
            continue

        existing = next_state.windows.get(window.key)
        if window.session_mode == "fresh":
            session_id = None
            binding_status = "fresh"
            binding_source = None
            binding_updated_at = None
        else:
            session_id = window.resolved_session_id or (existing.session_id if existing else None)
            binding_status = "bound" if session_id else (existing.session_binding_status if existing else None)
            binding_source = existing.session_binding_source if existing else None
            binding_updated_at = existing.session_binding_updated_at if existing else None
        next_state.windows[window.key] = WindowState(
            session_id=session_id,
            label=window.resolved_label or (existing.label if existing else None),
            agent=window.agent or (existing.agent if existing else None),
            slot=slot.name,
            window=window.name,
            launch_fingerprint=sync.desired_fingerprint(workspace, slot, window),
            launch_spec_version=LAUNCH_SPEC_VERSION,
            applied_at=applied_at,
            managed_runtime=slot.runtime,
            tmux_session=slot.tmux_session,
            session_binding_status=binding_status,
            session_binding_source=binding_source,
            session_binding_updated_at=binding_updated_at,
        )

    return next_state


def now_iso() -> str:
    """Return current UTC timestamp for state metadata."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
