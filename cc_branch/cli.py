from __future__ import annotations

import argparse
import ipaddress
import json
import os
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .bootstrap import check_environment, initialize_workspace_files
from .config import init_workspace, load_workspace, resolve_config_path
from .constants import DEFAULT_CONFIG
from .context import WorkspaceContext
from .doctor import build_doctor_report
from .exceptions import CcbError
from .planner import format_plan, plan_workspace
from .runtime import (
    apply_workspace,
    attach_slot,
    format_status,
    open_dashboard,
    restart_workspace,
    stop_workspace,
)
from .sessions import inspect_session, list_sessions, prune_sessions, restore_session
from .shells import tmux_install_hint
from .state import load_state, merge_state, save_state

console = Console()
SHORT_ALIAS = "ccb"
PRIMARY_COMMAND = "cc-branch"


def _package_version() -> str:
    try:
        return version("cc-branch")
    except PackageNotFoundError:
        return "0.1.0"


def _is_loopback_host(host: str) -> bool:
    """Return True when host only exposes the server to the local machine."""
    normalized = host.strip().strip("[]").lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def print_help():
    """Display a beautiful help message using rich."""
    parser = build_parser()
    command_action = _subparser_action(parser)

    # Create title
    title = Text()
    title.append(SHORT_ALIAS, style="bold cyan")
    title.append(" - CC Branch", style="bold white")

    # Create description
    description = Text("Multi-agent workspace orchestrator for shell and tmux runtimes", style="dim")

    # Create commands table
    table = Table(show_header=True, header_style="bold magenta", border_style="blue", padding=(0, 2))
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    commands = [
        (name, subparser.description or "")
        for name, subparser in command_action.choices.items()
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    # Print everything
    console.print()
    console.print(Panel(title, border_style="cyan"))
    console.print()
    console.print(description)
    console.print()
    console.print(table)
    console.print()
    console.print(f"[dim]Usage:[/dim] [cyan]{SHORT_ALIAS}[/cyan] [yellow]<command>[/yellow] [dim][options][/dim]")
    console.print(
        f"[dim]For command-specific help:[/dim] [cyan]{SHORT_ALIAS}[/cyan] "
        f"[yellow]<command>[/yellow] [cyan]--help[/cyan]"
    )
    console.print(f"[dim]Also available as:[/dim] [cyan]{PRIMARY_COMMAND}[/cyan]")
    console.print()


def print_command_help(command: str):
    """Display help for a specific command."""
    parser = build_parser()
    command_parser = _parser_for_command(parser, command.split())
    if command_parser is None:
        console.print(f"[red]Unknown command: {command}[/red]")
        return

    # Title
    title = Text()
    title.append(f"{SHORT_ALIAS} ", style="bold cyan")
    title.append(command, style="bold yellow")

    console.print()
    console.print(Panel(title, border_style="cyan"))
    console.print()
    console.print(Text(command_parser.description or "", style="white"))
    console.print()
    usage = command_parser.format_usage().replace("usage: ", "").strip()
    console.print("[dim]Usage:[/dim]", usage)
    console.print()

    rows = _help_rows(command_parser)
    if rows:
        table = Table(show_header=True, header_style="bold magenta", border_style="blue", padding=(0, 2))
        table.add_column("Option", style="yellow", no_wrap=True)
        table.add_column("Description", style="white")

        for opt, desc in rows:
            table.add_row(opt, desc)

        console.print(table)
        console.print()

    examples = _HELP_EXAMPLES.get(command)
    if examples:
        console.print("[dim]Examples:[/dim]")
        for example in examples:
            console.print(f"  [cyan]{example}[/cyan]")
        console.print()


_HELP_EXAMPLES = {
    "attach": [f"{SHORT_ALIAS} attach dev", f"{SHORT_ALIAS} attach dev:planner"],
    "start": [f"{SHORT_ALIAS} start", f"{SHORT_ALIAS} start --detach", f"{SHORT_ALIAS} start --dashboard"],
    "sessions": [
        f"{SHORT_ALIAS} sessions list",
        f"{SHORT_ALIAS} sessions inspect dev:planner",
        f"{SHORT_ALIAS} sessions command dev:planner",
    ],
    "session": [
        f"{SHORT_ALIAS} session list",
        f"{SHORT_ALIAS} session inspect dev:planner",
        f"{SHORT_ALIAS} session command dev:planner",
    ],
}


def _subparser_action(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise RuntimeError("parser has no subcommands")


def _parser_for_command(
    parser: argparse.ArgumentParser, command_path: list[str]
) -> argparse.ArgumentParser | None:
    current = parser
    for part in command_path:
        action = _subparser_action(current)
        current = action.choices.get(part)
        if current is None:
            return None
    return current


def _help_rows(parser: argparse.ArgumentParser) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for action in parser._actions:
        if action.help == argparse.SUPPRESS:
            continue
        if isinstance(action, argparse._HelpAction):
            continue
        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                rows.append((name, subparser.description or ""))
            continue
        rows.append((_action_display(action), action.help or ""))
    return rows


def _action_display(action: argparse.Action) -> str:
    if action.option_strings:
        if action.nargs == 0:
            return ", ".join(action.option_strings)
        metavar = action.metavar or action.dest.upper()
        return ", ".join(f"{opt} {metavar}" for opt in action.option_strings)
    name = action.metavar or action.dest
    if action.nargs == "?":
        return f"[{name}]"
    return f"<{name}>"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage an agent workspace",
        prog=SHORT_ALIAS,
        add_help=False  # Disable default help to use custom help
    )
    parser.add_argument("-h", "--help", action="store_true", help="show this help message")
    parser.add_argument("--version", action="version", version=f"cc-branch {_package_version()}")
    parser.add_argument("--project", type=str, help="project directory containing .cc-branch.yaml")
    parser.add_argument("--config", type=str, help="path to .cc-branch.yaml")
    parser.add_argument("--state", type=str, help="path to .cc-branch.state.toml")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format for inspection commands",
    )
    parser.add_argument("--no-color", action="store_true", help="disable ANSI color output")
    parser.add_argument("--debug", action="store_true", help="show Python tracebacks")
    sub = parser.add_subparsers(dest="command")

    init_cmd = sub.add_parser(
        "init",
        help="create a starter workspace config",
        description="Create a starter workspace config",
        add_help=False,
    )
    init_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    init_cmd.add_argument("--force", action="store_true", help="overwrite existing config files")
    init_cmd.add_argument(
        "--bootstrap-sessions",
        action="store_true",
        help="compatibility flag; session metadata is bootstrapped automatically when agent CLIs are detected",
    )
    init_cmd.add_argument("--minimal", action="store_true", help="minimal init without environment checks")
    init_cmd.add_argument("--profile", type=str, default="solo-dev", help="profile template to use")

    plan_cmd = sub.add_parser(
        "plan",
        help="show the resolved launch plan",
        description="Show the resolved launch plan",
        add_help=False,
    )
    plan_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    plan_cmd.add_argument(
        "--bootstrap-if-missing",
        action="store_true",
        help="compatibility alias for --write-state; writes .cc-branch.state.toml",
    )
    plan_cmd.add_argument("--write-state", action="store_true", help="write missing generated state metadata")
    plan_cmd.add_argument("--json", action="store_true", help="alias for --format json")

    status_cmd = sub.add_parser(
        "status",
        help="show workspace status",
        description="Show workspace status",
        add_help=False,
    )
    status_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    status_cmd.add_argument(
        "--bootstrap-if-missing",
        action="store_true",
        help="compatibility alias for --write-state; writes .cc-branch.state.toml",
    )
    status_cmd.add_argument("--write-state", action="store_true", help="write missing generated state metadata")
    status_cmd.add_argument("--json", action="store_true", help="alias for --format json")

    def add_start_options(command: argparse.ArgumentParser) -> None:
        command.add_argument("-h", "--help", action="store_true", help="show this help message")
        command.add_argument(
            "--bootstrap-if-missing",
            action="store_true",
            help="compatibility alias for --prepare; writes .cc-branch.state.toml",
        )
        command.add_argument("--prepare", action="store_true", help="write missing generated state metadata before launch")
        command.add_argument("--detach", action="store_true", help="start sessions without attaching")
        command.add_argument("--dashboard", action="store_true", help="open the tiled dashboard after planning")

    start_cmd = sub.add_parser(
        "start",
        help="start the configured tmux workspace",
        description="Start the configured tmux workspace",
        add_help=False,
    )
    add_start_options(start_cmd)

    attach_cmd = sub.add_parser(
        "attach",
        help="attach to a slot or slot window",
        description="Attach to a slot or slot window",
        add_help=False,
    )
    attach_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    attach_cmd.add_argument("slot", nargs="?", metavar="slot[:window]", help="target such as dev or dev:planner")

    stop_cmd = sub.add_parser(
        "stop",
        help="stop the workspace, a slot, or a slot window",
        description="Stop the workspace, a slot, or a slot window",
        add_help=False,
    )
    stop_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    stop_cmd.add_argument("target", nargs="?", metavar="slot[:window]", help="optional target such as dev or dev:planner")

    restart_cmd = sub.add_parser(
        "restart",
        help="restart the workspace, a slot, or a slot window",
        description="Restart the workspace, a slot, or a slot window",
        add_help=False,
    )
    restart_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    restart_cmd.add_argument("target", nargs="?", metavar="slot[:window]", help="optional target such as dev or dev:planner")
    restart_cmd.add_argument(
        "--bootstrap-if-missing",
        action="store_true",
        help="compatibility alias for --prepare; writes .cc-branch.state.toml",
    )
    restart_cmd.add_argument("--prepare", action="store_true", help="write missing generated state metadata before restart")
    restart_cmd.add_argument("--detach", action="store_true", help="restart without attaching")

    doctor_cmd = sub.add_parser(
        "doctor",
        help="validate workspace dependencies and metadata",
        description="Validate workspace dependencies and metadata",
        add_help=False,
    )
    doctor_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    doctor_cmd.add_argument(
        "--bootstrap-if-missing",
        action="store_true",
        help="compatibility alias for --write-state; writes .cc-branch.state.toml",
    )
    doctor_cmd.add_argument("--write-state", action="store_true", help="write missing generated state metadata")
    doctor_cmd.add_argument("--fix", action="store_true", help="automatically fix simple issues")

    dashboard_cmd = sub.add_parser(
        "dashboard",
        help="open a tiled tmux dashboard for all slots",
        description="Open a tiled tmux dashboard for all slots",
        add_help=False,
    )
    dashboard_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    dashboard_cmd.add_argument(
        "--bootstrap-if-missing",
        action="store_true",
        help="compatibility alias for --prepare; writes .cc-branch.state.toml",
    )
    dashboard_cmd.add_argument("--prepare", action="store_true", help="write missing generated state metadata before opening")

    serve_cmd = sub.add_parser(
        "serve",
        help="start the web UI server",
        description="Start the Web UI server",
        add_help=False,
    )
    serve_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    serve_cmd.add_argument("--host", type=str, default="127.0.0.1", help="host to bind to")
    serve_cmd.add_argument("--port", type=int, default=8080, help="port to listen on")
    serve_cmd.add_argument(
        "--token",
        type=str,
        default=None,
        help="bearer token required for token-protected Web UI access; can also use CC_BRANCH_WEB_TOKEN",
    )

    _add_session_group(sub, "session", "manage saved agent session metadata")
    _add_session_group(sub, "sessions", "compatibility alias for session")
    _add_workspace_group(sub)
    _add_target_group(sub)
    _add_config_group(sub)
    _add_ui_group(sub)
    _add_state_group(sub)
    help_cmd = sub.add_parser(
        "help",
        help="show concept guides",
        description="Show concept guides",
        add_help=False,
    )
    help_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    help_cmd.add_argument("topic", nargs="?", choices=["targets"], help="guide topic")

    return parser


