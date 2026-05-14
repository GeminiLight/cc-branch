"""Runtime workspace lifecycle operations."""

from __future__ import annotations

from pathlib import Path

from ...models import AppliedWindowResult, WorkspaceConfig, WorkspacePlan
from ..capabilities import (
    is_external_process_runtime,
    supports_attach,
    supports_background_start,
    supports_stop,
)


def apply_workspace(plan: WorkspacePlan, detach: bool = False) -> list[AppliedWindowResult]:
    """Start the configured workspace."""
    import cc_branch.runtime.execution as execution

    background_slots = [slot for slot in plan.slots if supports_background_start(slot.runtime)]
    if background_slots and not execution.get_backend().available():
        raise RuntimeError("tmux is required for workspace start")

    results: list[AppliedWindowResult] = []
    for slot in plan.slots:
        results.extend(
            execution.ensure_slot(
                slot,
                custom_openers=plan.openers,
                default_opener=plan.default_opener,
            )
        )

    if detach or not plan.slots:
        return results

    first_slot = next((slot for slot in plan.slots if supports_attach(slot.runtime)), None)
    if first_slot is None or not first_slot.windows:
        return results

    execution.get_backend().attach_session(first_slot.tmux_session)
    return results


def attach_slot(plan: WorkspacePlan, slot_name: str) -> None:
    """Attach to a slot or a specific window."""
    import cc_branch.runtime.execution as execution

    slot, window = execution._resolve_target(plan, slot_name)
    if slot is None:
        from ...exceptions import SlotNotFoundError

        raise SlotNotFoundError(f"unknown slot: {slot_name}")

    if is_external_process_runtime(slot.runtime):
        execution.ensure_slot(slot, custom_openers=plan.openers, default_opener=plan.default_opener)
        return

    target = slot.tmux_session if window is None else f"{slot.tmux_session}:{window.name}"
    execution.get_backend().attach_session(target)


def stop_workspace(
    workspace: WorkspaceConfig, plan: WorkspacePlan, target: str | None = None
) -> None:
    """Stop the whole workspace, a slot, or a single window."""
    import cc_branch.runtime.execution as execution

    stoppable_slots = [slot for slot in plan.slots if supports_stop(slot.runtime)]
    if stoppable_slots and not execution.get_backend().available():
        raise RuntimeError("tmux is required for workspace stop")

    execution._kill_dashboard(workspace)

    slots, window = execution._resolve_target_slots(plan, target)
    if not slots:
        for planned_slot in stoppable_slots:
            if execution.tmux_has_session(planned_slot.tmux_session):
                execution.get_backend().kill_session(planned_slot.tmux_session)
        return

    if window is None:
        for slot in slots:
            if not supports_stop(slot.runtime):
                continue
            if execution.tmux_has_session(slot.tmux_session):
                execution.get_backend().kill_session(slot.tmux_session)
        return

    slot = slots[0]
    if not supports_stop(slot.runtime):
        return

    if execution.tmux_has_window(slot.tmux_session, window.name):
        execution.get_backend().kill_window(f"{slot.tmux_session}:{window.name}")


def stop_extra_windows(sync_report, target: str | None = None) -> list[str]:
    """Stop extra tmux windows selected from a runtime sync report."""
    import cc_branch.runtime.execution as execution

    from ..sync import extra_window_targets

    stopped: list[str] = []
    for tmux_target in extra_window_targets(sync_report, target):
        execution.get_backend().kill_window(tmux_target)
        stopped.append(tmux_target)
    return stopped


def restart_workspace(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    target: str | None = None,
    detach: bool = False,
) -> list[AppliedWindowResult]:
    """Restart the whole workspace, a slot, or a single window."""
    import cc_branch.runtime.execution as execution

    restartable_slots = [slot for slot in plan.slots if supports_stop(slot.runtime)]
    if restartable_slots and not execution.get_backend().available():
        raise RuntimeError("tmux is required for workspace restart")

    slots, window = execution._resolve_target_slots(plan, target)

    if not slots:
        execution.stop_workspace(workspace, plan)
        results = execution.apply_workspace(plan, detach=True)
        if not detach and plan.slots:
            execution.attach_slot(plan, plan.slots[0].name)
        for result in results:
            if result.action == "created":
                result.action = "recreated"
        return results

    execution._kill_dashboard(workspace)
    if window is None:
        results = []
        for slot in slots:
            if is_external_process_runtime(slot.runtime):
                results.extend(
                    execution.ensure_slot(
                        slot,
                        custom_openers=plan.openers,
                        default_opener=plan.default_opener,
                    )
                )
                continue
            if execution.tmux_has_session(slot.tmux_session):
                execution.get_backend().kill_session(slot.tmux_session)
            results.extend(execution.ensure_slot(slot, created_action="recreated"))
        if not detach:
            attachable_slot = next((slot for slot in slots if supports_attach(slot.runtime)), None)
            if attachable_slot is not None:
                execution.attach_slot(plan, attachable_slot.name)
        return results

    slot = slots[0]
    if is_external_process_runtime(slot.runtime):
        execution.open_command(
            opener_id=window.opener or slot.opener or plan.default_opener or "auto-terminal",
            cwd=Path(window.cwd),
            command=window.launch_command,
            custom_openers=plan.openers,
        )
        return [
            AppliedWindowResult(
                slot=slot.name,
                window=window.name,
                key=window.key,
                runtime=slot.runtime,
                tmux_session=slot.tmux_session,
                action="opened_external",
            )
        ]

    if execution.tmux_has_window(slot.tmux_session, window.name):
        execution.get_backend().kill_window(f"{slot.tmux_session}:{window.name}")
    results = execution.ensure_slot(slot, created_action="recreated")
    if not detach:
        execution.attach_slot(plan, f"{slot.name}:{window.name}")
    return results
