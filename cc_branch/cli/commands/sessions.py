"""CLI session subcommands."""

from __future__ import annotations

import argparse
import json

from rich.table import Table

from ...application.session_hooks import SessionHookEvent, apply_session_hook_event, normalize_session_hook_key
from ...application.session_restore import restore_sessions_from_local_transcripts
from ...application.state_store import StateStore
from ...context import WorkspaceContext
from ...text import count_label
from ..output import output_format, status_color


def run_session(ctx: WorkspaceContext, args: argparse.Namespace, workspace, plan, state, parser) -> int:
    """Run a session subcommand."""

    if args.session_command == "list" or args.session_command is None:
        return _run_session_list(args, workspace, plan, state)
    if args.session_command == "inspect":
        return _run_session_inspect(args, workspace, plan, state)
    if args.session_command == "prune":
        return _run_session_prune(ctx, args, workspace, plan, state)
    if args.session_command == "restore":
        return _run_session_restore(ctx, args, workspace, plan, state)
    if args.session_command == "command":
        return _run_session_command(args, workspace, plan, state)
    if args.session_command == "hook":
        return _run_session_hook(ctx, args)

    parser.error("session subcommand required")
    return 2


def _run_session_list(args: argparse.Namespace, workspace, plan, state) -> int:
    import cc_branch.cli as cli

    sessions = cli.list_sessions(workspace, plan, state)
    if output_format(args) == "json":
        print(json.dumps([s.__dict__ for s in sessions], indent=2))
        return 0
    if not sessions:
        cli.console.print("[dim]No sessions found.[/dim]")
        return 0

    table = Table(show_header=True, header_style="bold magenta", border_style="blue", padding=(0, 2))
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Slot", style="white")
    table.add_column("Window", style="white")
    table.add_column("Agent", style="white")
    table.add_column("Status", style="white")
    table.add_column("Session", style="white")
    for session in sessions:
        color = status_color(session.status)
        table.add_row(
            session.key,
            session.slot,
            session.window,
            session.agent or "[dim]-[/dim]",
            f"[{color}]{session.status}[/{color}]",
            _session_display(session.session_id, session.session_binding_status),
        )
    cli.console.print(table)
    return 0


def _run_session_inspect(args: argparse.Namespace, workspace, plan, state) -> int:
    import cc_branch.cli as cli

    info = cli.inspect_session(workspace, plan, state, args.key)
    if info is None:
        cli.console.print(f"[red]Session not found: {args.key}[/red]")
        return 1
    if output_format(args) == "json":
        print(json.dumps(info.__dict__, indent=2))
        return 0
    cli.console.print(f"[bold]Session:[/bold] {info.key}")
    cli.console.print(f"  Tab: {info.slot}")
    cli.console.print(f"  Pane: {info.window}")
    cli.console.print(f"  Agent: {info.agent or '[dim]none[/dim]'}")
    cli.console.print(f"  Session ID: {info.session_id or '[dim]none[/dim]'}")
    cli.console.print(f"  Session intent: {info.session_intent}")
    cli.console.print(f"  Session binding: {_binding_display(info.session_binding_status)}")
    if info.session_binding_source:
        cli.console.print(f"  Binding source: {info.session_binding_source}")
    if info.session_runtime_status:
        cli.console.print(f"  Runtime status: {info.session_runtime_status}")
    if info.session_transcript_path:
        cli.console.print(f"  Transcript: {info.session_transcript_path}")
    if info.session_hook_event:
        cli.console.print(f"  Last hook: {info.session_hook_event}")
    cli.console.print(f"  Label: {info.label or '[dim]none[/dim]'}")
    color = status_color(info.status)
    cli.console.print(f"  Status: [{color}]{info.status}[/{color}]")
    if info.launch_command:
        cli.console.print(f"  Launch command: {info.launch_command}")
    return 0


