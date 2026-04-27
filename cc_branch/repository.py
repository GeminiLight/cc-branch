"""State persistence with atomic writes and rollback support.

This module replaces the direct file-I/O approach in ``state.py`` with a
repository pattern that guarantees:

- Atomic writes (no half-written files)
- Backup before overwrite
- Structured access via ``WorkspaceState`` models
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .models import WindowState, WorkspaceState

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        tomllib = None


def _toml_quote(value: str) -> str:
    """Escape a string for TOML double-quoted representation.

    Handles all characters required by the TOML spec for basic strings,
    including backspace, form-feed, and control characters.
    """
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\b", "\\b")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\f", "\\f")
        .replace("\r", "\\r")
    )
    # Escape remaining control characters (0x00-0x1F except those handled above)
    result = []
    for ch in escaped:
        code = ord(ch)
        if code < 0x20 and ch not in "\b\t\n\f\r":
            result.append(f"\\u{code:04x}")
        else:
            result.append(ch)
    return f'"{"".join(result)}"'


def _state_to_toml(state: WorkspaceState) -> str:
    """Render *state* as TOML text."""
    lines = [f"version = {state.version}", ""]
    for key in sorted(state.windows):
        lines.append(f"[windows.{_toml_quote(key)}]")
        entry = state.windows[key]
        for field in sorted(vars(entry)):
            value = getattr(entry, field)
            if value in (None, ""):
                continue
            if isinstance(value, bool):
                rendered = "true" if value else "false"
            elif isinstance(value, int):
                rendered = str(value)
            else:
                rendered = _toml_quote(str(value))
            lines.append(f"{field} = {rendered}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _toml_to_state(data: dict[str, Any]) -> WorkspaceState:
    """Convert a parsed TOML dict into a ``WorkspaceState``."""
    state = WorkspaceState(
        version=int(data.get("version", 1)),
    )
    raw_windows = data.get("windows", {})
    for key, entry in raw_windows.items():
        if not isinstance(entry, dict):
            continue
        state.windows[key] = WindowState(
            session_id=entry.get("session_id"),
            label=entry.get("label"),
            agent=entry.get("agent"),
            slot=entry.get("slot"),
            window=entry.get("window"),
        )
    return state


class StateRepository:
    """Repository for atomic read/write of workspace state."""

    def __init__(self, path: Path) -> None:
        self._path = path

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load(self) -> WorkspaceState:
        """Load state from disk, or return a fresh empty state."""
        if not self._path.exists():
            return WorkspaceState()

        if tomllib is None:  # pragma: no cover
            raise RuntimeError(
                "TOML state support on Python 3.10 requires the 'tomli' package"
            )

        with self._path.open("rb") as handle:
            data = tomllib.load(handle)
        return _toml_to_state(data)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(self, state: WorkspaceState) -> None:
        """Save *state* atomically.

        Steps:
        1. Write to a temporary file in the same directory.
        2. If an existing file exists, keep it as a ``.bak``.
        3. Rename the temp file to the target path (atomic on POSIX).
        """
        content = _state_to_toml(state)
        temp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        backup_path = self._path.with_suffix(self._path.suffix + ".bak")

        # Step 1: write temp
        temp_path.write_text(content, encoding="utf-8")

        # Step 2: backup existing (if any)
        if self._path.exists():
            shutil.copy2(self._path, backup_path)

        # Step 3: atomic replace
        temp_path.replace(self._path)

    def rollback(self) -> WorkspaceState:
        """Restore from the latest ``.bak`` file if one exists."""
        backup_path = self._path.with_suffix(self._path.suffix + ".bak")
        if not backup_path.exists():
            raise FileNotFoundError(f"No backup found at {backup_path}")
        shutil.copy2(backup_path, self._path)
        return self.load()
