"""Workspace config path resolution."""

from __future__ import annotations

from pathlib import Path

from ..constants import CONFIG_DIR, DEFAULT_CONFIG, DEFAULT_STATE


def resolve_config_path(target_dir: Path) -> Path:
    """Return the canonical workspace config path for *target_dir*."""
    return target_dir / DEFAULT_CONFIG


def resolve_state_path(target_dir: Path, config_path: Path | None = None) -> Path:
    """Return the canonical workspace state path for *target_dir*."""
    del config_path
    return target_dir / DEFAULT_STATE


def project_dir_for_config(config_path: Path) -> Path:
    """Return the project root that owns *config_path*."""
    if config_path.parent.name == CONFIG_DIR:
        return config_path.parent.parent
    return config_path.parent
