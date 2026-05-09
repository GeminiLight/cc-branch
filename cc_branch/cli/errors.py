"""CLI error formatting."""

from __future__ import annotations

from pathlib import Path

from .constants import PRIMARY_COMMAND
from ..constants import DEFAULT_CONFIG


def format_file_not_found(error: FileNotFoundError) -> str:
    """Return a user-facing missing-file error message."""
    missing = Path(error.filename) if error.filename else None
    if missing and missing.name == DEFAULT_CONFIG:
        return (
            f"No workspace config found in {missing.parent}.\n\n"
            "For the guided setup, run:\n"
            f"  {PRIMARY_COMMAND} serve\n\n"
            "For the terminal setup, run:\n"
            f"  {PRIMARY_COMMAND} init\n"
            f"  {PRIMARY_COMMAND} start\n\n"
            "Or point to a config:\n"
            f"  CC_BRANCH_CONFIG=/path/to/{DEFAULT_CONFIG} {PRIMARY_COMMAND} plan"
        )
    return f"Required file not found: {missing or error}"


def print_cli_error(message: str) -> int:
    """Print a CLI error through the facade console and return failure."""
    import cc_branch.cli as cli

    cli.console.print(message)
    return 1
