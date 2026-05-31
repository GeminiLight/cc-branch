"""CLI init command."""

from __future__ import annotations

import argparse
from pathlib import Path

from ...constants import DEFAULT_CONFIG
from ...runtime.shells import tmux_install_hint
from ..constants import PRIMARY_COMMAND


def run_init(cwd: Path, args: argparse.Namespace) -> int:
    """Initialize a workspace from the CLI."""
    import cc_branch.cli as cli

    config_path = cli.resolve_config_path(cwd)
    if config_path.exists() and not args.force:
        _print_existing_config_error(config_path)
        return 1

    if args.minimal:
        return _run_minimal_init(cwd, args)

    return _run_guided_init(cwd, args)


def _print_existing_config_error(config_path: Path) -> None:
    import cc_branch.cli as cli

    console = cli.console
    console.print()
    console.print("[red]✗[/red] Initialization failed")
    console.print()
    console.print(f"  {config_path.name} already exists")
    console.print()
    console.print("[dim]Options:[/dim]")
    console.print("  • Use [cyan]--force[/cyan] to overwrite existing config")
    console.print(f"  • Edit [cyan]{DEFAULT_CONFIG}[/cyan] manually")
    console.print("  • Delete the file and run init again")
    console.print()


def _run_minimal_init(cwd: Path, args: argparse.Namespace) -> int:
    import cc_branch.cli as cli

    result = cli.initialize_minimal_workspace(
        cwd,
        force=args.force,
        bootstrap_sessions=False,
    )
    config_path = Path(result.payload["config_path"])
    state_path = Path(result.payload["state_path"])
    cli.console.print()
    cli.console.print(f"[green]✓[/green] Created {config_path.name}")
    cli.console.print(f"[green]✓[/green] Created {state_path.name}")
    cli.console.print()
    cli.console.print(f"[dim]Config created. Edit {DEFAULT_CONFIG} to customize.[/dim]")
    cli.console.print("[dim]Run 'cc-branch plan' to preview before launch.[/dim]")
    cli.console.print()
    return 0


def _run_guided_init(cwd: Path, args: argparse.Namespace) -> int:
    import cc_branch.cli as cli

    console = cli.console
    console.print()
    console.print("[cyan]Checking environment...[/cyan]")
    console.print()

    env_result = cli.inspect_workspace_environment(cwd)
    env_report = env_result.payload["environment"]

    _print_environment_report(env_report)

    if not env_report.can_proceed:
        console.print("[red]✗[/red] Cannot proceed: no write permission")
        console.print()
        console.print("[dim]→ Check directory permissions: ls -la[/dim]")
        console.print("[dim]→ Or run in a directory where you have write access[/dim]")
        console.print()
        return 1

    if not env_report.available_agents:
        console.print("[yellow]⚠[/yellow] No AI agent CLIs detected")
        console.print()
        console.print("[dim]You can still create a workspace, but it will only have shell panes.[/dim]")
        console.print("[dim]Install at least one agent CLI for AI-powered workflows.[/dim]")
        console.print()

    console.print("[cyan]Generating config...[/cyan]")
    console.print()

    try:
        result = cli.initialize_workspace_from_environment(
            cwd,
            profile=args.profile,
            available_agents=env_report.available_agents,
            tmux_available=env_report.tmux_available,
            bootstrap_sessions=False,
        )
    except ValueError as error:
        console.print(f"[red]✗[/red] Invalid profile: {error}")
        console.print()
        available = [profile["id"] for profile in cli.profile_options().payload["profiles"]]
        console.print(f"[dim]Available profiles: {', '.join(available)}[/dim]")
        console.print()
        return 1

    _print_init_result(result.payload, env_report.available_agents)
    return 0


