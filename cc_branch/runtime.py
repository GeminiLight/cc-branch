"""Runtime functions for tmux-based workspace management.

Public API operates on typed models.
"""

from __future__ import annotations

import subprocess  # noqa: F401  # retained for test patch compatibility
import time

from .backends import get_backend
from .exceptions import SlotNotFoundError, WindowNotFoundError
from .models import SlotPlan, WindowPlan, WorkspaceConfig, WorkspacePlan
from .shells import tmux_attach_shell_command
from .targets import parse_target

# Configurable delay between post-launch commands (seconds).
POST_LAUNCH_DELAY: float = 0.2


def which(name: str) -> str | None:
    """Return the path to executable *name* or None."""
    import shutil

    return shutil.which(name)


def tmux_has_session(name: str) -> bool:
    """Check whether tmux session *name* exists."""
    return get_backend().has_session(name)


def tmux_has_window(session: str, window: str) -> bool:
    """Check whether *window* exists inside tmux *session*."""
    return get_backend().has_window(session, window)


def send_keys(target: str, command: str) -> None:
    """Send *command* followed by Enter to a tmux *target*."""
    if not command:
        return
    get_backend().send_keys(target, command)


def _resolve_target(
    plan: WorkspacePlan, target: str | None
) -> tuple[SlotPlan | None, WindowPlan | None]:
    """Parse a target string like ``slot`` or ``slot:window``."""
    if not target:
        return None, None

    parsed = parse_target(target)
    slot = plan.get_slot(parsed.slot)
    if slot is None:
        raise SlotNotFoundError(f"unknown slot: {target}")

    if parsed.window is None:
        return slot, None

    window = _get_window(slot, parsed.window)
    if window is None:
        raise WindowNotFoundError(f"unknown window: {target}")

    return slot, window


# Need a helper on SlotPlan for window lookup by name
def _get_window(slot: SlotPlan, window_name: str) -> WindowPlan | None:
    for w in slot.windows:
        if w.name == window_name:
            return w
    return None


def _dashboard_session_name(workspace: WorkspaceConfig) -> str:
    return f"{workspace.project}-dashboard"


def _dashboard_layout(workspace: WorkspaceConfig, slot_count: int) -> str:
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


def _kill_dashboard(workspace: WorkspaceConfig) -> None:
    dashboard = _dashboard_session_name(workspace)
    if tmux_has_session(dashboard):
        try:
            get_backend().kill_session(dashboard)
        except RuntimeError:
            # Session may have already disappeared (race condition).
            pass


def _ensure_window(
    session: str,
    window: WindowPlan,
    *,
    is_first: bool,
) -> None:
    """Create a single window and send its launch commands."""
    name = window.name
    cwd = window.cwd
    launch = window.launch_command
    post = window.post_launch_commands

    if is_first:
        if not tmux_has_session(session):
            get_backend().create_session(session, cwd=cwd, window_name=name)
            send_keys(f"{session}:{name}", launch)
            for command in post:
                time.sleep(POST_LAUNCH_DELAY)
                send_keys(f"{session}:{name}", command)
            return
        elif not tmux_has_window(session, name):
            get_backend().create_window(session, name, cwd=cwd)
            send_keys(f"{session}:{name}", launch)
            for command in post:
                time.sleep(POST_LAUNCH_DELAY)
                send_keys(f"{session}:{name}", command)
            return
    else:
        if tmux_has_window(session, name):
            return
        get_backend().create_window(session, name, cwd=cwd)
        send_keys(f"{session}:{name}", launch)
        for command in post:
            time.sleep(POST_LAUNCH_DELAY)
            send_keys(f"{session}:{name}", command)


def ensure_slot(slot: SlotPlan) -> None:
    """Create or restore a single slot (tmux session + windows)."""
    session = slot.tmux_session
    windows = slot.windows
    if not windows:
        return

    _ensure_window(session, windows[0], is_first=True)
    for window in windows[1:]:
        _ensure_window(session, window, is_first=False)


def apply_workspace(plan: WorkspacePlan, detach: bool = False) -> None:
    """Start the configured workspace."""
    if not get_backend().available():
        raise RuntimeError("tmux is required for workspace start")

    for slot in plan.slots:
        ensure_slot(slot)

    if detach or not plan.slots:
        return

    first_slot = plan.slots[0]
    if not first_slot.windows:
        return

    get_backend().attach_session(first_slot.tmux_session)


def attach_slot(plan: WorkspacePlan, slot_name: str) -> None:
    """Attach to a slot or a specific window."""
    slot, window = _resolve_target(plan, slot_name)
    if slot is None:
        raise SlotNotFoundError(f"unknown slot: {slot_name}")

    target = slot.tmux_session
    if window is not None:
        target = f"{target}:{window.name}"

    get_backend().attach_session(target)


