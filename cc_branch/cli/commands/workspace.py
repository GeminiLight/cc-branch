"""CLI workspace lifecycle, plan, and status commands."""

from __future__ import annotations

import argparse
import json

from ...context import WorkspaceContext
from ...runtime import format_status
from ..output import output_format


def status_dict(workspace, plan, state=None) -> dict:
    """Return a structured workspace status payload."""
    import cc_branch.cli as cli

    return cli.build_workspace_status(workspace, plan, state)


def run_attach(parser, ctx: WorkspaceContext, args: argparse.Namespace, workspace, plan, state) -> int:
    if args.slot is None:
        parser.error("attach requires a <slot>")
        return 2
    import cc_branch.cli as cli

    result = cli.attach_workspace_action(workspace, plan, state, ctx.state_path, target=args.slot)
    if not result.ok:
        cli.console.print(f"[red]{result.message}[/red]")
    return result.exit_code


def run_stop(ctx: WorkspaceContext, args: argparse.Namespace, workspace, plan, state) -> int:
    import cc_branch.cli as cli

    result = cli.stop_workspace_action(workspace, plan, state, ctx.state_path, target=args.target)
    if not result.ok:
        cli.console.print(f"[red]{result.message}[/red]")
    return result.exit_code


def run_plan(args: argparse.Namespace, plan) -> int:
    import cc_branch.cli as cli

    if output_format(args) == "json":
        print(json.dumps(plan.to_dict(), indent=2))
    else:
        print(cli.format_plan(plan))
    return 0


def run_status(args: argparse.Namespace, workspace, plan, state) -> int:
    if output_format(args) == "json":
        print(json.dumps(status_dict(workspace, plan, state), indent=2))
    else:
        print(format_status(workspace, plan, state))
    return 0


def run_start(ctx: WorkspaceContext, args: argparse.Namespace, workspace, plan, state) -> int:
    import cc_branch.cli as cli

    if getattr(args, "dashboard", False):
        result = cli.open_dashboard_workspace_action(workspace, plan, state, ctx.state_path)
    elif getattr(args, "detach", False):
        result = cli.launch_workspace_action(workspace, plan, state, ctx.state_path)
    else:
        result = cli.start_workspace_action(workspace, plan, state, ctx.state_path, detach=args.detach)
    if not result.ok:
        cli.console.print(f"[red]{result.message}[/red]")
    return result.exit_code


def run_restart(ctx: WorkspaceContext, args: argparse.Namespace, workspace, plan, state) -> int:
    import cc_branch.cli as cli

    result = cli.restart_workspace_action(
        workspace,
        plan,
        state,
        ctx.state_path,
        target=args.target,
        detach=args.detach,
    )
    if not result.ok:
        cli.console.print(f"[red]{result.message}[/red]")
    return result.exit_code


def run_dashboard(ctx: WorkspaceContext, workspace, plan, state) -> int:
    import cc_branch.cli as cli

    result = cli.open_dashboard_workspace_action(workspace, plan, state, ctx.state_path)
    if not result.ok:
        cli.console.print(f"[red]{result.message}[/red]")
    return result.exit_code