def _add_session_group(
    subparsers: argparse._SubParsersAction, name: str, description: str
) -> None:
    cmd = subparsers.add_parser(
        name,
        help=description,
        description=description.capitalize(),
        add_help=False,
    )
    cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    nested = cmd.add_subparsers(dest="sessions_command")
    nested.add_parser("list", help="list saved agent session entries", description="List saved agent session entries")

    inspect_cmd = nested.add_parser("inspect", help="inspect a saved session entry", description="Inspect a saved session entry")
    inspect_cmd.add_argument("key", metavar="slot[:window]", help="target such as dev:planner")

    prune_cmd = nested.add_parser("prune", help="remove orphaned session entries", description="Remove orphaned session entries")
    prune_cmd.add_argument("--dry-run", action="store_true", help="show what would be removed")

    command_cmd = nested.add_parser("command", help="print the launch command for a target", description="Print the launch command for a target")
    command_cmd.add_argument("key", metavar="slot[:window]", help="target such as dev:planner")

    restore_cmd = nested.add_parser("restore", help="compatibility alias for command", description="Compatibility alias for command")
    restore_cmd.add_argument("key", metavar="slot[:window]", help="target such as dev:planner")


def _add_workspace_group(subparsers: argparse._SubParsersAction) -> None:
    cmd = subparsers.add_parser(
        "workspace",
        help="workspace lifecycle commands",
        description="Workspace lifecycle commands",
        add_help=False,
    )
    cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    nested = cmd.add_subparsers(dest="workspace_command")
    init_cmd = nested.add_parser("init", help="alias for init", description="Alias for init")
    init_cmd.add_argument("--force", action="store_true", help="overwrite existing config files")
    init_cmd.add_argument(
        "--bootstrap-sessions",
        action="store_true",
        help="compatibility flag; session metadata is bootstrapped automatically when agent CLIs are detected",
    )
    init_cmd.add_argument("--minimal", action="store_true", help="minimal init without environment checks")
    init_cmd.add_argument("--profile", type=str, default="solo-dev", help="profile template to use")
    plan_cmd = nested.add_parser("plan", help="alias for plan", description="Alias for plan")
    plan_cmd.add_argument("--write-state", action="store_true", help="write missing generated state metadata")
    plan_cmd.add_argument("--bootstrap-if-missing", action="store_true", help="compatibility alias for --write-state")
    plan_cmd.add_argument("--json", action="store_true", help="alias for --format json")
    status_cmd = nested.add_parser("status", help="alias for status", description="Alias for status")
    status_cmd.add_argument("--write-state", action="store_true", help="write missing generated state metadata")
    status_cmd.add_argument("--bootstrap-if-missing", action="store_true", help="compatibility alias for --write-state")
    status_cmd.add_argument("--json", action="store_true", help="alias for --format json")
    def add_workspace_start_options(command: argparse.ArgumentParser) -> None:
        command.add_argument("--detach", action="store_true", help="start sessions without attaching")
        command.add_argument("--dashboard", action="store_true", help="open the tiled dashboard")
        command.add_argument("--prepare", action="store_true", help="write missing generated state metadata")
        command.add_argument("--bootstrap-if-missing", action="store_true", help="compatibility alias for --prepare")

    start_cmd = nested.add_parser("start", help="alias for start", description="Alias for start")
    add_workspace_start_options(start_cmd)
    nested.add_parser("down", help="alias for stop", description="Alias for stop")
    prepare_cmd = nested.add_parser("prepare", help="write missing state metadata", description="Write missing state metadata")
    prepare_cmd.add_argument("--dry-run", action="store_true", help="show changes without writing state")


