"""CLI open command."""

from __future__ import annotations

import argparse

from ...config import project_dir_for_config
from ...context import WorkspaceContext
from ...openers import OpenIntent
from ..constants import PRIMARY_COMMAND


def run_open(ctx: WorkspaceContext, args: argparse.Namespace) -> int:
    """Open the workspace or a target with the selected opener."""
    import cc_branch.cli as cli

    workspace, plan = ctx.load(bootstrap_missing=True)
    state = ctx.state
    opener = args.opener or plan.default_opener or "auto-terminal"
    intent = OpenIntent(kind="project_folder") if args.project_dir else None
    result = cli.open_workspace_action(
        workspace,
        plan,
        state,
        ctx.state_path,
        cwd=project_dir_for_config(ctx.config_path),
        cli=PRIMARY_COMMAND,
        opener=opener,
        target=args.target,
        intent=intent,
    )
    if result.ok:
        cli.console.print(f"[green]✓[/green] {result.message}")
    else:
        cli.console.print(f"[red]{result.message}[/red]")
    return result.exit_code
