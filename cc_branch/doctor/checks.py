from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path
from typing import Callable

from ..models import DoctorReport, Issue, WorkspaceConfig, WorkspacePlan, WorkspaceState
from ..models.config import RemoteConfig
from ..planner.remote import effective_remote
from ..runtime import which
from ..runtime.capabilities import is_managed_runtime
from ..runtime.shells import tmux_install_hint
from ..targets import reserved_target_separators
from ..text import count_label
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


def _is_default_shell_placeholder(command_binary: str) -> bool:
    return command_binary in {"$SHELL", "${SHELL}"}


def _build_agent_issues(workspace: WorkspaceConfig) -> list[Issue]:
    issues: list[Issue] = []
    referenced: set[str] = set()
    for slot in workspace.slots:
        if slot.agent and slot.remote is None:
            referenced.add(slot.agent)
        for window in slot.windows:
            if window.agent and effective_remote(slot.remote, window.remote) is None:
                referenced.add(window.agent)
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
        slot_separators = reserved_target_separators(slot.name)
        if slot_separators:
            issues.append(
                Issue(
                    "reserved_name_separator",
                    "error",
                    f"Slot name cannot contain ':' or '.': {slot.name}",
                    target=f"slot:{slot.name}",
                    context={
                        "scope": "slot",
                        "name": slot.name,
                        "separators": slot_separators,
                    },
                )
            )

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
        for window in slot.windows:
            window_separators = reserved_target_separators(window.name)
            if window_separators:
                issues.append(
                    Issue(
                        "reserved_name_separator",
                        "error",
                        f"Window name cannot contain ':' or '.': {window.name}",
                        target=f"{slot.name}.{window.name}",
                        context={
                            "scope": "window",
                            "slot": slot.name,
                            "name": window.name,
                            "window": window.name,
                            "separators": window_separators,
                        },
                    )
                )

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
                if _is_default_shell_placeholder(window.command_binary):
                    continue
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


RemoteProbe = Callable[[tuple[RemoteConfig, tuple[str, ...]]], dict]


def _remote_key(remote: RemoteConfig) -> tuple:
    return (
        remote.host,
        remote.user,
        remote.port,
        remote.cwd,
        tuple(remote.args),
        tuple(sorted(remote.options.items())),
    )


def _ssh_command(remote: RemoteConfig, remote_command: str) -> list[str]:
    target = remote.target()
    command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8"]
    if remote.port is not None:
        command.extend(["-p", str(remote.port)])
    for key, value in sorted(remote.options.items()):
        option = str(key) if value is None else f"{key}={value}"
        command.extend(["-o", option])
    command.extend(remote.args)
    command.extend([target, remote_command])
    return command


