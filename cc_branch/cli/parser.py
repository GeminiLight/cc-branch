from __future__ import annotations

import argparse
from .. import __version__
from ..constants import DEFAULT_CONFIG, DEFAULT_STATE
from .constants import SHORT_ALIAS


def _package_version() -> str:
    return __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage an agent workspace",
        prog=SHORT_ALIAS,
        add_help=False  # Disable default help to use custom help
    )
    parser.add_argument("-h", "--help", action="store_true", help="show this help message")
    parser.add_argument("--version", action="version", version=f"cc-branch {_package_version()}")
    parser.add_argument("--project", type=str, help=f"project directory containing {DEFAULT_CONFIG}")
    parser.add_argument("--config", type=str, help="config path or name under .cc-branch/configs")
    parser.add_argument("--state", type=str, help=f"path to {DEFAULT_STATE}")
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

    service_cmd = sub.add_parser(
        "service",
        help="manage the local Web UI service",
        description="Manage the local Web UI service",
        add_help=False,
    )
    service_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    service_sub = service_cmd.add_subparsers(dest="service_command")

    def add_service_start_options(command: argparse.ArgumentParser) -> None:
        command.add_argument("--host", type=str, default="127.0.0.1", help="host to bind to")
        command.add_argument("--port", type=int, default=8080, help="port to listen on")
        command.add_argument(
            "--token",
            type=str,
            default=None,
            help="bearer token required for token-protected Web UI access",
        )

    service_start = service_sub.add_parser(
        "start",
        help="start the Web UI service",
        description="Start the Web UI service in the background",
    )
    add_service_start_options(service_start)
    service_sub.add_parser("status", help="show Web UI service status", description="Show Web UI service status")
    service_stop = service_sub.add_parser("stop", help="stop the Web UI service", description="Stop the Web UI service")
    service_stop.add_argument("--timeout", type=float, default=5.0, help="seconds to wait for shutdown")
    service_restart = service_sub.add_parser(
        "restart",
        help="restart the Web UI service",
        description="Restart the Web UI service",
    )
    add_service_start_options(service_restart)
    service_restart.add_argument("--timeout", type=float, default=5.0, help="seconds to wait for shutdown")
    service_logs = service_sub.add_parser("logs", help="show Web UI service logs", description="Show Web UI service logs")
    service_logs.add_argument("-n", "--lines", type=int, default=100, help="number of lines to show")

    init_cmd = sub.add_parser(
        "init",
        help="create a starter workspace config",
        description="Create a starter workspace config",
        add_help=False,
    )
    init_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    init_cmd.add_argument("--force", action="store_true", help="overwrite existing config files")
    init_cmd.add_argument("--minimal", action="store_true", help="create config without environment checks")
    init_cmd.add_argument("--profile", type=str, default="development", help="profile template to use")

    def add_start_options(command: argparse.ArgumentParser) -> None:
        command.add_argument("-h", "--help", action="store_true", help="show this help message")
        command.add_argument("--prepare", action="store_true", help="write missing generated state metadata before launch")
        command.add_argument(
            "--detach",
            action="store_true",
            help="start reusable tmux sessions without attaching or opening direct-layout panes",
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
    open_cmd.add_argument("target", nargs="?", metavar="tab[:pane]", help="optional target such as dev or dev:planner")
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
    status_cmd.add_argument(
        "--format",
        choices=["text", "json"],
        default=argparse.SUPPRESS,
        help="output format",
    )
    status_cmd.add_argument("--json", action="store_true", help="alias for --format json")

    plan_cmd = sub.add_parser(
        "plan",
        help="show the resolved launch plan",
        description="Show the resolved launch plan",
        add_help=False,
    )
    plan_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    plan_cmd.add_argument("--write-state", action="store_true", help="write missing generated state metadata")
    plan_cmd.add_argument(
        "--format",
        choices=["text", "json"],
        default=argparse.SUPPRESS,
        help="output format",
    )
    plan_cmd.add_argument("--json", action="store_true", help="alias for --format json")

    attach_cmd = sub.add_parser(
        "attach",
        help="attach to a tab or pane",
        description="Attach to a tab or pane",
        add_help=False,
    )
    attach_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    attach_cmd.add_argument("slot", nargs="?", metavar="tab[:pane]", help="target such as dev or dev:planner")

    stop_cmd = sub.add_parser(
        "stop",
        help="stop the workspace, a tab, or a pane",
        description="Stop the workspace, a tab, or a pane",
        add_help=False,
    )
    stop_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    stop_cmd.add_argument("target", nargs="?", metavar="tab[:pane]", help="optional target such as dev or dev:planner")

    restart_cmd = sub.add_parser(
        "restart",
        help="restart the workspace, a tab, or a pane",
        description="Restart the workspace, a tab, or a pane",
        add_help=False,
    )
    restart_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    restart_cmd.add_argument("target", nargs="?", metavar="tab[:pane]", help="optional target such as dev or dev:planner")
    restart_cmd.add_argument("--prepare", action="store_true", help="write missing generated state metadata before restart")
    restart_cmd.add_argument("--detach", action="store_true", help="restart without attaching")

    send_cmd = sub.add_parser(
        "send",
        help="send a message to a tab or pane",
        description="Send a message to a tab or pane",
        add_help=False,
    )
    send_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    send_cmd.add_argument("target", metavar="tab[:pane]", help="target such as dev:planner")
    send_cmd.add_argument("message", nargs="+", help="message text to paste into the target")

    def add_apply_options(command: argparse.ArgumentParser) -> None:
        command.add_argument("-h", "--help", action="store_true", help="show this help message")
        command.add_argument("target", nargs="?", metavar="tab[:pane]", help="optional target such as dev or dev:planner")
        command.add_argument("--dry-run", action="store_true", help="show planned actions without changing runtime")
        command.add_argument("--yes", action="store_true", help="sync without interactive confirmation")
        command.add_argument("--stop-removed", action="store_true", help="also stop extra tmux panes not in config")

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
    doctor_cmd.add_argument(
        "--format",
        choices=["text", "json"],
        default=argparse.SUPPRESS,
        help="output format",
    )

    dashboard_cmd = sub.add_parser(
        "dashboard",
        help="open a tiled tmux dashboard for all tabs",
        description="Open a tiled tmux dashboard for all tabs",
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
    list_cmd = nested.add_parser(
        "list",
        help="list saved agent session entries",
        description="List saved agent session entries",
    )
    list_cmd.add_argument(
        "--format",
        choices=["text", "json"],
        default=argparse.SUPPRESS,
        help="output format",
    )

    inspect_cmd = nested.add_parser("inspect", help="inspect a saved session entry", description="Inspect a saved session entry")
    inspect_cmd.add_argument("key", metavar="tab[:pane]", help="target such as dev:planner")
    inspect_cmd.add_argument(
        "--format",
        choices=["text", "json"],
        default=argparse.SUPPRESS,
        help="output format",
    )

    prune_cmd = nested.add_parser(
        "prune",
        help="remove stale local session records",
        description="Remove stale local session records that no longer belong to the current config",
    )
    prune_cmd.add_argument("--dry-run", action="store_true", help="show what would be removed")

    restore_cmd = nested.add_parser(
        "restore",
        help="scan local agent transcripts and bind matching sessions",
        description="Scan local agent transcripts and bind matching sessions",
    )
    restore_cmd.add_argument(
        "--format",
        choices=["text", "json"],
        default=argparse.SUPPRESS,
        help="output format",
    )

    command_cmd = nested.add_parser("command", help="print the launch command for a target", description="Print the launch command for a target")
    command_cmd.add_argument("key", metavar="tab[:pane]", help="target such as dev:planner")

    hook_cmd = nested.add_parser(
        "hook",
        help="record an agent session lifecycle event",
        description="Record an agent session lifecycle event",
    )
    hook_cmd.add_argument("key", metavar="tab:pane", help="target such as dev:planner")
    hook_cmd.add_argument(
        "--event",
        required=True,
        choices=["started", "updated", "exited", "error"],
        help="agent lifecycle event",
    )
    hook_cmd.add_argument("--agent", type=str, default=None, help="agent id such as codex or claude")
    hook_cmd.add_argument("--session-id", type=str, default=None, help="agent-native session id")
    hook_cmd.add_argument("--transcript", type=str, default=None, help="agent transcript path")
    hook_cmd.add_argument("--label", type=str, default=None, help="human-readable session label")
    hook_cmd.add_argument("--pid", type=int, default=None, help="agent process id")
    hook_cmd.add_argument("--exit-code", type=int, default=None, help="agent process exit code")
    hook_cmd.add_argument("--timestamp", type=str, default=None, help="event timestamp as ISO-8601")
    hook_cmd.add_argument(
        "--format",
        choices=["text", "json"],
        default=argparse.SUPPRESS,
        help="output format",
    )
