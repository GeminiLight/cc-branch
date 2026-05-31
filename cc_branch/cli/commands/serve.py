"""CLI serve command."""

from __future__ import annotations

import argparse
import ipaddress
import os

from ...context import WorkspaceContext


def is_loopback_host(host: str) -> bool:
    """Return True when host only exposes the server to the local machine."""
    normalized = host.strip().strip("[]").lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def run_serve(ctx: WorkspaceContext, args: argparse.Namespace) -> int:
    """Start the Web UI server."""
    import cc_branch.cli as cli

    from ...webui.server import start_server
    from ...webui.server.static import missing_static_assets_message, static_assets_available

    token = args.token or os.environ.get("CC_BRANCH_WEB_TOKEN")
    if not is_loopback_host(args.host) and not token:
        cli.console.print(
            "[red]✗[/red] Refusing to bind Web UI to a non-loopback host without authentication."
        )
        cli.console.print(
            "[dim]Use --token or CC_BRANCH_WEB_TOKEN when serving beyond localhost.[/dim]"
        )
        return 1

    if not static_assets_available():
        cli.console.print(f"[red]✗[/red] {missing_static_assets_message()}")
        return 1

    start_server(ctx.config_path, ctx.state_path, host=args.host, port=args.port, token=token)
    return 0
