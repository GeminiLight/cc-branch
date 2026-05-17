"""Atomic state repository implementation."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ..models import WorkspaceState
from .codec import state_data, yaml_to_state
from .validation import require_yaml_path

_yaml: Any | None
try:
    import yaml as _yaml
except ModuleNotFoundError:  # pragma: no cover
    _yaml = None

yaml: Any | None = _yaml


class StateRepository:
    """Repository for atomic read/write of workspace state."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> WorkspaceState:
        """Load state from disk, or return a fresh empty state."""
        if not self._path.exists():
            return WorkspaceState()
        require_yaml_path(self._path)

        if yaml is None:  # pragma: no cover
            raise RuntimeError("YAML support requires PyYAML to be installed")

        data = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise TypeError("workspace state must deserialize to a mapping")
        return yaml_to_state(data)

    def save(self, state: WorkspaceState) -> None:
        """Save state atomically with a backup of the previous file."""
        require_yaml_path(self._path)
        if yaml is None:  # pragma: no cover
            raise RuntimeError("YAML support requires PyYAML to be installed")

        content = yaml.safe_dump(
            state_data(state),
            sort_keys=False,
            allow_unicode=False,
        )
        temp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        backup_path = self._path.with_suffix(self._path.suffix + ".bak")

        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_text(content, encoding="utf-8")
        if self._path.exists():
            shutil.copy2(self._path, backup_path)
        temp_path.replace(self._path)

    def rollback(self) -> WorkspaceState:
        """Restore from the latest backup file if one exists."""
        backup_path = self._path.with_suffix(self._path.suffix + ".bak")
        if not backup_path.exists():
            raise FileNotFoundError(f"No backup found at {backup_path}")
        shutil.copy2(backup_path, self._path)
        return self.load()
