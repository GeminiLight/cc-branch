"""CLI target help rendering."""

from __future__ import annotations

from rich.table import Table

from .constants import SHORT_ALIAS


def print_targets_help() -> None:
    """Render public target syntax help."""
    import cc_branch.cli as cli

    console = cli.console
    console.print("[bold]Targets[/bold]")
    console.print()
    console.print("Use targets to select a workspace, slot, or slot window.")
    console.print()
    table = Table(show_header=True, header_style="bold magenta", border_style="blue", padding=(0, 2))
    table.add_column("Input", style="cyan", no_wrap=True)
    table.add_column("Meaning", style="white")
    table.add_row("(empty)", "whole workspace, where the command supports it")
    table.add_row("dev", "slot named dev")
    table.add_row("dev:planner", "window named planner in slot dev")
    table.add_row("dev.planner", "legacy compatibility form for dev:planner")
    console.print(table)
    console.print()
    console.print("[dim]Examples:[/dim]")
    console.print(f"  [cyan]{SHORT_ALIAS} attach dev:planner[/cyan]")
    console.print(f"  [cyan]{SHORT_ALIAS} stop dev[/cyan]")
    console.print(f"  [cyan]{SHORT_ALIAS} session inspect dev:planner[/cyan]")
