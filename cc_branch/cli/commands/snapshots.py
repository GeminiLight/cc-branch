"""CLI workspace snapshot subcommands."""

from __future__ import annotations

import argparse
import json

from ...application.workspace_snapshots import (
    WorkspaceSnapshotStore,
    capture_workspace_snapshot,
    restore_workspace_snapshot,
)
from ...context import WorkspaceContext
from ..output import output_format


def run_snapshot(ctx: WorkspaceContext, args: argparse.Namespace, workspace, plan, state, parser) -> int:
    if args.snapshot_command in {None, "list"}:
        return _run_snapshot_list(args)
    if args.snapshot_command == "create":
        return _run_snapshot_create(ctx, args, workspace, plan, state)
    if args.snapshot_command == "restore":
        return _run_snapshot_restore(args)
    parser.error("snapshot subcommand required")
    return 2


def _run_snapshot_create(ctx: WorkspaceContext, args: argparse.Namespace, workspace, plan, state) -> int:
    import cc_branch.cli as cli

    snapshot = capture_workspace_snapshot(
        workspace,
        plan,
        state,
        config_path=ctx.config_path,
        state_path=ctx.state_path,
        name=args.name,
    )
    if output_format(args) == "json":
        print(json.dumps(snapshot, indent=2))
    else:
        cli.console.print(f"[green]✓[/green] Captured snapshot {snapshot['name']} ({snapshot['id']})")
    return 0


def _run_snapshot_list(args: argparse.Namespace) -> int:
    import cc_branch.cli as cli

    snapshots = WorkspaceSnapshotStore().list()
    if output_format(args) == "json":
        print(json.dumps(snapshots, indent=2))
    elif snapshots:
        for snapshot in snapshots:
            cli.console.print(f"{snapshot.get('id')}  {snapshot.get('name')}  {snapshot.get('created_at')}")
    else:
        cli.console.print("[dim]No snapshots found.[/dim]")
    return 0


def _run_snapshot_restore(args: argparse.Namespace) -> int:
    import cc_branch.cli as cli

    result = restore_workspace_snapshot(args.snapshot_id)
    if output_format(args) == "json":
        print(json.dumps(result, indent=2))
    else:
        cli.console.print(f"[green]✓[/green] Restored snapshot {result['name']} to {result['state_path']}")
    return 0
