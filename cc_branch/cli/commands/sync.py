"""CLI sync command."""

from __future__ import annotations

import argparse

from ...context import WorkspaceContext


def run_sync(ctx: WorkspaceContext, args: argparse.Namespace, workspace, plan, state) -> int:
    """Synchronize desired workspace state with the runtime."""
    import cc_branch.cli as cli

    if getattr(args, "dry_run", False) or not getattr(args, "yes", False):
        result = cli.sync_workspace(
            workspace,
            plan,
            state,
            ctx.state_path,
            target=args.target,
            stop_removed=getattr(args, "stop_removed", False),
            apply_changes=False,
        )
        extra_targets = result.payload.get("extra_targets", ())
        if result.changed_targets or extra_targets:
            cli.console.print("[bold]Runtime changes to sync:[/bold]")
            for target in result.changed_targets:
                cli.console.print(f"  - restart {target}")
            for target in extra_targets:
                cli.console.print(f"  - stop extra {target}")
            if not getattr(args, "yes", False):
                cli.console.print("[dim]Run with --yes to sync these changes.[/dim]")
        else:
            cli.console.print("[dim]No changed, missing, or untracked tmux windows need sync.[/dim]")
        return 0

    result = cli.sync_workspace(
        workspace,
        plan,
        state,
        ctx.state_path,
        target=args.target,
        stop_removed=getattr(args, "stop_removed", False),
        apply_changes=True,
    )
    stopped_extra = result.payload.get("stopped_extra", ())
    if result.changed_targets or stopped_extra:
        cli.console.print(f"[green]✓[/green] {result.message}.")
    else:
        cli.console.print("[dim]No changed, missing, or untracked tmux windows need sync.[/dim]")
    return 0
