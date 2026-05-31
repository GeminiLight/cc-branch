"""Launch specification fingerprinting."""

from __future__ import annotations

import hashlib
import json

from ...models import SlotPlan, WindowPlan, WorkspaceConfig
from .models import LAUNCH_SPEC_VERSION


def agent_spec_dict(workspace: WorkspaceConfig, agent_name: str | None) -> dict:
    """Return stable agent fields that affect launch behavior."""
    if not agent_name:
        return {}
    spec = workspace.get_agent(agent_name)
    if spec is None:
        return {}
    return {
        "command": spec.command,
        "resume_mode": spec.resume_mode,
        "resume_template": spec.resume_template,
        "create_mode": spec.create_mode,
        "create_template": spec.create_template,
        "label_template": spec.label_template,
        "label_mode": spec.label_mode,
        "rename_template": spec.rename_template,
    }


def window_launch_spec(workspace: WorkspaceConfig, slot: SlotPlan, window: WindowPlan) -> dict:
    """Return the normalized desired launch spec for fingerprinting."""
    return {
        "version": LAUNCH_SPEC_VERSION,
        "project": workspace.project,
        "runtime": slot.runtime,
        "slot": slot.name,
        "window": window.name,
        "tmux_session": slot.tmux_session,
        "cwd": window.cwd,
        "env": {key: str(value) for key, value in sorted((window.env or {}).items())},
        "agent": window.agent,
        "agent_spec": agent_spec_dict(workspace, window.agent),
        "command": window.launch_command,
        "post_launch_commands": list(window.post_launch_commands),
        "session_id": window.resolved_session_id,
        "label": window.resolved_label,
        "opener": window.opener or slot.opener,
    }


def fingerprint_launch_spec(spec: dict) -> str:
    """Return a stable SHA-256 fingerprint for a launch spec."""
    payload = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def desired_fingerprint(workspace: WorkspaceConfig, slot: SlotPlan, window: WindowPlan) -> str:
    """Return the desired launch fingerprint for a planned window."""
    return fingerprint_launch_spec(window_launch_spec(workspace, slot, window))
