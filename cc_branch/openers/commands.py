"""Command and shell rendering helpers for opener intents."""

from __future__ import annotations

import os
import shlex
from pathlib import Path

from .types import OpenIntent, OpenerError, OpenerInfo


def _validate_capability(info: OpenerInfo, intent: OpenIntent) -> None:
    required = {
        "workspace_dashboard": "dashboard",
        "attach_target": "attach_target",
        "project_folder": "open_project",
    }[intent.kind]
    if required not in info.capabilities:
        raise OpenerError(
            f"Opener {info.id} does not support {intent.kind}. "
            "Use a compatible opener or choose another intent."
        )
    if intent.kind == "attach_target" and not intent.target:
        raise OpenerError("attach_target requires a target")


def _intent_command(cli: str, intent: OpenIntent) -> str:
    if intent.kind == "workspace_dashboard":
        return f"{cli} dashboard"
    if intent.kind == "attach_target":
        if not intent.target:
            raise OpenerError("attach_target requires a target")
        return f"{cli} attach {_argument_quote(intent.target)}"
    raise OpenerError(f"Intent {intent.kind} does not produce a shell command")


def _intent_title(intent: OpenIntent) -> str:
    if intent.kind == "workspace_dashboard":
        return "CC Branch Dashboard"
    if intent.target:
        return f"CC Branch {intent.target}"
    return "CC Branch"


def _argument_quote(value: str) -> str:
    if os.name == "nt":
        return _powershell_single_quote(value)
    return shlex.quote(value)


def _powershell_single_quote(value: str) -> str:
    """Return *value* as a PowerShell single-quoted string literal."""
    return "'" + value.replace("'", "''") + "'"


def _shell_command(cwd: Path, command: str) -> str:
    return f"cd {shlex.quote(str(cwd))} && {command}"


def _project_shell_command() -> str:
    return ":"
