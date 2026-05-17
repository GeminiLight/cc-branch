"""Workspace config loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import WorkspaceConfig
from .normalization import normalize_raw_config

_yaml: Any | None
try:
    import yaml as _yaml
except ModuleNotFoundError:  # pragma: no cover
    _yaml = None

yaml: Any | None = _yaml


def load_config_data(path: Path) -> dict:
    """Parse a YAML config file into a raw dict."""
    return load_config_data_from_text(path.read_text(encoding="utf-8"), path)


def load_config_data_from_text(content: str, path: Path) -> dict:
    """Parse YAML config content into a raw dict."""
    suffix = path.suffix.lower()
    if suffix not in {".yaml", ".yml"}:
        raise ValueError(f"unsupported config format: {path.suffix}; use YAML")
    if yaml is None:  # pragma: no cover
        raise RuntimeError("YAML support requires PyYAML to be installed")

    data = yaml.safe_load(content) or {}
    if not isinstance(data, dict):
        raise TypeError("workspace config must deserialize to a mapping")
    return data


def load_workspace(path: Path) -> WorkspaceConfig:
    """Load workspace configuration."""
    raw = load_config_data(path)
    normalized = normalize_raw_config(raw, path)
    return WorkspaceConfig.from_dict(normalized)


def load_workspace_from_text(content: str, path: Path) -> WorkspaceConfig:
    """Load workspace configuration from unsaved text using *path* as base."""
    raw = load_config_data_from_text(content, path)
    normalized = normalize_raw_config(raw, path)
    return WorkspaceConfig.from_dict(normalized)
