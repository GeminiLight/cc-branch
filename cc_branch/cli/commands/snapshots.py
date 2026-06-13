"""CLI workspace snapshot subcommands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...application.workspace_snapshots import (
    WorkspaceSnapshotStore,
    capture_workspace_snapshot,
    export_workspace_snapshot,
    import_workspace_snapshot,
    preview_workspace_snapshot_restore,
    restore_workspace_snapshot,
)
from ...context import WorkspaceContext
from ..output import output_format


def run_snapshot(ctx: WorkspaceContext, args: argparse.Namespace, workspace, plan, state, parser) -> int:
    if args.snapshot_command in {None, "list"}:
        return _run_snapshot_list(args)
    if args.snapshot_command == "create":
        return _run_snapshot_create(ctx, args, workspace, plan, state)
    if args.snapshot_command == "show":
        return _run_snapshot_show(args)
    if args.snapshot_command == "preview":
        return _run_snapshot_preview(args)
    if args.snapshot_command == "restore":
        return _run_snapshot_restore(args)
    if args.snapshot_command == "export":
        return _run_snapshot_export(args)
    if args.snapshot_command == "import":
        return _run_snapshot_import(args)
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

    result = restore_workspace_snapshot(
        args.snapshot_id,
        state_path=Path(args.state_path) if args.state_path else None,
        dry_run=args.dry_run,
    )
    if output_format(args) == "json":
        print(json.dumps(result, indent=2))
    else:
        if args.dry_run:
            _print_preview(result)
        else:
            cli.console.print(f"[green]✓[/green] Restored snapshot {result['name']} to {result['state_path']}")
    return 0


def _run_snapshot_show(args: argparse.Namespace) -> int:
    import cc_branch.cli as cli

    snapshot = WorkspaceSnapshotStore().get(args.snapshot_id)
    if output_format(args) == "json":
        print(json.dumps(snapshot, indent=2))
    else:
        cli.console.print(f"[bold]{snapshot.get('name')}[/bold] ({snapshot.get('id')})")
        cli.console.print(f"  Created: {snapshot.get('created_at')}")
        cli.console.print(f"  Project: {snapshot.get('project')}")
        cli.console.print(f"  State: {snapshot.get('state_path')}")
        cli.console.print(f"  Config: {snapshot.get('config_path')}")
    return 0


def _run_snapshot_preview(args: argparse.Namespace) -> int:
    result = preview_workspace_snapshot_restore(
        args.snapshot_id,
        state_path=Path(args.state_path) if args.state_path else None,
    )
    if output_format(args) == "json":
        print(json.dumps(result, indent=2))
    else:
        _print_preview(result)
    return 0


def _run_snapshot_export(args: argparse.Namespace) -> int:
    import cc_branch.cli as cli

    result = export_workspace_snapshot(args.snapshot_id, Path(args.output))
    if output_format(args) == "json":
        print(json.dumps(result, indent=2))
    else:
        cli.console.print(f"[green]✓[/green] Exported snapshot {result['name']} to {result['path']}")
    return 0


def _run_snapshot_import(args: argparse.Namespace) -> int:
    import cc_branch.cli as cli

    result = import_workspace_snapshot(Path(args.path), name=args.name)
    if output_format(args) == "json":
        print(json.dumps(result, indent=2))
    else:
        cli.console.print(f"[green]✓[/green] Imported snapshot {result['name']} ({result['snapshot_id']})")
    return 0


def _print_preview(result: dict[str, object]) -> None:
    import cc_branch.cli as cli

    raw_summary = result.get("summary")
    summary = raw_summary if isinstance(raw_summary, dict) else {}
    raw_windows = summary.get("windows")
    raw_slots = summary.get("slots")
    windows = raw_windows if isinstance(raw_windows, dict) else {}
    slots = raw_slots if isinstance(raw_slots, dict) else {}
    cli.console.print(f"[yellow]Preview[/yellow] snapshot {result.get('name')} -> {result.get('state_path')}")
    cli.console.print(
        "  Windows: "
        f"+{windows.get('added', 0)} "
        f"~{windows.get('changed', 0)} "
        f"-{windows.get('removed', 0)} "
        f"={windows.get('unchanged', 0)}"
    )
    cli.console.print(
        "  Slots: "
        f"+{slots.get('added', 0)} "
        f"~{slots.get('changed', 0)} "
        f"-{slots.get('removed', 0)} "
        f"={slots.get('unchanged', 0)}"
    )
