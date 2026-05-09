"""Workspace config path resolution."""

from __future__ import annotations

from pathlib import Path

from ..constants import DEFAULT_CONFIG


def resolve_config_path(target_dir: Path) -> Path:
    """Return the canonical workspace config path."""
    return target_dir / DEFAULT_CONFIG