def _add_target_group(subparsers: argparse._SubParsersAction) -> None:
    cmd = subparsers.add_parser(
        "target",
        help="target lifecycle commands",
        description="Target lifecycle commands",
        add_help=False,
    )
    cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    nested = cmd.add_subparsers(dest="target_command")
    attach_cmd = nested.add_parser("attach", help="alias for attach", description="Alias for attach")
    attach_cmd.add_argument("slot", metavar="slot[:window]", help="target such as dev or dev:planner")
    stop_cmd = nested.add_parser("stop", help="alias for stop", description="Alias for stop")
    stop_cmd.add_argument("target", nargs="?", metavar="slot[:window]", help="optional target such as dev or dev:planner")
    restart_cmd = nested.add_parser("restart", help="alias for restart", description="Alias for restart")
    restart_cmd.add_argument("target", nargs="?", metavar="slot[:window]", help="optional target such as dev or dev:planner")
    restart_cmd.add_argument("--detach", action="store_true", help="restart without attaching")
    restart_cmd.add_argument("--prepare", action="store_true", help="write missing generated state metadata")
    restart_cmd.add_argument("--bootstrap-if-missing", action="store_true", help="compatibility alias for --prepare")


def _add_config_group(subparsers: argparse._SubParsersAction) -> None:
    cmd = subparsers.add_parser(
        "config",
        help="config validation and diagnostics",
        description="Config validation and diagnostics",
        add_help=False,
    )
    cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    nested = cmd.add_subparsers(dest="config_command")
    nested.add_parser("validate", help="validate config and state", description="Validate config and state")
    doctor_cmd = nested.add_parser("doctor", help="alias for doctor", description="Alias for doctor")
    doctor_cmd.add_argument("--fix", action="store_true", help="automatically fix simple issues")
    doctor_cmd.add_argument("--write-state", action="store_true", help="write missing generated state metadata")
    doctor_cmd.add_argument("--bootstrap-if-missing", action="store_true", help="compatibility alias for --write-state")
    nested.add_parser("edit", help="print the config path or open $EDITOR", description="Print the config path or open $EDITOR")