def _probe_remote(command: tuple[RemoteConfig, tuple[str, ...]], *, timeout: int = 8) -> dict:
    remote, command_binaries = command
    cwd = remote.cwd or "."
    checks = [
        f"if test -d {shlex.quote(cwd)}; then echo cwd=ok; else echo cwd=missing; fi",
        "if command -v tmux >/dev/null 2>&1; then echo tmux=ok; else echo tmux=missing; fi",
    ]
    for binary in command_binaries:
        safe_binary = shlex.quote(binary)
        safe_label = binary.replace("\n", " ")
        checks.append(
            f"if command -v {safe_binary} >/dev/null 2>&1; "
            f"then echo cmd:{shlex.quote(safe_label)}=ok; "
            f"else echo cmd:{shlex.quote(safe_label)}=missing; fi"
        )
    result = subprocess.run(
        _ssh_command(remote, " && ".join(checks)),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        return {
            "cwd": None,
            "tmux": None,
            "commands": {},
            "error": result.stderr.strip() or result.stdout.strip() or "SSH remote check failed",
        }
    payload = {"cwd": None, "tmux": None, "commands": {}, "error": None}
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if line == "cwd=ok":
            payload["cwd"] = True
        elif line == "cwd=missing":
            payload["cwd"] = False
        elif line == "tmux=ok":
            payload["tmux"] = True
        elif line == "tmux=missing":
            payload["tmux"] = False
        elif line.startswith("cmd:") and "=" in line:
            name, value = line[4:].rsplit("=", 1)
            payload["commands"][name] = value == "ok"
    return payload


def _remote_command_binary(workspace: WorkspaceConfig, window) -> str:
    if window.agent and window.agent in workspace.agents:
        command = workspace.agents[window.agent].command or window.agent
        return command.split()[0]
    return window.command_binary


def _build_remote_issues(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    *,
    remote_probe: RemoteProbe | None,
) -> list[Issue]:
    if remote_probe is None:
        return []

    remotes: dict[tuple, tuple[RemoteConfig, set[str]]] = {}
    for slot in plan.slots:
        for window in slot.windows:
            remote = window.remote
            if remote is None:
                continue
            entry = remotes.setdefault(_remote_key(remote), (remote, set()))
            command_binary = _remote_command_binary(workspace, window)
            if command_binary and command_binary != "ssh" and not _is_default_shell_placeholder(command_binary):
                entry[1].add(command_binary)

    issues: list[Issue] = []
    for remote, command_binaries in remotes.values():
        target = f"remote:{remote.target()}"
        context = {
            "host": remote.host,
            "target": remote.target(),
            "cwd": remote.cwd,
        }
        try:
            result = remote_probe((remote, tuple(sorted(command_binaries))))
        except subprocess.TimeoutExpired as error:
            result = {"cwd": None, "tmux": None, "commands": {}, "error": str(error)}
        except OSError as error:
            result = {"cwd": None, "tmux": None, "commands": {}, "error": str(error)}

        if result.get("error"):
            issues.append(
                Issue(
                    "remote_unreachable",
                    "error",
                    f"Cannot inspect SSH target {remote.target()}: {result['error']}",
                    target=target,
                    context={**context, "error": result["error"]},
                )
            )
            continue
        if result.get("cwd") is False:
            issues.append(
                Issue(
                    "remote_missing_cwd",
                    "error",
                    f"Remote working directory does not exist on {remote.target()}: {remote.cwd}",
                    target=target,
                    context=context,
                    fixable=True,
                )
            )
        if result.get("tmux") is False:
            issues.append(
                Issue(
                    "remote_missing_tmux",
                    "error",
                    f"tmux is missing on SSH target {remote.target()}",
                    target=target,
                    context=context,
                )
            )
        commands = result.get("commands") or {}
        for command, ok in sorted(commands.items()):
            if ok is False:
                issues.append(
                    Issue(
                        "remote_missing_command",
                        "error",
                        f"Remote command not found on {remote.target()}: {command}",
                        target=target,
                        context={**context, "command": command},
                    )
                )
    return issues


def _build_state_issues(plan: WorkspacePlan, state: WorkspaceState | None) -> list[Issue]:
    if state is None:
        return []

    plan_keys = {window.key for slot in plan.slots for window in slot.windows}
    stale_entries = [
        {
            "key": key,
            "slot": entry.slot,
            "window": entry.window,
            "agent": entry.agent,
            "session_id": entry.session_id,
            "label": entry.label,
            "tmux_session": entry.tmux_session,
        }
        for key, entry in sorted(state.windows.items())
        if key not in plan_keys
    ]
    if not stale_entries:
        return []
    stale_count = len(stale_entries)
    return [
        Issue(
            "orphaned_state",
            "warning",
            f"{count_label(stale_count, 'stale local session record')} no longer "
            f"{'matches' if stale_count == 1 else 'match'} the current config",
            target="state",
            context={
                "count": stale_count,
                "keys": [entry["key"] for entry in stale_entries],
                "entries": stale_entries,
            },
            fixable=True,
        )
    ]


# ---------------------------------------------------------------------------
# Structured report builder
# ---------------------------------------------------------------------------


def collect_doctor_report(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    state: WorkspaceState | None = None,
    *,
    remote_probe: RemoteProbe | None = _probe_remote,
) -> DoctorReport:
    """Build a structured doctor report."""
    issues: list[Issue] = []

    tmux_issue = _build_tmux_issue() if any(is_managed_runtime(slot.runtime) for slot in plan.slots) else None
    if tmux_issue:
        issues.append(tmux_issue)

    issues.extend(_build_agent_issues(workspace))
    issues.extend(_build_slot_issues(plan))
    issues.extend(_build_window_issues(plan))
    issues.extend(_build_remote_issues(workspace, plan, remote_probe=remote_probe))
    issues.extend(_build_state_issues(plan, state))

    return DoctorReport(project=workspace.project, issues=issues)
