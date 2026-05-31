"""Path resolution for global app state files."""

from __future__ import annotations

from pathlib import Path


def app_home_dir() -> Path:
    """Return the global cc-branch user directory."""
    return Path.home() / ".cc-branch"


def app_data_dir() -> Path:
    """Return the directory for app-level runtime metadata."""
    return app_home_dir() / "app"


def projects_index_path() -> Path:
    """Return the global projects index file path."""
    return app_data_dir() / "projects.yaml"
