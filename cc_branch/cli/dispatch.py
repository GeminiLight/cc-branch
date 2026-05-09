"""CLI command dispatch."""

from __future__ import annotations

from ..exceptions import CcbError
from .commands.doctor import run_doctor
from .commands.init import run_init
from .commands.open import run_open
from .commands.serve import run_serve
from .commands.sessions import run_session
from .commands.sync import run_sync
from .commands.workspace import (
    run_attach,
    run_dashboard,
    run_plan,
    run_restart,
    run_start,
    run_status,
    run_stop,
)
from .errors import format_file_not_found, print_cli_error
from .output import should_write_generated_state
from .targets import print_targets_help


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    debug = argv is not None and "--debug" in argv
    try:
        return main_impl(argv)
    except FileNotFoundError as error:
        if debug:
            raise
        return print_cli_error(format_file_not_found(error))
    except CcbError as error:
        if debug:
            raise
        return print_cli_error(str(error))
    except ValueError as error:
        if debug:
            raise
        return print_cli_error(str(error))


def main_impl(argv: list[str] | None = None) -> int:
    """Parse arguments and route to a command handler."""
    import cc_branch.cli as cli

    parser = cli.build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "no_color", False):
        cli.console.no_color = True
    cwd = cli.Path(args.project).expanduser() if getattr(args, "project", None) else cli.Path.cwd()

    if args.command and hasattr(args, "help") and args.help:
        cli.print_command_help(args.command)
        return 0
    if args.command is None:
        cli.print_help()
        return 0

    if args.command == "init":
        return run_init(cwd, args)

    if args.command == "help":
        if args.topic == "targets":
            print_targets_help()
            return 0
        cli.print_help()
        return 0

    ctx = cli.WorkspaceContext(
        cwd,
        config_path=getattr(args, "config", None),
        state_path=getattr(args, "state", None),
    )

    if args.command == "serve":
        return run_serve(ctx, args)
    if args.command == "open":
        return run_open(ctx, args)

    workspace, plan = ctx.load(bootstrap_missing=should_write_generated_state(args))
    state = ctx.state

    if args.command == "attach":
        return run_attach(parser, ctx, args, workspace, plan, state)
    if args.command == "stop":
        return run_stop(ctx, args, workspace, plan, state)
    if args.command == "plan":
        return run_plan(args, plan)
    if args.command == "status":
        return run_status(args, workspace, plan, state)
    if args.command == "start":
        return run_start(ctx, args, workspace, plan, state)
    if args.command == "restart":
        return run_restart(ctx, args, workspace, plan, state)
    if args.command == "sync":
        return run_sync(ctx, args, workspace, plan, state)
    if args.command == "doctor":
        return run_doctor(ctx, args, workspace, plan)
    if args.command == "dashboard":
        return run_dashboard(ctx, workspace, plan, state)
    if args.command == "session":
        return run_session(ctx, args, workspace, plan, state, parser)

    parser.error(f"unsupported command: {args.command}")
    return 2
