"""Runtime slot/window creation helpers."""

from __future__ import annotations

import time
from pathlib import Path

from ...models import AppliedWindowResult, SlotPlan, WindowPlan
from ..capabilities import is_external_process_runtime


def ensure_window(
    session: str,
    slot: SlotPlan,
    window: WindowPlan,
    *,
    is_first: bool,
    created_action: str = "created",
) -> AppliedWindowResult:
    """Create a single managed-runtime window and send its launch commands."""
    import cc_branch.runtime.execution as execution

    name = window.name
    result = AppliedWindowResult(
        slot=slot.name,
        window=window.name,
        key=window.key,
        runtime=slot.runtime,
        tmux_session=session,
        action="already_present",
    )

    if is_first:
        if not execution.tmux_has_session(session):
            _create_and_launch(session, window)
            result.action = created_action  # type: ignore[assignment]
            return result
        if not execution.tmux_has_window(session, name):
            execution.get_backend().create_window(session, name, cwd=window.cwd)
            _launch_commands(session, window)
            result.action = created_action  # type: ignore[assignment]
            return result
    else:
        if execution.tmux_has_window(session, name):
            return result
        execution.get_backend().create_window(session, name, cwd=window.cwd)
        _launch_commands(session, window)
        result.action = created_action  # type: ignore[assignment]
        return result

    return result


def ensure_terminal_slot(
    slot: SlotPlan,
    *,
    custom_openers=None,
    default_opener: str | None = None,
) -> list[AppliedWindowResult]:
    """Open a visible terminal process for each window in a terminal slot."""
    import cc_branch.runtime.execution as execution

    opener_id = slot.opener or default_opener or "auto-terminal"
    results: list[AppliedWindowResult] = []
    for window in slot.windows:
        execution.open_command(
            opener_id=window.opener or opener_id,
            cwd=Path(window.cwd),
            command=window.launch_command,
            custom_openers=custom_openers,
        )
        results.append(
            AppliedWindowResult(
                slot=slot.name,
                window=window.name,
                key=window.key,
                runtime=slot.runtime,
                tmux_session=slot.tmux_session,
                action="opened_external",
            )
        )
    return results


def ensure_slot(
    slot: SlotPlan,
    *,
    custom_openers=None,
    default_opener: str | None = None,
    created_action: str = "created",
) -> list[AppliedWindowResult]:
    """Create or restore a runtime slot."""
    import cc_branch.runtime.execution as execution

    if is_external_process_runtime(slot.runtime):
        return execution._ensure_terminal_slot(
            slot,
            custom_openers=custom_openers,
            default_opener=default_opener,
        )

    if not slot.windows:
        return []

    results = [
        execution._ensure_window(
            slot.tmux_session,
            slot,
            slot.windows[0],
            is_first=True,
            created_action=created_action,
        )
    ]
    for window in slot.windows[1:]:
        results.append(
            execution._ensure_window(
                slot.tmux_session,
                slot,
                window,
                is_first=False,
                created_action=created_action,
            )
        )
    return results


def _create_and_launch(session: str, window: WindowPlan) -> None:
    import cc_branch.runtime.execution as execution

    execution.get_backend().create_session(session, cwd=window.cwd, window_name=window.name)
    _launch_commands(session, window)


def _launch_commands(session: str, window: WindowPlan) -> None:
    import cc_branch.runtime.execution as execution

    target = f"{session}:{window.name}"
    execution.send_keys(target, window.launch_command)
    for command in window.post_launch_commands:
        time.sleep(execution.POST_LAUNCH_DELAY)
        execution.send_keys(target, command)
