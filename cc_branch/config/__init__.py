"""Workspace config facade."""

from __future__ import annotations

from pathlib import Path

from ..runtime.shells import default_shell_command
from . import initialization as _initialization
from .initialization import init_workspace as _init_workspace
from .loading import (
    load_config_data,
    load_config_data_from_text,
    load_workspace,
    load_workspace_from_text,
)
from .normalization import effective_agent_profiles, normalize_raw_config
from .paths import project_dir_for_config, resolve_config_path, resolve_state_path


def init_workspace(target_dir: Path, force: bool, bootstrap_sessions: bool) -> tuple[Path, Path]:
    """Create starter workspace config and state files."""
    _initialization.default_shell_command = default_shell_command
    return _init_workspace(target_dir, force, bootstrap_sessions)


_effective_agent_profiles = effective_agent_profiles
_load_config_data = load_config_data
_load_config_data_from_text = load_config_data_from_text
_normalize_raw_config = normalize_raw_config

__all__ = [
    "default_shell_command",
    "effective_agent_profiles",
    "init_workspace",
    "load_config_data",
    "load_config_data_from_text",
    "load_workspace",
    "load_workspace_from_text",
    "normalize_raw_config",
    "project_dir_for_config",
    "resolve_config_path",
    "resolve_state_path",
]
