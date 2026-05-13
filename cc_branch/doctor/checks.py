from __future__ import annotations

import re
from pathlib import Path

from ..models import DoctorReport, Issue, WorkspaceConfig, WorkspacePlan
from ..runtime import which
from ..runtime.capabilities import is_managed_runtime
from ..runtime.shells import tmux_install_hint
from .messages import _get_install_suggestion


def _duplicate_names(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        name = value.strip()
        if not name:
            continue
        if name in seen:
            duplicates.add(name)
        else:
            seen.add(name)
    return sorted(duplicates)


def _valid_env_key(key: str) -> bool:
    return re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key) is not None


def _build_tmux_issue() -> Issue | None:
    tmux_path = which("tmux")
    if tmux_path:
        return Issue("tmux_ok", "info", f"tmux: ok ({tmux_path})", target="tmux")
    return Issue(
        "missing_tmux",
        "error",
        "tmux is missing",
        target="tmux",
        context={"hint": tmux_install_hint()},
    )


def _build_agent_issues(workspace: WorkspaceConfig) -> list[Issue]:
    issues: list[Issue] = []
    referenced = {
        agent
        for slot in workspace.slots
        for agent in [
            slot.agent,
            *(window.agent for window in slot.windows),
        ]
        if agent
    }
    if not referenced:
        return issues

    for name in sorted(referenced):
        spec = workspace.agents.get(name)
        if spec is None:
            # Unknown references are reported with window-level context.
            continue
        command = spec.command or name
        command_binary = command.split()[0]
        resolved = which(command_binary)
        if resolved:
            issues.append(
                Issue("agent_ok", "info", f"{name}: ok ({command})", target=f"agent:{name}")
            )
        else:
            issues.append(
                Issue(
                    "missing_command",
                    "error",
                    f"Agent '{name}' command not found: {command}",
                    target=f"agent:{name}",
                    context={"command": command, "hint": _get_install_suggestion(name, command)},
                )
            )
    return issues


def _build_slot_issues(plan: WorkspacePlan) -> list[Issue]:
    issues: list[Issue] = []
    duplicate_slots = _duplicate_names([slot.name for slot in plan.slots])
    for name in duplicate_slots:
        issues.append(
            Issue(
                "duplicate_slot",
                "error",
                f"Duplicate slot '{name}'",
                target=f"slot:{name}",
                context={"slot": name},
            )
        )

    seen_sessions: set[str] = set()
    for slot in plan.slots:
        if not is_managed_runtime(slot.runtime):
            continue
        if slot.tmux_session in seen_sessions:
            issues.append(
                Issue(
                    "duplicate_tmux_session",
                    "error",
                    f"Duplicate tmux session '{slot.tmux_session}'",
                    target=f"slot:{slot.name}",
                    context={"session": slot.tmux_session, "slot": slot.name},
                )
            )
        else:
            seen_sessions.add(slot.tmux_session)

        duplicate_windows = _duplicate_names([w.name for w in slot.windows])
        for name in duplicate_windows:
            issues.append(
                Issue(
                    "duplicate_window",
                    "error",
                    f"Duplicate window '{name}' in slot '{slot.name}'",
                    target=f"slot:{slot.name}",
                    context={"slot": slot.name, "window": name},
                )
            )
    return issues


def _build_window_issues(plan: WorkspacePlan) -> list[Issue]:
    issues: list[Issue] = []
    # Cache repeated filesystem lookups across windows
    command_cache: dict[str, str | None] = {}
    cwd_cache: dict[str, bool] = {}

    for slot in plan.slots:
        for window in slot.windows:
            target = f"{slot.name}.{window.name}"
            ctx: dict = {"slot": slot.name, "window": window.name}

            if window.agent and not window.agent_declared:
                issues.append(
                    Issue(
                        "unknown_agent",
                        "error",
                        f"Unknown agent '{window.agent}'",
                        target=target,
                        context={**ctx, "agent": window.agent},
                    )
                )

            if (
                window.resume_mode != "none"
                and not window.resolved_session_id
                and window.create_mode == "none"
            ):
                issues.append(
                    Issue(
                        "missing_session_id",
                        "error",
                        "Window requires a session_id for resume but has none",
                        target=target,
                        context=ctx,
                        fixable=True,
                    )
                )

            if window.command_binary:
                path = command_cache.get(window.command_binary)
                if path is None and window.command_binary not in command_cache:
                    path = which(window.command_binary)
                    command_cache[window.command_binary] = path
                if path is None:
                    issues.append(
                        Issue(
                            "missing_command",
                            "error",
                            f"Command not found: {window.command_binary}",
                            target=target,
                            context={**ctx, "command": window.command_binary},
                        )
                    )

            invalid_env_keys = sorted(key for key in window.env if not _valid_env_key(key))
            for key in invalid_env_keys:
                issues.append(
                    Issue(
                        "invalid_env_key",
                        "error",
                        f"Invalid environment variable name: {key}",
                        target=target,
                        context={**ctx, "key": key},
                    )
                )

            cwd_exists = cwd_cache.get(window.cwd)
            if cwd_exists is None:
                cwd_exists = Path(window.cwd).exists()
                cwd_cache[window.cwd] = cwd_exists
            if not cwd_exists:
                issues.append(
                    Issue(
                        "missing_cwd",
                        "error",
                        f"Working directory does not exist: {window.cwd}",
                        target=target,
                        context={**ctx, "cwd": window.cwd},
                        fixable=True,
                    )
                )

            if not window.launch_command:
                issues.append(
                    Issue(
                        "missing_launch_command",
                        "error",
                        "Window has no launch command",
                        target=target,
                        context=ctx,
                    )
                )
    return issues


# ---------------------------------------------------------------------------
# Structured report builder
# ---------------------------------------------------------------------------


def collect_doctor_report(workspace: WorkspaceConfig, plan: WorkspacePlan) -> DoctorReport:
    """Build a structured doctor report."""
    issues: list[Issue] = []

    tmux_issue = _build_tmux_issue() if any(is_managed_runtime(slot.runtime) for slot in plan.slots) else None
    if tmux_issue:
        issues.append(tmux_issue)

    issues.extend(_build_agent_issues(workspace))
    issues.extend(_build_slot_issues(plan))
    issues.extend(_build_window_issues(plan))

    return DoctorReport(project=workspace.project, issues=issues)
