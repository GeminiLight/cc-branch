from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version

from .. import __version__
from .constants import PRIMARY_COMMAND, SHORT_ALIAS


def _package_version() -> str:
    try:
        return version("cc-branch")
    except PackageNotFoundError:
        return __version__


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
    parser.add_argument("--state", type=str, help="path to .cc-branch.state.yaml")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format for inspection commands",
    )
    parser.add_argument("--no-color", action="store_true", help="disable ANSI color output")
    parser.add_argument("--debug", action="store_true", help="show Python tracebacks")
    sub = parser.add_subparsers(dest="command")

    serve_cmd = sub.add_parser(
        "serve",
        help="start the Web UI server",
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

    init_cmd = sub.add_parser(
        "init",
        help="create a starter workspace config",
        description="Create a starter workspace config",
        add_help=False,
    )
    init_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    init_cmd.add_argument("--force", action="store_true", help="overwrite existing config files")
    init_cmd.add_argument("--minimal", action="store_true", help="create config without environment checks")
    init_cmd.add_argument("--profile", type=str, default="solo-dev", help="profile template to use")

    def add_start_options(command: argparse.ArgumentParser) -> None:
        command.add_argument("-h", "--help", action="store_true", help="show this help message")
        command.add_argument("--prepare", action="store_true", help="write missing generated state metadata before launch")
        command.add_argument(
            "--detach",
            action="store_true",
            help="start reusable tmux sessions without attaching or opening terminal-runtime slots",
        )
        command.add_argument("--dashboard", action="store_true", help="open the tiled tmux dashboard")

    start_cmd = sub.add_parser(
        "start",
        help="start reusable tmux sessions",
        description="Start reusable tmux sessions",
        add_help=False,
    )
    add_start_options(start_cmd)

    open_cmd = sub.add_parser(
        "open",
        help="open the workspace or a target in a local app",
        description="Open the workspace or a target in a local app",
        add_help=False,
    )
    open_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    open_cmd.add_argument("target", nargs="?", metavar="slot[:window]", help="optional target such as dev or dev:planner")
    open_cmd.add_argument("--opener", type=str, default=None, help="opener id such as auto-terminal, warp, vscode, or cursor")
    open_cmd.add_argument("--project-dir", action="store_true", help="open the project directory instead of the workspace")

    status_cmd = sub.add_parser(
        "status",
        help="show workspace status",
        description="Show workspace status",
        add_help=False,
    )
    status_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    status_cmd.add_argument("--write-state", action="store_true", help="write missing generated state metadata")
    status_cmd.add_argument("--json", action="store_true", help="alias for --format json")

    plan_cmd = sub.add_parser(
        "plan",
        help="show the resolved launch plan",
        description="Show the resolved launch plan",
        add_help=False,
    )
    plan_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    plan_cmd.add_argument("--write-state", action="store_true", help="write missing generated state metadata")
    plan_cmd.add_argument("--json", action="store_true", help="alias for --format json")

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
    restart_cmd.add_argument("--prepare", action="store_true", help="write missing generated state metadata before restart")
    restart_cmd.add_argument("--detach", action="store_true", help="restart without attaching")

    def add_apply_options(command: argparse.ArgumentParser) -> None:
        command.add_argument("-h", "--help", action="store_true", help="show this help message")
        command.add_argument("target", nargs="?", metavar="slot[:window]", help="optional target such as dev or dev:planner")
        command.add_argument("--dry-run", action="store_true", help="show planned actions without changing runtime")
        command.add_argument("--yes", action="store_true", help="sync without interactive confirmation")
        command.add_argument("--stop-removed", action="store_true", help="also stop extra tmux windows not in config")

    sync_cmd = sub.add_parser(
        "sync",
        help="sync config changes with running tmux targets",
        description="Sync config changes with running tmux targets",
        add_help=False,
    )
    add_apply_options(sync_cmd)

    doctor_cmd = sub.add_parser(
        "doctor",
        help="validate workspace dependencies and metadata",
        description="Validate workspace dependencies and metadata",
        add_help=False,
    )
    doctor_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    doctor_cmd.add_argument("--write-state", action="store_true", help="write missing generated state metadata")
    doctor_cmd.add_argument("--fix", action="store_true", help="automatically fix simple issues")

    dashboard_cmd = sub.add_parser(
        "dashboard",
        help="open a tiled tmux dashboard for all slots",
        description="Open a tiled tmux dashboard for all slots",
        add_help=False,
    )
    dashboard_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    dashboard_cmd.add_argument("--prepare", action="store_true", help="write missing generated state metadata before opening")

    _add_session_group(sub, "session", "manage saved agent session metadata")
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
    nested = cmd.add_subparsers(dest="session_command")
    nested.add_parser("list", help="list saved agent session entries", description="List saved agent session entries")

    inspect_cmd = nested.add_parser("inspect", help="inspect a saved session entry", description="Inspect a saved session entry")
    inspect_cmd.add_argument("key", metavar="slot[:window]", help="target such as dev:planner")

    prune_cmd = nested.add_parser("prune", help="remove orphaned session entries", description="Remove orphaned session entries")
    prune_cmd.add_argument("--dry-run", action="store_true", help="show what would be removed")

    command_cmd = nested.add_parser("command", help="print the launch command for a target", description="Print the launch command for a target")
    command_cmd.add_argument("key", metavar="slot[:window]", help="target such as dev:planner")


