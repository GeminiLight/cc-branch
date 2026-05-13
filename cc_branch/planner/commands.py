from __future__ import annotations

import shlex
import uuid

from ..adapters import get_adapter
from ..models import (
    AgentSpec,
    SlotConfig,
    WindowConfig,
    WindowPlan,
    WindowState,
    WorkspaceConfig,
    WorkspaceState,
)
from ..templates import render_template
from .naming import session_key
from .paths import _apply_env, _resolve_window_cwd

SESSION_AUTO = "auto"
SESSION_FRESH = "fresh"


def _resolve_agent_field(window: WindowConfig, agent: AgentSpec | None, field: str) -> str | None:
    """Return the effective value for an agent field, respecting window-level overrides."""
    window_val = getattr(window, field)
    if window_val is not None:
        return window_val
    if agent is not None:
        return getattr(agent, field)
    return None


def _build_label(
    workspace: WorkspaceConfig,
    slot_name: str,
    window_name: str,
    window: WindowConfig,
    agent: AgentSpec | None,
    state_entry: WindowState | None,
    session_id: str | None,
) -> str:
    """Resolve the effective label for a window."""
    context = {
        "project": workspace.project,
        "slot": slot_name,
        "tab": slot_name,
        "window": window_name,
        "pane": window_name,
        "session_id": session_id or "",
    }
    return (
        window.label
        or (state_entry.label if state_entry else None)
        or render_template(window.label_template, context)
        or render_template(agent.label_template if agent else None, context)
        or ""
    )


def _resolve_session_id(window: WindowConfig, state_entry: WindowState | None) -> tuple[str | None, str]:
    """Resolve config-level session intent into a concrete session id.

    ``session`` is the public config field:
    - omitted / ``auto``: use explicit legacy id, then bound state id
    - ``fresh``: intentionally start without a bound id
    - any other string: treat as the real agent session id
    """
    raw = (window.session or "").strip()
    if raw == SESSION_FRESH:
        return None, SESSION_FRESH
    if raw and raw != SESSION_AUTO:
        return raw, "explicit"
    return window.session_id or (state_entry.session_id if state_entry else None), SESSION_AUTO


def _build_window_plan(
    workspace: WorkspaceConfig,
    slot: SlotConfig,
    window: WindowConfig,
    state: WorkspaceState,
    bootstrap_missing: bool,
) -> WindowPlan:
    """Build a typed :class:`WindowPlan` from config + state."""
    slot_name = slot.name
    window_name = window.name
    key = session_key(slot_name, window_name)
    state_entry = state.get_window(key)

    agent_name = window.agent
    agent = workspace.get_agent(agent_name)
    session_id, session_mode = _resolve_session_id(window, state_entry)
    has_command_override = bool(window.command)

    cwd = _resolve_window_cwd(workspace.root, slot, window)
    label = _build_label(workspace, slot_name, window_name, window, agent, state_entry, session_id)

    bootstrapped = False
    create_mode = (
        "none"
        if has_command_override or session_mode == SESSION_FRESH
        else _resolve_agent_field(window, agent, "create_mode") or "none"
    )
    if session_mode == SESSION_AUTO and not session_id and bootstrap_missing and create_mode == "generated_uuid":
        session_id = str(uuid.uuid4())
        bootstrapped = True
        label = label or _build_label(
            workspace, slot_name, window_name, window, agent, state_entry, session_id
        )

    context = {
        "project": workspace.project,
        "slot": slot_name,
        "tab": slot_name,
        "window": window_name,
        "pane": window_name,
        "session_id": session_id or "",
        "label": label or "",
    }

    env = {**dict(slot.env or {}), **dict(window.env or {})}
    launch_command = window.command or ""
    post_launch_commands: list[str] = []
    command_binary = shlex.split(launch_command)[0] if launch_command else ""

    if agent_name and not has_command_override:
        if agent is None:
            base_command = agent_name
            command_binary = shlex.split(base_command)[0] if base_command else ""
            launch_command = base_command
        else:
            base_command = agent.command or agent_name
            command_binary = shlex.split(base_command)[0] if base_command else ""
            adapter = get_adapter(agent)
            launch_command, post_cmds = adapter.build_launch_command(
                agent, context, session_id=session_id, bootstrapped=bootstrapped
            )
            post_launch_commands.extend(post_cmds)
            label_cmds = adapter.build_label_commands(agent, context, label=label)
            post_launch_commands.extend(label_cmds)

    launch_command = _apply_env(launch_command, env)
    resume_mode = (
        "none"
        if has_command_override or session_mode == SESSION_FRESH
        else _resolve_agent_field(window, agent, "resume_mode") or "none"
    )
    agent_declared = not agent_name or agent_name in workspace.agents

    return WindowPlan(
        name=window_name,
        key=key,
        agent=agent_name,
        runtime=slot.runtime,
        opener=slot.opener,
        cwd=cwd,
        env=env,
        resolved_session_id=session_id,
        resolved_label=label,
        launch_command=launch_command,
        command_binary=command_binary,
        post_launch_commands=post_launch_commands,
        bootstrapped=bootstrapped,
        session_mode=session_mode,
        resume_mode=resume_mode,
        create_mode=create_mode,
        agent_declared=agent_declared,
    )