def stop_workspace(
    workspace: WorkspaceConfig, plan: WorkspacePlan, target: str | None = None
) -> None:
    """Stop the whole workspace, a slot, or a single window."""
    if not get_backend().available():
        raise RuntimeError("tmux is required for workspace stop")  # noqa: EM101

    _kill_dashboard(workspace)

    slot, window = _resolve_target(plan, target)
    if slot is None:
        for planned_slot in plan.slots:
            if tmux_has_session(planned_slot.tmux_session):
                get_backend().kill_session(planned_slot.tmux_session)
        return

    if window is None:
        if tmux_has_session(slot.tmux_session):
            get_backend().kill_session(slot.tmux_session)
        return

    if tmux_has_window(slot.tmux_session, window.name):
        get_backend().kill_window(f"{slot.tmux_session}:{window.name}")


def restart_workspace(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    target: str | None = None,
    detach: bool = False,
) -> None:
    """Restart the whole workspace, a slot, or a single window."""
    if not get_backend().available():
        raise RuntimeError("tmux is required for workspace restart")

    slot, window = _resolve_target(plan, target)

    if slot is None:
        stop_workspace(workspace, plan)
        apply_workspace(plan, detach=True)
        if not detach and plan.slots:
            attach_slot(plan, plan.slots[0].name)
        return

    _kill_dashboard(workspace)
    if window is None:
        if tmux_has_session(slot.tmux_session):
            get_backend().kill_session(slot.tmux_session)
        ensure_slot(slot)
        if not detach:
            attach_slot(plan, slot.name)
        return

    if tmux_has_window(slot.tmux_session, window.name):
        get_backend().kill_window(f"{slot.tmux_session}:{window.name}")
    ensure_slot(slot)
    if not detach:
        attach_slot(plan, f"{slot.name}:{window.name}")


def open_dashboard(workspace: WorkspaceConfig, plan: WorkspacePlan) -> None:
    """Open a tiled tmux dashboard showing all slots."""
    if not get_backend().available():
        raise RuntimeError("tmux is required for workspace dashboard")

    apply_workspace(plan, detach=True)

    dashboard = _dashboard_session_name(workspace)
    if tmux_has_session(dashboard):
        get_backend().attach_session(dashboard)
        return

    slots = plan.slots
    if not slots:
        raise RuntimeError("no slots configured")
    layout = _dashboard_layout(workspace, len(slots))

    first = slots[0].tmux_session
    get_backend().create_session(dashboard, window_name="grid", command=tmux_attach_shell_command(first))

    for slot in slots[1:]:
        get_backend().split_window(f"{dashboard}:grid", tmux_attach_shell_command(slot.tmux_session))

    get_backend().select_layout(f"{dashboard}:grid", layout)

    get_backend().attach_session(dashboard)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def _list_window_names(session: str) -> set[str]:
    """Return the set of window names inside a tmux session.

    Queries tmux once per session instead of once per window.
    """
    try:
        import subprocess

        result = subprocess.run(
            ["tmux", "list-windows", "-t", session, "-F", "#{window_name}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if result.returncode != 0:
            return set()
        return set(result.stdout.splitlines())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return set()


def build_status_data(
    workspace: WorkspaceConfig, plan: WorkspacePlan
) -> dict:
    """Return structured status data without formatting.

    This separates the *query* phase (talking to tmux) from the
    *presentation* phase so that callers can render the data however
    they wish (plain text, JSON, HTML, etc.).
    """
    slots: list[dict] = []
    for slot in plan.slots:
        running = tmux_has_session(slot.tmux_session)
        present_windows = _list_window_names(slot.tmux_session) if running else set()
        windows: list[dict] = []
        for window in slot.windows:
            windows.append(
                {
                    "name": window.name,
                    "agent": window.agent,
                    "session_id": window.resolved_session_id,
                    "label": window.resolved_label,
                    "present": window.name in present_windows,
                }
            )
        slots.append(
            {
                "name": slot.name,
                "backend": slot.backend,
                "session": slot.tmux_session,
                "running": running,
                "windows": windows,
            }
        )
    return {"project": workspace.project, "root": workspace.root, "slots": slots}


def format_status(workspace: WorkspaceConfig, plan: WorkspacePlan) -> str:
    """Format workspace status as plain text."""
    data = build_status_data(workspace, plan)
    lines = [f"workspace {data['project']} @ {data['root']}"]
    for slot in data["slots"]:
        status = "running" if slot["running"] else "stopped"
        lines.append(
            f"- {slot['name']} [{slot['backend']}] session={slot['session']} status={status}"
        )
        for window in slot["windows"]:
            session_id = window.get("session_id") or "-"
            label = window.get("label") or "-"
            agent = window.get("agent") or "command"
            window_status = "present" if window.get("present") else "missing"
            lines.append(
                f"  - {window['name']}: agent={agent} "
                f"window={window_status} session_id={session_id} label={label}"
            )
    return "\n".join(lines)
