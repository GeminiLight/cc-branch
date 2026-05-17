"""Runtime dashboard helpers."""

from __future__ import annotations

from ...models import WorkspaceConfig, WorkspacePlan
from ..capabilities import supports_dashboard


def dashboard_session_name(workspace: WorkspaceConfig) -> str:
    """Return the tmux session name used for the dashboard."""
    return f"{workspace.project}-dashboard"


def dashboard_layout(workspace: WorkspaceConfig, slot_count: int) -> str:
    """Return the tmux layout for the configured dashboard display mode."""
    mode = str(workspace.display.mode).lower()
    columns = max(1, int(workspace.display.columns) or 2)

    if mode in {"columns", "horizontal"}:
        return "even-horizontal"
    if mode in {"rows", "vertical"}:
        return "even-vertical"
    if mode != "grid":
        return "tiled"
    if columns <= 1:
        return "even-vertical"
    if columns >= slot_count:
        return "even-horizontal"
    return "tiled"


def kill_dashboard(workspace: WorkspaceConfig) -> None:
    """Kill the dashboard session if it exists."""
    import cc_branch.runtime.execution as execution

    dashboard = execution._dashboard_session_name(workspace)
    if execution.tmux_has_session(dashboard):
        try:
            execution.get_backend().kill_session(dashboard)
        except RuntimeError:
            pass


def open_dashboard(workspace: WorkspaceConfig, plan: WorkspacePlan) -> None:
    """Open a tiled tmux dashboard showing all dashboard-capable slots."""
    import cc_branch.runtime.execution as execution

    if not execution.get_backend().available():
        raise RuntimeError("tmux is required for workspace dashboard")

    slots = [slot for slot in plan.slots if supports_dashboard(slot.runtime)]
    if not slots:
        raise RuntimeError("dashboard requires at least one tmux runtime slot")

    for slot in slots:
        execution.ensure_slot(slot)

    dashboard = execution._dashboard_session_name(workspace)
    if execution.tmux_has_session(dashboard):
        execution.get_backend().attach_session(dashboard)
        return

    layout = execution._dashboard_layout(workspace, len(slots))
    first = slots[0].tmux_session
    execution.get_backend().create_session(
        dashboard,
        window_name="grid",
        command=execution.tmux_attach_shell_command(first),
    )

    for slot in slots[1:]:
        execution.get_backend().split_window(
            f"{dashboard}:grid",
            execution.tmux_attach_shell_command(slot.tmux_session),
        )

    execution.get_backend().select_layout(f"{dashboard}:grid", layout)
    execution.get_backend().attach_session(dashboard)
