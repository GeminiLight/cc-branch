"""CLI facade.

The package keeps parser/help/command handlers split by responsibility while
preserving the historical ``cc_branch.cli`` import and patch surface.
"""

from __future__ import annotations

from pathlib import Path

from . import help as _help_module
from .commands.serve import is_loopback_host as _is_loopback_host
from .constants import PRIMARY_COMMAND, SHORT_ALIAS, console
from .dispatch import main, main_impl as _main_impl
from .errors import format_file_not_found as _format_file_not_found
from .errors import print_cli_error as _print_cli_error
from .output import output_format as _output_format
from .output import should_write_generated_state as _should_write_generated_state
from .parser import build_parser
from .targets import print_targets_help as _print_targets_help

from ..application.config_workflows import initialize_minimal_workspace
from ..application.config_workflows import initialize_workspace_from_environment
from ..application.config_workflows import inspect_workspace_environment
from ..application.config_workflows import profile_options
from ..application.diagnostics import get_doctor_report, render_report
from ..application.workspace_actions import attach_workspace as attach_workspace_action
from ..application.workspace_actions import launch_workspace as launch_workspace_action
from ..application.workspace_actions import open_dashboard_workspace as open_dashboard_workspace_action
from ..application.workspace_actions import open_workspace as open_workspace_action
from ..application.workspace_actions import restart_workspace as restart_workspace_action
from ..application.workspace_actions import start_workspace as start_workspace_action
from ..application.workspace_actions import stop_workspace as stop_workspace_action
from ..application.workspace_actions import sync_workspace
from ..application.workspace_status import build_workspace_status
from ..config import resolve_config_path
from ..context import WorkspaceContext
from ..planner import format_plan
from ..runtime.sessions import inspect_session, list_sessions, prune_sessions, restore_session


def print_help() -> None:
    """Render top-level help using the current facade console."""
    _help_module.console = console
    _help_module.print_help()


def print_command_help(command: str) -> None:
    """Render command-specific help using the current facade console."""
    _help_module.console = console
    _help_module.print_command_help(command)


__all__ = [
    "PRIMARY_COMMAND",
    "SHORT_ALIAS",
    "Path",
    "WorkspaceContext",
    "attach_workspace_action",
    "build_parser",
    "build_workspace_status",
    "console",
    "format_plan",
    "get_doctor_report",
    "initialize_minimal_workspace",
    "initialize_workspace_from_environment",
    "inspect_session",
    "inspect_workspace_environment",
    "launch_workspace_action",
    "list_sessions",
    "main",
    "open_dashboard_workspace_action",
    "open_workspace_action",
    "print_command_help",
    "print_help",
    "profile_options",
    "prune_sessions",
    "render_report",
    "resolve_config_path",
    "restart_workspace_action",
    "restore_session",
    "start_workspace_action",
    "stop_workspace_action",
    "sync_workspace",
]
