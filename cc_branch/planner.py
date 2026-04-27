"""Workspace planner: turns config + state into an executable plan.

Public API operates on typed models.
"""

from __future__ import annotations

import re
import shlex
import uuid
from pathlib import Path

from .adapters import get_adapter
from .models import (
    AgentSpec,
    SlotConfig,
    SlotPlan,
    WindowConfig,
    WindowPlan,
    WindowState,
    WorkspaceConfig,
    WorkspacePlan,
    WorkspaceState,
)
from .templates import render_template


def session_key(slot_name: str, window_name: str) -> str:
    """Return the canonical state key for a window."""
    return f"{slot_name}.{window_name}"


def _safe_name(value: str) -> str:
    """Sanitise a string for use in tmux session names."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "workspace"


def tmux_session_name(project: str, slot_name: str) -> str:
    """Generate the tmux session name for a slot."""
    return f"{_safe_name(project)}-{_safe_name(slot_name)}"


def _apply_env(command: str, env: dict) -> str:
    """Prefix *command* with ``env KEY=val ...`` when env vars are present."""
    if not command or not env:
        return command
    assignments = " ".join(
        f"{key}={shlex.quote(str(value))}"
        for key, value in sorted(env.items())
        if value is not None
    )
    if not assignments:
        return command
    return f"env {assignments} {command}"


def _resolve_slot_cwd(workspace_root: str, slot: SlotConfig) -> Path:
    """Resolve a slot's working directory."""
    return (Path(workspace_root) / slot.cwd).resolve()


def _resolve_window_cwd(workspace_root: str, slot: SlotConfig, window: WindowConfig) -> str:
    """Resolve a window's working directory."""
    if not window.cwd:
        return str(_resolve_slot_cwd(workspace_root, slot))
    window_path = Path(window.cwd)
    if window_path.is_absolute():
        return str(window_path.resolve())
    base_dir = _resolve_slot_cwd(workspace_root, slot) if slot.cwd else Path(workspace_root)
    return str((base_dir / window_path).resolve())


def _slot_windows(slot: SlotConfig) -> list[WindowConfig]:
    """Normalise a slot's windows.

    Shell slots are normalised into a single synthetic ``main`` window.
    """
    if slot.backend == "shell":
        return [
            WindowConfig(
                name=slot.window_name or "main",
                command=slot.command,
                agent=slot.agent,
                cwd=slot.cwd,
                env=slot.env,
                session_id=slot.session_id,
                label=slot.label,
            )
        ]
    return list(slot.windows)


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
        "window": window_name,
        "session_id": session_id or "",
    }
    return (
        window.label
        or (state_entry.label if state_entry else None)
        or render_template(window.label_template, context)
        or render_template(agent.label_template if agent else None, context)
        or ""
    )


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
    session_id = window.session_id or (state_entry.session_id if state_entry else None)

    cwd = _resolve_window_cwd(workspace.root, slot, window)
    label = _build_label(workspace, slot_name, window_name, window, agent, state_entry, session_id)

    bootstrapped = False
    create_mode = _resolve_agent_field(window, agent, "create_mode") or "none"
    if not session_id and bootstrap_missing and create_mode == "generated_uuid":
        session_id = str(uuid.uuid4())
        bootstrapped = True
        label = label or _build_label(
            workspace, slot_name, window_name, window, agent, state_entry, session_id
        )

    context = {
        "project": workspace.project,
        "slot": slot_name,
        "window": window_name,
        "session_id": session_id or "",
        "label": label or "",
    }

    env = {**dict(slot.env or {}), **dict(window.env or {})}
    launch_command = window.command or ""
    post_launch_commands: list[str] = []
    command_binary = shlex.split(launch_command)[0] if launch_command else ""
    has_command_override = bool(window.command)

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
    resume_mode = _resolve_agent_field(window, agent, "resume_mode") or "none"
    agent_declared = not agent_name or agent_name in workspace.agents

    return WindowPlan(
        name=window_name,
        key=key,
        agent=agent_name,
        backend=slot.backend,
        cwd=cwd,
        env=env,
        resolved_session_id=session_id,
        resolved_label=label,
        launch_command=launch_command,
        command_binary=command_binary,
        post_launch_commands=post_launch_commands,
        bootstrapped=bootstrapped,
        resume_mode=resume_mode,
        create_mode=create_mode,
        agent_declared=agent_declared,
    )


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
            backend=slot.backend,
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
        slots=plan_slots,
        state_updates=state_updates,
    )


def format_plan(plan: WorkspacePlan) -> str:
    """Render a plan as human-readable text."""
    lines = [f"workspace {plan.project} plan"]
    for slot in plan.slots:
        lines.append(f"- slot {slot.name} [{slot.backend}] -> {slot.tmux_session}")
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
