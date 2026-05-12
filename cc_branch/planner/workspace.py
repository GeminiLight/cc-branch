from __future__ import annotations

from pathlib import Path

from ..models import SlotPlan, WorkspaceConfig, WorkspacePlan, WorkspaceState
from ..runtime.capabilities import is_managed_runtime
from .commands import _build_window_plan
from .naming import tmux_session_name
from .slots import _slot_windows


def plan_workspace(
    workspace: WorkspaceConfig,
    state: WorkspaceState,
    bootstrap_missing: bool,
) -> WorkspacePlan:
    """Resolve config + state into a typed :class:`WorkspacePlan`."""
    plan_slots: list[SlotPlan] = []
    state_updates: dict[str, dict] = {}

    for slot in workspace.slots:
        planned_slot = SlotPlan(
            name=slot.name,
            runtime=slot.runtime,
            layout=slot.layout,
            opener=slot.opener,
            tmux_session=tmux_session_name(workspace.project, slot.name),
            cwd=str((Path(workspace.root) / slot.cwd).resolve()),
        )

        for window in _slot_windows(slot):
            window_plan = _build_window_plan(workspace, slot, window, state, bootstrap_missing)
            planned_slot.windows.append(window_plan)
            if window_plan.resolved_session_id or window_plan.resolved_label:
                state_updates[window_plan.key] = {
                    "session_id": window_plan.resolved_session_id,
                    "label": window_plan.resolved_label,
                    "agent": window_plan.agent,
                    "slot": slot.name,
                    "window": window.name,
                }

        plan_slots.append(planned_slot)

    return WorkspacePlan(
        project=workspace.project,
        root=workspace.root,
        openers=workspace.openers,
        default_opener=workspace.default_opener,
        slots=plan_slots,
        state_updates=state_updates,
    )


def format_plan(plan: WorkspacePlan) -> str:
    """Render a plan as human-readable text."""
    lines = [f"workspace {plan.project} plan"]
    for slot in plan.slots:
        target = slot.tmux_session if is_managed_runtime(slot.runtime) else (slot.opener or "terminal")
        lines.append(f"- slot {slot.name} [{slot.runtime}] -> {target}")
        for window in slot.windows:
            extra = []
            if window.resolved_session_id:
                extra.append(f"id={window.resolved_session_id}")
            if window.resolved_label:
                extra.append(f"label={window.resolved_label}")
            if window.bootstrapped:
                extra.append("bootstrapped")
            suffix = f" ({', '.join(extra)})" if extra else ""
            lines.append(f"  - {window.name}: {window.launch_command}{suffix}")
            for command in window.post_launch_commands:
                lines.append(f"    -> post: {command}")
    return "\n".join(lines)
