"""Session management for cc-branch.

Treats sessions as first-class objects that can be listed, inspected,
pruned, and restored independently of the current runtime state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import WorkspaceConfig, WorkspacePlan, WorkspaceState
from .planner import session_key
from .runtime import tmux_has_session, tmux_has_window
from .targets import target_key


@dataclass
class SessionInfo:
    """A single session as seen by the user."""

    key: str
    slot: str
    window: str
    agent: str | None
    session_id: str | None
    label: str | None
    status: Literal["running", "stopped", "orphaned"]
    launch_command: str | None = None


def list_sessions(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    state: WorkspaceState,
) -> list[SessionInfo]:
    """List all sessions known to the workspace.

    A session is "running" if its tmux window exists, "stopped" if the
    slot session exists but the window does not, and "orphaned" if the
    slot session does not exist at all.
    """
    sessions: list[SessionInfo] = []

    # Build a lookup from plan windows to their launch commands
    plan_windows: dict[str, str | None] = {}
    for slot in plan.slots:
        for window in slot.windows:
            key = session_key(slot.name, window.name)
            plan_windows[key] = window.launch_command

    # Cache session existence per slot to avoid redundant subprocess calls
    session_exists_cache: dict[str, bool] = {}

    def _session_exists(slot_plan: WorkspacePlan) -> bool:
        name = slot_plan.tmux_session
        if name not in session_exists_cache:
            session_exists_cache[name] = tmux_has_session(name)
        return session_exists_cache[name]

    # Gather from state
    for key, entry in state.windows.items():
        slot_name = entry.slot if entry.slot else (key.split(".")[0] if "." in key else "")
        window_name = entry.window if entry.window else (key.split(".")[1] if "." in key else "")

        # Find the slot in the plan to check tmux status
        slot_plan = plan.get_slot(slot_name)
        if slot_plan is None:
            status: Literal["running", "stopped", "orphaned"] = "orphaned"
        else:
            exists = _session_exists(slot_plan)
            if not exists:
                status = "orphaned"
            elif tmux_has_window(slot_plan.tmux_session, window_name):
                status = "running"
            else:
                status = "stopped"

        sessions.append(
            SessionInfo(
                key=key,
                slot=slot_name,
                window=window_name,
                agent=entry.agent,
                session_id=entry.session_id,
                label=entry.label,
                status=status,
                launch_command=plan_windows.get(key),
            )
        )

    # Also include plan windows that have no state entry yet
    state_keys = set(state.windows.keys())
    for slot in plan.slots:
        for window in slot.windows:
            key = session_key(slot.name, window.name)
            if key in state_keys:
                continue
            exists = _session_exists(slot)
            if not exists:
                status = "orphaned"
            elif tmux_has_window(slot.tmux_session, window.name):
                status = "running"
            else:
                status = "stopped"
            sessions.append(
                SessionInfo(
                    key=key,
                    slot=slot.name,
                    window=window.name,
                    agent=window.agent,
                    session_id=window.resolved_session_id,
                    label=window.resolved_label,
                    status=status,
                    launch_command=window.launch_command,
                )
            )

    return sorted(sessions, key=lambda s: (s.slot, s.window))


def inspect_session(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    state: WorkspaceState,
    key: str,
) -> SessionInfo | None:
    """Return detailed info for a single session, or None if not found."""
    key = target_key(key)
    slot_name, _, window_name = key.partition(".")
    slot_plan = plan.get_slot(slot_name)
    if slot_plan is None:
        return None

    # Check if the key exists in state
    entry = state.get_window(key)
    if entry is not None:
        session_exists = tmux_has_session(slot_plan.tmux_session)
        if not session_exists:
            status: Literal["running", "stopped", "orphaned"] = "orphaned"
        elif tmux_has_window(slot_plan.tmux_session, window_name):
            status = "running"
        else:
            status = "stopped"
        return SessionInfo(
            key=key,
            slot=slot_name,
            window=window_name,
            agent=entry.agent,
            session_id=entry.session_id,
            label=entry.label,
            status=status,
            launch_command=None,
        )

    # Check if the window exists in the plan but not in state
    for w in slot_plan.windows:
        if w.name == window_name:
            session_exists = tmux_has_session(slot_plan.tmux_session)
            if not session_exists:
                status = "orphaned"
            elif tmux_has_window(slot_plan.tmux_session, window_name):
                status = "running"
            else:
                status = "stopped"
            return SessionInfo(
                key=key,
                slot=slot_name,
                window=window_name,
                agent=w.agent,
                session_id=w.resolved_session_id,
                label=w.resolved_label,
                status=status,
                launch_command=w.launch_command,
            )

    return None


def prune_sessions(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    state: WorkspaceState,
    dry_run: bool = False,
) -> list[str]:
    """Remove orphaned session entries from *state*.

    Returns the list of keys that were (or would be) removed.
    """
    removed: list[str] = []
    keys_to_remove: list[str] = []

    for key, entry in list(state.windows.items()):
        slot_name = entry.slot or key.split(".")[0] if "." in key else ""
        slot_plan = plan.get_slot(slot_name)
        if slot_plan is None:
            keys_to_remove.append(key)
            removed.append(key)
            continue
        if not tmux_has_session(slot_plan.tmux_session):
            keys_to_remove.append(key)
            removed.append(key)

    if not dry_run:
        for key in keys_to_remove:
            del state.windows[key]

    return removed


def restore_session(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    state: WorkspaceState,
    key: str,
) -> str | None:
    """Generate a shell command that restores the session *key*.

    Returns the command string, or None if the session cannot be restored
    (e.g. missing session_id, unknown agent, or window not found in plan).
    """
    # Find the window plan
    key = target_key(key)
    slot_name, _, window_name = key.partition(".")
    slot_plan = plan.get_slot(slot_name)
    if slot_plan is None:
        return None

    window_plan = None
    for w in slot_plan.windows:
        if w.name == window_name:
            window_plan = w
            break
    if window_plan is None:
        return None

    # Prefer the launch_command from the plan (already includes resume logic)
    if window_plan.launch_command:
        return window_plan.launch_command

    return None