def _add_ui_group(subparsers: argparse._SubParsersAction) -> None:
    cmd = subparsers.add_parser(
        "ui",
        help="Web UI commands",
        description="Web UI commands",
        add_help=False,
    )
    cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    nested = cmd.add_subparsers(dest="ui_command")
    serve_cmd = nested.add_parser("serve", help="alias for serve", description="Alias for serve")
    serve_cmd.add_argument("--host", type=str, default="127.0.0.1", help="host to bind to")
    serve_cmd.add_argument("--port", type=int, default=8080, help="port to listen on")
    serve_cmd.add_argument("--token", type=str, default=None, help="bearer token for token-protected Web UI access")
    dashboard_cmd = nested.add_parser("dashboard", help="alias for dashboard", description="Alias for dashboard")
    dashboard_cmd.add_argument("--prepare", action="store_true", help="write missing generated state metadata")
    dashboard_cmd.add_argument("--bootstrap-if-missing", action="store_true", help="compatibility alias for --prepare")


def _add_state_group(subparsers: argparse._SubParsersAction) -> None:
    cmd = subparsers.add_parser(
        "state",
        help="state preparation commands",
        description="State preparation commands",
        add_help=False,
    )
    cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    nested = cmd.add_subparsers(dest="state_command")
    bootstrap_cmd = nested.add_parser("bootstrap", help="write missing session metadata", description="Write missing session metadata")
    bootstrap_cmd.add_argument("--dry-run", action="store_true", help="show changes without writing state")


