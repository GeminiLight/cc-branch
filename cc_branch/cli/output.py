"""CLI output option helpers."""

from __future__ import annotations

import argparse


def output_format(args: argparse.Namespace) -> str:
    """Return the selected text/json output format."""
    if getattr(args, "json", False):
        return "json"
    return getattr(args, "format", "text")


def should_write_generated_state(args: argparse.Namespace) -> bool:
    """Return whether generated session metadata should be persisted."""
    return bool(
        getattr(args, "write_state", False)
        or getattr(args, "prepare", False)
    )


def status_color(status: str) -> str:
    """Return a Rich color for a session status."""
    return {
        "running": "green",
        "stopped": "yellow",
        "orphaned": "red",
    }.get(status, "white")
