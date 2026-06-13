"""CLI send command."""

from __future__ import annotations

import argparse

from ...application.agent_messages import send_agent_message
from ...context import WorkspaceContext


def run_send(ctx: WorkspaceContext, args: argparse.Namespace, workspace, plan, state) -> int:
    """Send text to a managed pane."""
    del ctx, state
    result = send_agent_message(workspace, plan, args.target, " ".join(args.message))
    print(result.message)
    return 0 if result.ok else result.exit_code