def _normalize_grouped_command(args: argparse.Namespace) -> None:
    """Map canonical grouped commands onto existing handler names."""
    if args.command == "workspace":
        command = getattr(args, "workspace_command", None)
        if command == "down":
            args.command = "stop"
            args.target = None
        elif command == "prepare":
            args.command = "state"
            args.state_command = "bootstrap"
        elif command in {"init", "plan", "start", "status"}:
            args.command = command
        return

    if args.command == "target":
        command = getattr(args, "target_command", None)
        if command in {"attach", "stop", "restart"}:
            args.command = command
        return

    if args.command == "session":
        args.command = "sessions"
        return

    if args.command == "config":
        command = getattr(args, "config_command", None)
        if command == "doctor":
            args.command = "doctor"
        elif command == "validate":
            args.command = "config_validate"
        elif command == "edit":
            args.command = "config_edit"
        return

    if args.command == "ui":
        command = getattr(args, "ui_command", None)
        if command in {"serve", "dashboard"}:
            args.command = command
        return


def _output_format(args: argparse.Namespace) -> str:
    if getattr(args, "json", False):
        return "json"
    return getattr(args, "format", "text")


def _should_write_generated_state(args: argparse.Namespace) -> bool:
    return bool(
        getattr(args, "bootstrap_if_missing", False)
        or getattr(args, "write_state", False)
        or getattr(args, "prepare", False)
    )


def _format_file_not_found(error: FileNotFoundError) -> str:
    missing = Path(error.filename) if error.filename else None
    if missing and missing.name == DEFAULT_CONFIG:
        return (
            f"No workspace config found in {missing.parent}.\n\n"
            "Run:\n"
            f"  {PRIMARY_COMMAND} init\n\n"
            "Or point to a config:\n"
            f"  CC_BRANCH_CONFIG=/path/to/{DEFAULT_CONFIG} {PRIMARY_COMMAND} plan"
        )
    return f"Required file not found: {missing or error}"


def _print_cli_error(message: str) -> int:
    console.print(message)
    return 1


def _status_dict(workspace, plan) -> dict:
    from . import runtime as runtime_mod

    slots = []
    for slot in plan.slots:
        slot_running = runtime_mod.tmux_has_session(slot.tmux_session)
        windows = []
        for window in slot.windows:
            windows.append(
                {
                    "name": window.name,
                    "agent": window.agent,
                    "command": window.launch_command,
                    "session_id": window.resolved_session_id,
                    "label": window.resolved_label,
                    "cwd": window.cwd,
                    "status": (
                        "running"
                        if slot_running
                        and runtime_mod.tmux_has_window(slot.tmux_session, window.name)
                        else "stopped"
                    ),
                }
            )
        slots.append(
            {
                "name": slot.name,
                "backend": slot.backend,
                "session_name": slot.tmux_session,
                "status": "running" if slot_running else "stopped",
                "windows": windows,
            }
        )
    return {"project": workspace.project, "root": str(workspace.root), "slots": slots}


def _run_state_bootstrap(ctx: WorkspaceContext, *, dry_run: bool) -> int:
    workspace = load_workspace(ctx.config_path)
    state = load_state(ctx.state_path)
    plan = plan_workspace(workspace, state, bootstrap_missing=True)
    merged_state = merge_state(state, plan.state_updates)
    changed = merged_state != state
    if dry_run:
        if changed:
            console.print(f"[dim]Would update {ctx.state_path}[/dim]")
        else:
            console.print("[dim]State is already prepared.[/dim]")
        return 0

    if changed:
        save_state(ctx.state_path, merged_state)
        console.print(f"[green]✓[/green] Prepared state: {ctx.state_path}")
    else:
        console.print("[dim]State is already prepared.[/dim]")
    return 0


def _print_targets_help() -> None:
    console.print("[bold]Targets[/bold]")
    console.print()
    console.print("Use targets to select a workspace, slot, or slot window.")
    console.print()
    table = Table(show_header=True, header_style="bold magenta", border_style="blue", padding=(0, 2))
    table.add_column("Input", style="cyan", no_wrap=True)
    table.add_column("Meaning", style="white")
    table.add_row("(empty)", "whole workspace, where the command supports it")
    table.add_row("dev", "slot named dev")
    table.add_row("dev:planner", "window named planner in slot dev")
    table.add_row("dev.planner", "legacy compatibility form for dev:planner")
    console.print(table)
    console.print()
    console.print("[dim]Examples:[/dim]")
    console.print(f"  [cyan]{SHORT_ALIAS} attach dev:planner[/cyan]")
    console.print(f"  [cyan]{SHORT_ALIAS} stop dev[/cyan]")
    console.print(f"  [cyan]{SHORT_ALIAS} session inspect dev:planner[/cyan]")


