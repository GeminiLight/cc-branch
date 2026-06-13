"""CLI agent worktree subcommands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...application.agent_worktrees import (
    AgentWorktreeStore,
    cleanup_agent_worktree,
    finish_agent_worktree,
    import_agent_worktree,
    setup_agent_worktree,
    worktree_status_for_agents,
)
from ...context import WorkspaceContext
from ..output import output_format


def _runner(command):
    from ...application.agent_worktrees import _run

    return _run(command)


def run_worktree(ctx: WorkspaceContext, args: argparse.Namespace, workspace, plan, state, parser) -> int:
    del ctx, state
    if args.worktree_command in {None, "status"}:
        return _run_worktree_status(args)
    if args.worktree_command == "setup":
        return _run_worktree_setup(args, workspace, plan)
    if args.worktree_command == "import":
        return _run_worktree_import(args, workspace, plan)
    if args.worktree_command == "finish":
        return _run_worktree_finish(args)
    if args.worktree_command == "cleanup":
        return _run_worktree_cleanup(args)
    parser.error("worktree subcommand required")
    return 2


def _run_worktree_setup(args: argparse.Namespace, workspace, plan) -> int:
    import cc_branch.cli as cli

    record = setup_agent_worktree(
        workspace,
        plan,
        args.target,
        store=AgentWorktreeStore(),
        path=Path(args.path) if args.path else None,
        branch=args.branch,
        base_ref=args.base,
        copy_ignored=args.copy,
        symlink_ignored=args.symlink,
        setup_hook=args.setup_hook,
        runner=_runner,
    )
    if output_format(args) == "json":
        print(json.dumps(record, indent=2))
    else:
        cli.console.print(f"[green]✓[/green] Worktree ready for {record['target']}: {record['path']}")
    return 0


def _run_worktree_import(args: argparse.Namespace, workspace, plan) -> int:
    import cc_branch.cli as cli

    record = import_agent_worktree(
        workspace,
        plan,
        args.target,
        path=Path(args.path),
        branch=args.branch,
        store=AgentWorktreeStore(),
    )
    if output_format(args) == "json":
        print(json.dumps(record, indent=2))
    else:
        cli.console.print(f"[green]✓[/green] Imported worktree for {record['target']}: {record['path']}")
    return 0


def _run_worktree_status(args: argparse.Namespace) -> int:
    import cc_branch.cli as cli

    statuses = worktree_status_for_agents(store=AgentWorktreeStore(), runner=_runner)
    if output_format(args) == "json":
        print(json.dumps(statuses, indent=2))
    elif statuses:
        for status in statuses:
            dirty = "dirty" if status.get("dirty") else "clean"
            cli.console.print(f"{status.get('target')}  {status.get('branch')}  {dirty}  {status.get('path')}")
    else:
        cli.console.print("[dim]No agent worktrees found.[/dim]")
    return 0


def _run_worktree_finish(args: argparse.Namespace) -> int:
    import cc_branch.cli as cli

    record = finish_agent_worktree(args.target, store=AgentWorktreeStore(), runner=_runner)
    if output_format(args) == "json":
        print(json.dumps(record, indent=2))
    else:
        cli.console.print(f"[green]✓[/green] Marked worktree finished for {record['target']}")
    return 0


def _run_worktree_cleanup(args: argparse.Namespace) -> int:
    import cc_branch.cli as cli

    record = cleanup_agent_worktree(args.target, store=AgentWorktreeStore(), runner=_runner, force=args.force)
    if output_format(args) == "json":
        print(json.dumps(record, indent=2))
    else:
        cli.console.print(f"[green]✓[/green] Removed worktree for {record['target']}")
    return 0
