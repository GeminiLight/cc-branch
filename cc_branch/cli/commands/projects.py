"""CLI project index subcommands."""

from __future__ import annotations

import argparse
import json

from rich.table import Table

from ...app_state import ProjectIndexStore
from ..output import output_format


def run_project(args: argparse.Namespace, parser) -> int:
    """Run a project index subcommand."""
    if args.project_command in {None, "list"}:
        return _run_project_list(args)
    if args.project_command == "add":
        return _run_project_add(args)
    if args.project_command == "add-remote":
        return _run_project_add_remote(args)
    parser.error("project subcommand required")
    return 2


def _run_project_list(args: argparse.Namespace) -> int:
    import cc_branch.cli as cli

    payload = ProjectIndexStore().payload()
    if output_format(args) == "json":
        print(json.dumps(payload, indent=2))
        return 0

    raw_projects = payload.get("projects")
    projects: list[object] = raw_projects if isinstance(raw_projects, list) else []
    if not projects:
        cli.console.print("[dim]No indexed projects found.[/dim]")
        return 0
    table = Table(show_header=True, header_style="bold magenta", border_style="blue", padding=(0, 2))
    table.add_column("Active", style="white", no_wrap=True)
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="white")
    table.add_column("Remote", style="white")
    active_id = payload.get("active_project_id")
    for project in projects:
        if not isinstance(project, dict):
            continue
        remote = project.get("remote")
        remote_host = str(remote.get("host") or "") if isinstance(remote, dict) else ""
        table.add_row(
            "*" if project.get("id") == active_id else "",
            str(project.get("name") or ""),
            str(project.get("display_path") or project.get("path") or ""),
            remote_host,
        )
    cli.console.print(table)
    return 0


def _run_project_add(args: argparse.Namespace) -> int:
    import cc_branch.cli as cli

    payload = ProjectIndexStore().add_project(args.path, name=args.name)
    if output_format(args) == "json":
        print(json.dumps(payload, indent=2))
    else:
        active = _active_project(payload)
        cli.console.print(f"[green]✓[/green] Added project {active.get('name') if active else args.path}")
    return 0


def _run_project_add_remote(args: argparse.Namespace) -> int:
    import cc_branch.cli as cli

    remote: dict[str, object] = {
        "host": args.host,
        "cwd": args.cwd,
    }
    if args.user:
        remote["user"] = args.user
    if args.port:
        remote["port"] = args.port

    store = ProjectIndexStore()
    if args.dry_run:
        payload = store.preview_remote_project(remote, name=args.name, agent=args.agent)
        if output_format(args) == "json":
            print(json.dumps({"success": True, "dry_run": True, **payload}, indent=2))
        else:
            cli.console.print(f"[green]✓[/green] SSH preflight passed for {payload['display_path']}")
            cli.console.print(f"  Agent: {payload['agent']}")
            cli.console.print(f"  Local metadata path: {payload['path']}")
        return 0

    payload = store.add_remote_project(remote, name=args.name, agent=args.agent)
    if output_format(args) == "json":
        print(json.dumps(payload, indent=2))
    else:
        active = _active_project(payload)
        cli.console.print(f"[green]✓[/green] Added SSH project {active.get('name') if active else args.host}")
        if active and active.get("display_path"):
            cli.console.print(f"  Remote: {active['display_path']}")
    return 0


def _active_project(payload: dict[str, object]) -> dict[str, object] | None:
    active_id = payload.get("active_project_id")
    projects = payload.get("projects")
    if not isinstance(projects, list):
        return None
    for project in projects:
        if isinstance(project, dict) and project.get("id") == active_id:
            return project
    return None