def main(argv: list[str] | None = None) -> int:
    debug = argv is not None and "--debug" in argv
    try:
        return _main_impl(argv)
    except FileNotFoundError as e:
        if debug:
            raise
        return _print_cli_error(_format_file_not_found(e))
    except CcbError as e:
        if debug:
            raise
        return _print_cli_error(str(e))
    except ValueError as e:
        if debug:
            raise
        return _print_cli_error(str(e))


def _main_impl(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "no_color", False):
        console.no_color = True
    cwd = Path(args.project).expanduser() if getattr(args, "project", None) else Path.cwd()

    # Show command-specific help if command is provided with -h flag
    if args.command and hasattr(args, 'help') and args.help:
        print_command_help(args.command)
        return 0

    # Show main help if no command or -h flag without command
    if args.command is None:
        print_help()
        return 0

    _normalize_grouped_command(args)

    if args.command == "init":
        # Check if config already exists
        config_path = resolve_config_path(cwd)
        if config_path.exists() and not args.force:
            console.print()
            console.print("[red]✗[/red] Initialization failed")
            console.print()
            console.print(f"  {config_path.name} already exists")
            console.print()
            console.print("[dim]Options:[/dim]")
            console.print("  • Use [cyan]--force[/cyan] to overwrite existing config")
            console.print("  • Edit [cyan].cc-branch.yaml[/cyan] manually")
            console.print("  • Delete the file and run init again")
            console.print()
            return 1

        # Minimal mode: quick init without checks
        if args.minimal:
            config_path, state_path = init_workspace(
                cwd, args.force, args.bootstrap_sessions
            )
            console.print()
            console.print(f"[green]✓[/green] Created {config_path.name}")
            console.print(f"[green]✓[/green] Created {state_path.name}")
            console.print()
            console.print("[dim]Config created. Edit .cc-branch.yaml to customize.[/dim]")
            console.print("[dim]Run 'cc-branch plan' to preview before launch.[/dim]")
            console.print()
            return 0

        # Cold-start mode: full environment check and guided setup
        console.print()
        console.print("[cyan]Checking environment...[/cyan]")
        console.print()

        env_report = check_environment(cwd)

        # Display environment check results
        console.print("[bold]Environment Check:[/bold]")

        # Tmux check
        if env_report.tmux_available:
            console.print(f"  [green]✓[/green] tmux: ok ({env_report.tmux_path})")
        else:
            console.print("  [red]✗[/red] tmux: missing")
            console.print(f"    [dim]→ {tmux_install_hint()}[/dim]")

        console.print()

        # Agent CLIs check
        if env_report.agents:
            console.print("[bold]Agent CLIs:[/bold]")
            for agent in env_report.agents:
                if agent.status == "ok":
                    console.print(f"  [green]✓[/green] {agent.name}: ok ({agent.command})")
                else:
                    console.print(f"  [red]✗[/red] {agent.name}: missing")
                    console.print(f"    [dim]→ {agent.install_hint}[/dim]")

        console.print()

        # Config status
        console.print("[bold]Config:[/bold]")
        if env_report.config_exists:
            console.print("  [yellow]⚠[/yellow] .cc-branch.yaml: exists")
        else:
            if env_report.available_agents:
                console.print("  [yellow]⚠[/yellow] .cc-branch.yaml: missing")
                console.print(f"    [dim]→ Will create starter config with {len(env_report.available_agents)} agent(s)[/dim]")
            else:
                console.print("  [yellow]⚠[/yellow] .cc-branch.yaml: missing")
                console.print("    [dim]→ Will create minimal config with shell workspace[/dim]")

        console.print()

        # Check for blockers
        if not env_report.can_proceed:
            console.print("[red]✗[/red] Cannot proceed: no write permission")
            console.print()
            console.print("[dim]→ Check directory permissions: ls -la[/dim]")
            console.print("[dim]→ Or run in a directory where you have write access[/dim]")
            console.print()
            return 1

        # Warn about missing agents but continue
        if not env_report.available_agents:
            console.print("[yellow]⚠[/yellow] No AI agent CLIs detected")
            console.print()
            console.print("[dim]You can still create a workspace, but it will only have shell windows.[/dim]")
            console.print("[dim]Install at least one agent CLI for AI-powered workflows.[/dim]")
            console.print()

        # Generate config
        console.print("[cyan]Generating config...[/cyan]")
        console.print()

        try:
            result = initialize_workspace_files(
                cwd,
                profile=args.profile,
                available_agents=env_report.available_agents,
                bootstrap_sessions_requested=args.bootstrap_sessions,
            )
        except ValueError as e:
            console.print(f"[red]✗[/red] Invalid profile: {e}")
            console.print()
            from .profiles import get_available_profiles
            available = get_available_profiles()
            console.print(f"[dim]Available profiles: {', '.join(available)}[/dim]")
            console.print()
            return 1

        console.print(f"[green]✓[/green] Created {result.config_path.name}")
        console.print(f"  [dim]- {result.config_summary.slots} slots[/dim]")
        console.print(f"  [dim]- {result.config_summary.windows} windows[/dim]")
        console.print(f"  [dim]- {result.config_summary.agents} agents[/dim]")
        console.print()

        # Bootstrap sessions
        if args.bootstrap_sessions or env_report.available_agents:
            console.print("[cyan]Bootstrapping session metadata...[/cyan]")
            console.print()

            # Show what was bootstrapped
            num_sessions = len(result.state.windows)
            if num_sessions > 0:
                console.print(f"[green]✓[/green] Generated {num_sessions} session ID(s)")
                windows_items = list(result.state.windows.items())
                for key, entry in windows_items[:3]:
                    if entry and entry.session_id:
                        session_id = entry.session_id
                        short_id = session_id[:8] + "..." if len(session_id) > 8 else session_id
                        console.print(f"  [dim]- {key} → {short_id}[/dim]")
                if num_sessions > 3:
                    console.print(f"  [dim]- ... and {num_sessions - 3} more[/dim]")
            else:
                console.print("[yellow]⊘[/yellow] No sessions to bootstrap (shell-only workspace)")

            console.print()
            console.print(f"[green]✓[/green] Created {result.state_path.name}")
            console.print()
        else:
            console.print(f"[green]✓[/green] Created {result.state_path.name} (empty)")
            console.print()

        if result.gitignore_created:
            console.print("[green]✓[/green] Created .gitignore")
            console.print()
        elif result.gitignore_updated:
            console.print("[green]✓[/green] Updated .gitignore")
            console.print()

        # Success message with next steps
        console.print("[green]✓[/green] [bold]Workspace initialized successfully![/bold]")
        console.print()
        console.print("[bold]Next steps:[/bold]")
        console.print(f"  1. Review config: [cyan]cat {DEFAULT_CONFIG}[/cyan]")
        console.print(f"  2. Check status: [cyan]{PRIMARY_COMMAND} doctor[/cyan]")
        console.print(f"  3. Start workspace: [cyan]{PRIMARY_COMMAND} start[/cyan]")
        console.print()
        console.print(f"[dim]Tip: Use '{PRIMARY_COMMAND} plan' to preview the launch plan before starting.[/dim]")
        console.print()

        return 0

    if args.command == "help":
        if args.topic == "targets":
            _print_targets_help()
            return 0
        print_help()
        return 0

    # Load workspace context for all other commands
    ctx = WorkspaceContext(
        cwd,
        config_path=getattr(args, "config", None),
        state_path=getattr(args, "state", None),
    )
    if args.command == "state":
        if getattr(args, "state_command", None) in {"bootstrap", None}:
            return _run_state_bootstrap(ctx, dry_run=getattr(args, "dry_run", False))
        parser.error("state subcommand required")
        return 2

    if args.command == "config_edit":
        editor = os.environ.get("EDITOR")
        if editor:
            return subprocess.call([editor, str(ctx.config_path)])
        console.print(str(ctx.config_path))
        return 0

    if args.command == "serve":
        from .webui.server import start_server

        token = args.token or os.environ.get("CC_BRANCH_WEB_TOKEN")
        if not _is_loopback_host(args.host) and not token:
            console.print(
                "[red]✗[/red] Refusing to bind Web UI to a non-loopback host without authentication."
            )
            console.print(
                "[dim]Use --token or CC_BRANCH_WEB_TOKEN when serving beyond localhost.[/dim]"
            )
            return 1

        start_server(ctx.config_path, ctx.state_path, host=args.host, port=args.port, token=token)
        return 0

    bootstrap_missing = _should_write_generated_state(args)
    workspace, plan = ctx.load(bootstrap_missing=bootstrap_missing)
    state = ctx.state

    if args.command == "attach":
        if args.slot is None:
            parser.error("attach requires a <slot>")
            return 2
        attach_slot(plan, args.slot)
        return 0

    if args.command == "stop":
        stop_workspace(workspace, plan, args.target)
        return 0

    if args.command == "plan":
        if _output_format(args) == "json":
            print(json.dumps(plan.to_dict(), indent=2))
        else:
            print(format_plan(plan))
        return 0

    if args.command == "status":
        if _output_format(args) == "json":
            print(json.dumps(_status_dict(workspace, plan), indent=2))
        else:
            print(format_status(workspace, plan))
        return 0

    if args.command == "start":
        if getattr(args, "dashboard", False):
            open_dashboard(workspace, plan)
            return 0
        apply_workspace(plan, detach=args.detach)
        return 0

    if args.command == "restart":
        restart_workspace(workspace, plan, args.target, detach=args.detach)
        return 0

    if args.command == "doctor":
        report = build_doctor_report(workspace, plan)
        if _output_format(args) == "json":
            print(json.dumps({"report": report}, indent=2))
        else:
            print(report)

        # If --fix flag is provided, attempt to fix issues
        if getattr(args, "fix", False):
            from .doctor import auto_fix_issues
            print("\n" + "="*50)
            print("Attempting to fix issues automatically...")
            print("="*50 + "\n")
            fixes_applied = auto_fix_issues(workspace, plan, ctx.state_path)
            if fixes_applied:
                print("\n✓ Some issues were fixed. Run 'cc-branch doctor' again to verify.")
            else:
                print("\n⚠ No automatic fixes were applied. Please fix issues manually.")
        return 0

    if args.command == "config_validate":
        if _output_format(args) == "json":
            print(json.dumps({"valid": True, "config_path": str(ctx.config_path)}, indent=2))
        else:
            console.print(f"[green]✓[/green] Config valid: {ctx.config_path}")
        return 0

    if args.command == "dashboard":
        open_dashboard(workspace, plan)
        return 0

    if args.command == "sessions":
        if args.sessions_command == "list" or args.sessions_command is None:
            sessions = list_sessions(workspace, plan, state)
            if _output_format(args) == "json":
                print(json.dumps([s.__dict__ for s in sessions], indent=2))
                return 0
            if not sessions:
                console.print("[dim]No sessions found.[/dim]")
                return 0
            table = Table(show_header=True, header_style="bold magenta", border_style="blue", padding=(0, 2))
            table.add_column("Key", style="cyan", no_wrap=True)
            table.add_column("Slot", style="white")
            table.add_column("Window", style="white")
            table.add_column("Agent", style="white")
            table.add_column("Status", style="white")
            for s in sessions:
                status_color = {
                    "running": "green",
                    "stopped": "yellow",
                    "orphaned": "red",
                }.get(s.status, "white")
                table.add_row(
                    s.key,
                    s.slot,
                    s.window,
                    s.agent or "[dim]-[/dim]",
                    f"[{status_color}]{s.status}[/{status_color}]",
                )
            console.print(table)
            return 0

        if args.sessions_command == "inspect":
            info = inspect_session(workspace, plan, state, args.key)
            if info is None:
                console.print(f"[red]Session not found: {args.key}[/red]")
                return 1
            if _output_format(args) == "json":
                print(json.dumps(info.__dict__, indent=2))
                return 0
            console.print(f"[bold]Session:[/bold] {info.key}")
            console.print(f"  Slot: {info.slot}")
            console.print(f"  Window: {info.window}")
            console.print(f"  Agent: {info.agent or '[dim]none[/dim]'}")
            console.print(f"  Session ID: {info.session_id or '[dim]none[/dim]'}")
            console.print(f"  Label: {info.label or '[dim]none[/dim]'}")
            status_color = {
                "running": "green",
                "stopped": "yellow",
                "orphaned": "red",
            }.get(info.status, "white")
            console.print(f"  Status: [{status_color}]{info.status}[/{status_color}]")
            if info.launch_command:
                console.print(f"  Launch command: {info.launch_command}")
            return 0

        if args.sessions_command == "prune":
            removed = prune_sessions(workspace, plan, state, dry_run=args.dry_run)
            if args.dry_run:
                if removed:
                    console.print(f"[dim]Would remove {len(removed)} session(s):[/dim]")
                    for key in removed:
                        console.print(f"  [yellow]- {key}[/yellow]")
                else:
                    console.print("[dim]No orphaned sessions to prune.[/dim]")
            else:
                if removed:
                    # Persist updated state
                    save_state(ctx.state_path, state)
                    console.print(f"[green]✓[/green] Pruned {len(removed)} orphaned session(s):")
                    for key in removed:
                        console.print(f"  [green]- {key}[/green]")
                else:
                    console.print("[dim]No orphaned sessions to prune.[/dim]")
            return 0

        if args.sessions_command in {"command", "restore"}:
            command = restore_session(workspace, plan, state, args.key)
            if command is None:
                console.print(f"[red]Cannot build launch command for: {args.key}[/red]")
                return 1
            label = "Launch command"
            if args.sessions_command == "restore":
                console.print("[yellow]restore is a compatibility alias; prefer session command.[/yellow]")
            console.print(f"[dim]{label} for {args.key}:[/dim]")
            console.print(command)
            return 0

        parser.error("sessions subcommand required")
        return 2

    parser.error(f"unsupported command: {args.command}")
    return 2