def _print_environment_report(env_report) -> None:
    import cc_branch.cli as cli

    console = cli.console
    console.print("[bold]Environment Check:[/bold]")
    if env_report.tmux_available:
        console.print(f"  [green]✓[/green] tmux: ok ({env_report.tmux_path})")
    else:
        console.print("  [yellow]⚠[/yellow] tmux runtime: unavailable")
        console.print("    [dim]→ Starter config will use direct-layout tabs.[/dim]")
        console.print(f"    [dim]→ Install tmux later to enable reusable tmux workspaces: {tmux_install_hint()}[/dim]")

    console.print()
    if env_report.agents:
        console.print("[bold]Agent CLIs:[/bold]")
        for agent in env_report.agents:
            if agent.status == "ok":
                console.print(f"  [green]✓[/green] {agent.name}: ok ({agent.command})")
            else:
                console.print(f"  [red]✗[/red] {agent.name}: missing")
                console.print(f"    [dim]→ {agent.install_hint}[/dim]")

    console.print()
    console.print("[bold]Config:[/bold]")
    if env_report.config_exists:
        console.print(f"  [yellow]⚠[/yellow] {DEFAULT_CONFIG}: exists")
    elif env_report.available_agents:
        console.print(f"  [yellow]⚠[/yellow] {DEFAULT_CONFIG}: missing")
        console.print(
            f"    [dim]→ Will create starter config with {len(env_report.available_agents)} agent(s)[/dim]"
        )
    else:
        console.print(f"  [yellow]⚠[/yellow] {DEFAULT_CONFIG}: missing")
        console.print("    [dim]→ Will create minimal config with shell workspace[/dim]")
    console.print()


def _print_init_result(payload: dict, available_agents: list[str]) -> None:
    import cc_branch.cli as cli

    console = cli.console
    config_path = Path(payload["config_path"])
    state_path = Path(payload["state_path"])
    summary = payload["summary"]
    state_windows = payload.get("state_windows", [])
    console.print(f"[green]✓[/green] Created {config_path.name}")
    console.print(f"  [dim]- {summary['slots']} tabs[/dim]")
    console.print(f"  [dim]- {summary['windows']} panes[/dim]")
    console.print(f"  [dim]- {summary['agents']} agents[/dim]")
    console.print()

    if available_agents:
        _print_bootstrap_summary(state_path, state_windows)
    else:
        console.print(f"[green]✓[/green] Created {state_path.name} (empty)")
        console.print()

    if payload["gitignore_created"]:
        console.print("[green]✓[/green] Created .gitignore")
        console.print()
    elif payload["gitignore_updated"]:
        console.print("[green]✓[/green] Updated .gitignore")
        console.print()

    console.print("[green]✓[/green] [bold]Workspace initialized successfully![/bold]")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  1. Review config: [cyan]cat {DEFAULT_CONFIG}[/cyan]")
    console.print(f"  2. Check status: [cyan]{PRIMARY_COMMAND} doctor[/cyan]")
    console.print(f"  3. Start workspace: [cyan]{PRIMARY_COMMAND} start[/cyan]")
    console.print()
    console.print(f"[dim]Tip: Use '{PRIMARY_COMMAND} plan' to preview the launch plan before starting.[/dim]")
    console.print()


def _print_bootstrap_summary(state_path: Path, state_windows: list[dict]) -> None:
    import cc_branch.cli as cli

    console = cli.console
    console.print("[cyan]Bootstrapping session metadata...[/cyan]")
    console.print()
    num_sessions = len(state_windows)
    if num_sessions > 0:
        console.print(f"[green]✓[/green] Generated {num_sessions} session ID(s)")
        for entry in state_windows[:3]:
            key = entry["key"]
            session_id = entry["session_id"]
            short_id = session_id[:8] + "..." if len(session_id) > 8 else session_id
            console.print(f"  [dim]- {key} → {short_id}[/dim]")
        if num_sessions > 3:
            console.print(f"  [dim]- ... and {num_sessions - 3} more[/dim]")
    else:
        console.print("[yellow]⊘[/yellow] No sessions to bootstrap (shell-only workspace)")
    console.print()
    console.print(f"[green]✓[/green] Created {state_path.name}")
    console.print()