def _run_session_prune(ctx: WorkspaceContext, args: argparse.Namespace, workspace, plan, state) -> int:
    import cc_branch.cli as cli

    removed = cli.prune_sessions(workspace, plan, state, dry_run=args.dry_run)
    if args.dry_run:
        if removed:
            cli.console.print(f"[dim]Would remove {count_label(len(removed), 'stale local session record')}:[/dim]")
            for key in removed:
                cli.console.print(f"  [yellow]- {key}[/yellow]")
        else:
            cli.console.print("[dim]No stale local session records to prune.[/dim]")
        return 0

    if removed:
        StateStore(ctx.state_path).save(state)
        cli.console.print(f"[green]✓[/green] Pruned {count_label(len(removed), 'stale local session record')}:")
        for key in removed:
            cli.console.print(f"  [green]- {key}[/green]")
    else:
        cli.console.print("[dim]No stale local session records to prune.[/dim]")
    return 0


def _run_session_restore(ctx: WorkspaceContext, args: argparse.Namespace, workspace, plan, state) -> int:
    import cc_branch.cli as cli

    result = restore_sessions_from_local_transcripts(
        workspace,
        plan,
        ctx.state_path,
        state,
        target=args.target,
        agent=args.agent,
        dry_run=args.dry_run,
        force=args.force,
        limit=args.limit,
        session_id=args.session_id,
    )
    payload = {
        "success": result.ok,
        "code": result.code,
        "message": result.message,
        "changed_targets": list(result.changed_targets),
        "warnings": list(result.warnings),
        **result.payload,
    }
    if output_format(args) == "json":
        print(json.dumps(payload, indent=2))
        return 0 if result.ok else result.exit_code
    if result.changed_targets:
        marker = "[yellow]Preview[/yellow]" if args.dry_run else "[green]✓[/green]"
        cli.console.print(f"{marker} {result.message}:")
        for target in result.changed_targets:
            cli.console.print(f"  [green]- {target}[/green]")
    else:
        cli.console.print(f"[dim]{result.message}[/dim]")
    skipped = result.payload.get("skipped")
    if isinstance(skipped, list) and skipped:
        cli.console.print("[dim]Skipped:[/dim]")
        for item in skipped:
            if isinstance(item, dict):
                cli.console.print(f"  [dim]- {item.get('target')}: {item.get('reason')}[/dim]")
    return 0 if result.ok else result.exit_code


def _run_session_command(args: argparse.Namespace, workspace, plan, state) -> int:
    import cc_branch.cli as cli

    command = cli.restore_session(workspace, plan, state, args.key)
    if command is None:
        cli.console.print(f"[red]Cannot build launch command for: {args.key}[/red]")
        return 1
    cli.console.print(f"[dim]Launch command for {args.key}:[/dim]")
    cli.console.print(command)
    return 0


def _run_session_hook(ctx: WorkspaceContext, args: argparse.Namespace) -> int:
    import cc_branch.cli as cli

    updated = apply_session_hook_event(
        ctx.state_path,
        SessionHookEvent(
            key=args.key,
            event=args.event,
            agent=args.agent,
            session_id=args.session_id,
            transcript_path=args.transcript,
            label=args.label,
            pid=args.pid,
            exit_code=args.exit_code,
            timestamp=args.timestamp,
        ),
    )
    key = normalize_session_hook_key(args.key)
    entry = updated.windows[key]
    payload = {"key": key, **entry.to_dict()}
    if output_format(args) == "json":
        print(json.dumps(payload, indent=2))
        return 0
    cli.console.print(
        f"[green]✓[/green] Recorded {args.event} hook for {key}"
        f"{f' ({entry.session_id})' if entry.session_id else ''}"
    )
    return 0


def _session_display(session_id: str | None, binding_status: str) -> str:
    if binding_status == "fresh":
        return _binding_display(binding_status)
    if session_id:
        return f"bound {session_id[:8]}"
    return _binding_display(binding_status)


def _binding_display(status: str) -> str:
    return {
        "bound": "bound",
        "will_bootstrap": "will save id",
        "will_capture": "will detect",
        "will_create": "will start",
        "pending_capture": "detecting",
        "ambiguous": "needs choice",
        "capture_failed": "capture failed",
        "fresh": "fresh",
        "none": "-",
    }.get(status, status or "-")
