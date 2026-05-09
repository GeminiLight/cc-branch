"""Repository input validation."""

from __future__ import annotations

from pathlib import Path


def require_yaml_path(path: Path) -> None:
    """Require YAML state paths."""
    if path.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError(f"unsupported state format: {path.suffix}; use YAML")
