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
    _add_snapshot_group(sub)
    _add_project_group(sub)
    _add_worktree_group(sub)
    help_cmd = sub.add_parser(
        "help",
        help="show concept guides",
        description="Show concept guides",
        add_help=False,
    )
    help_cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    help_cmd.add_argument("topic", nargs="?", choices=["targets"], help="guide topic")

    return parser


def _add_snapshot_group(subparsers: argparse._SubParsersAction) -> None:
    cmd = subparsers.add_parser(
        "snapshot",
        help="capture and restore workspace snapshots",
        description="Capture and restore workspace snapshots",
        add_help=False,
    )
    cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    nested = cmd.add_subparsers(dest="snapshot_command")
    create_cmd = nested.add_parser("create", help="capture the current workspace", description="Capture the current workspace")
    create_cmd.add_argument("--name", type=str, default=None, help="snapshot name")
    create_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")
    list_cmd = nested.add_parser("list", help="list workspace snapshots", description="List workspace snapshots")
    list_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")
    show_cmd = nested.add_parser("show", help="show snapshot details", description="Show snapshot details")
    show_cmd.add_argument("snapshot_id", help="snapshot id or name")
    show_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")
    preview_cmd = nested.add_parser("preview", help="preview snapshot restore changes", description="Preview snapshot restore changes")
    preview_cmd.add_argument("snapshot_id", help="snapshot id or name")
    preview_cmd.add_argument("--state-path", type=str, default=None, help="override target state path")
    preview_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")
    restore_cmd = nested.add_parser("restore", help="restore saved workspace state", description="Restore saved workspace state")
    restore_cmd.add_argument("snapshot_id", help="snapshot id or name")
    restore_cmd.add_argument("--dry-run", action="store_true", help="preview restore without writing state")
    restore_cmd.add_argument("--state-path", type=str, default=None, help="override target state path")
    restore_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")
    export_cmd = nested.add_parser("export", help="export a snapshot JSON file", description="Export a snapshot JSON file")
    export_cmd.add_argument("snapshot_id", help="snapshot id or name")
    export_cmd.add_argument("--output", "-o", required=True, help="output JSON path")
    export_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")
    import_cmd = nested.add_parser("import", help="import a snapshot JSON file", description="Import a snapshot JSON file")
    import_cmd.add_argument("path", help="snapshot JSON path")
    import_cmd.add_argument("--name", type=str, default=None, help="override imported snapshot name")
    import_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")


def _add_project_group(subparsers: argparse._SubParsersAction) -> None:
    cmd = subparsers.add_parser(
        "project",
        help="manage the desktop/Web UI project index",
        description="Manage the desktop/Web UI project index",
        add_help=False,
    )
    cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    nested = cmd.add_subparsers(dest="project_command")
    list_cmd = nested.add_parser("list", help="list indexed projects", description="List indexed projects")
    list_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")
    add_cmd = nested.add_parser("add", help="add a local project", description="Add a local project")
    add_cmd.add_argument("path", help="project path")
    add_cmd.add_argument("--name", type=str, default=None, help="project display name")
    add_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")
    remote_cmd = nested.add_parser("add-remote", help="add an SSH project", description="Add an SSH project")
    remote_cmd.add_argument("--host", required=True, help="SSH host or alias")
    remote_cmd.add_argument("--cwd", required=True, help="remote project directory")
    remote_cmd.add_argument("--user", type=str, default=None, help="SSH user")
    remote_cmd.add_argument("--port", type=int, default=None, help="SSH port")
    remote_cmd.add_argument("--name", type=str, default=None, help="project display name")
    remote_cmd.add_argument("--agent", type=str, default="codex", help="agent command to preflight and write into config")
    remote_cmd.add_argument("--dry-run", action="store_true", help="preflight without saving the project")
    remote_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")


def _add_worktree_group(subparsers: argparse._SubParsersAction) -> None:
    cmd = subparsers.add_parser(
        "worktree",
        help="manage optional agent git worktrees",
        description="Manage optional agent git worktrees",
        add_help=False,
    )
    cmd.add_argument("-h", "--help", action="store_true", help="show this help message")
    nested = cmd.add_subparsers(dest="worktree_command")
    setup_cmd = nested.add_parser("setup", help="create an agent worktree", description="Create an agent worktree")
    setup_cmd.add_argument("target", metavar="tab[:pane]", help="agent target such as dev:planner")
    setup_cmd.add_argument("--path", type=str, default=None, help="worktree path")
    setup_cmd.add_argument("--branch", type=str, default=None, help="branch name")
    setup_cmd.add_argument("--base", type=str, default="HEAD", help="base ref")
    setup_cmd.add_argument("--copy", action="append", default=[], help="copy a gitignored file or directory into the worktree")
    setup_cmd.add_argument("--symlink", action="append", default=[], help="symlink a gitignored file or directory into the worktree")
    setup_cmd.add_argument("--setup-hook", type=str, default=None, help="shell command to run after worktree creation")
    setup_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")
    import_cmd = nested.add_parser("import", help="record an existing agent worktree", description="Record an existing agent worktree")
    import_cmd.add_argument("target", metavar="tab[:pane]", help="agent target such as dev:planner")
    import_cmd.add_argument("path", help="existing worktree path")
    import_cmd.add_argument("--branch", type=str, default=None, help="branch name")
    import_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")
    status_cmd = nested.add_parser("status", help="show agent worktree status", description="Show agent worktree status")
    status_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")
    finish_cmd = nested.add_parser("finish", help="mark an agent worktree as finished", description="Mark an agent worktree as finished")
    finish_cmd.add_argument("target", metavar="tab[:pane]", help="agent target such as dev:planner")
    finish_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")
    cleanup_cmd = nested.add_parser("cleanup", help="remove an agent worktree", description="Remove an agent worktree")
    cleanup_cmd.add_argument("target", metavar="tab[:pane]", help="agent target such as dev:planner")
    cleanup_cmd.add_argument("--force", action="store_true", help="pass --force to git worktree remove")
    cleanup_cmd.add_argument("--format", choices=["text", "json"], default=argparse.SUPPRESS, help="output format")


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
    restore_cmd.add_argument("--target", type=str, default=None, help="only restore one target such as dev:planner")
    restore_cmd.add_argument("--agent", type=str, default=None, help="only restore panes for one agent id")
    restore_cmd.add_argument("--dry-run", action="store_true", help="show candidate bindings without writing state")
    restore_cmd.add_argument("--force", action="store_true", help="replace existing session bindings")
    restore_cmd.add_argument("--limit", type=int, default=20, help="candidate scan limit per agent")
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
