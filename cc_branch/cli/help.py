from __future__ import annotations

import argparse

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .constants import PRIMARY_COMMAND, SHORT_ALIAS, console
from .parser import build_parser


def print_help():
    """Display a beautiful help message using rich."""
    parser = build_parser()
    command_action = _subparser_action(parser)

    # Create title
    title = Text()
    title.append(SHORT_ALIAS, style="bold cyan")
    title.append(" - CC Branch", style="bold white")

    # Create description
    description = Text("Multi-agent workspace orchestrator for shell and tmux runtimes", style="dim")

    # Create commands table
    table = Table(show_header=True, header_style="bold magenta", border_style="blue", padding=(0, 2))
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    commands = [
        (name, subparser.description or "")
        for name, subparser in command_action.choices.items()
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    # Print everything
    console.print()
    console.print(Panel(title, border_style="cyan"))
    console.print()
    console.print(description)
    console.print()
    console.print(table)
    console.print()
    console.print(f"[dim]Usage:[/dim] [cyan]{SHORT_ALIAS}[/cyan] [yellow]<command>[/yellow] [dim][options][/dim]")
    console.print(
        f"[dim]For command-specific help:[/dim] [cyan]{SHORT_ALIAS}[/cyan] "
        f"[yellow]<command>[/yellow] [cyan]--help[/cyan]"
    )
    console.print(f"[dim]Also available as:[/dim] [cyan]{PRIMARY_COMMAND}[/cyan]")
    console.print()


def print_command_help(command: str):
    """Display help for a specific command."""
    parser = build_parser()
    command_parser = _parser_for_command(parser, command.split())
    if command_parser is None:
        console.print(f"[red]Unknown command: {command}[/red]")
        return

    # Title
    title = Text()
    title.append(f"{SHORT_ALIAS} ", style="bold cyan")
    title.append(command, style="bold yellow")

    console.print()
    console.print(Panel(title, border_style="cyan"))
    console.print()
    console.print(Text(command_parser.description or "", style="white"))
    console.print()
    usage = command_parser.format_usage().replace("usage: ", "").strip()
    console.print("[dim]Usage:[/dim]", usage)
    console.print()

    rows = _help_rows(command_parser)
    if rows:
        table = Table(show_header=True, header_style="bold magenta", border_style="blue", padding=(0, 2))
        table.add_column("Option", style="yellow", no_wrap=True)
        table.add_column("Description", style="white")

        for opt, desc in rows:
            table.add_row(opt, desc)

        console.print(table)
        console.print()

    examples = _HELP_EXAMPLES.get(command)
    if examples:
        console.print("[dim]Examples:[/dim]")
        for example in examples:
            console.print(f"  [cyan]{example}[/cyan]")
        console.print()


_HELP_EXAMPLES = {
    "attach": [f"{SHORT_ALIAS} attach dev", f"{SHORT_ALIAS} attach dev:planner"],
    "open": [f"{SHORT_ALIAS} open", f"{SHORT_ALIAS} open dev:planner --opener vscode", f"{SHORT_ALIAS} open --project-dir --opener cursor"],
    "start": [f"{SHORT_ALIAS} start", f"{SHORT_ALIAS} start --detach", f"{SHORT_ALIAS} start --dashboard"],
    "session": [
        f"{SHORT_ALIAS} session list",
        f"{SHORT_ALIAS} session inspect dev:planner",
        f"{SHORT_ALIAS} session command dev:planner",
    ],
}


def _subparser_action(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise RuntimeError("parser has no subcommands")


def _parser_for_command(
    parser: argparse.ArgumentParser, command_path: list[str]
) -> argparse.ArgumentParser | None:
    current = parser
    for part in command_path:
        action = _subparser_action(current)
        next_parser = action.choices.get(part)
        if not isinstance(next_parser, argparse.ArgumentParser):
            return None
        current = next_parser
    return current


def _help_rows(parser: argparse.ArgumentParser) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for action in parser._actions:
        if action.help == argparse.SUPPRESS:
            continue
        if isinstance(action, argparse._HelpAction):
            continue
        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                rows.append((name, subparser.description or ""))
            continue
        rows.append((_action_display(action), action.help or ""))
    return rows


def _action_display(action: argparse.Action) -> str:
    if action.option_strings:
        if action.nargs == 0:
            return ", ".join(action.option_strings)
        metavar = action.metavar or action.dest.upper()
        return ", ".join(f"{opt} {metavar}" for opt in action.option_strings)
    name = action.metavar or action.dest
    if action.nargs == "?":
        return f"[{name}]"
    return f"<{name}>"
