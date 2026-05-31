from __future__ import annotations

import shlex
from pathlib import Path

from ..models import SlotConfig, WindowConfig


def _apply_env(command: str, env: dict) -> str:
    """Prefix *command* with ``env KEY=val ...`` when env vars are present."""
    if not command or not env:
        return command
    assignments = " ".join(
        f"{key}={shlex.quote(str(value))}"
        for key, value in sorted(env.items())
        if value is not None
    )
    if not assignments:
        return command
    return f"env {assignments} {command}"


def _resolve_slot_cwd(workspace_root: str, slot: SlotConfig) -> Path:
    """Resolve a slot's working directory."""
    return (Path(workspace_root) / slot.cwd).resolve()


def _resolve_window_cwd(workspace_root: str, slot: SlotConfig, window: WindowConfig) -> str:
    """Resolve a window's working directory."""
    if not window.cwd:
        return str(_resolve_slot_cwd(workspace_root, slot))
    window_path = Path(window.cwd)
    if window_path.is_absolute():
        return str(window_path.resolve())
    base_dir = _resolve_slot_cwd(workspace_root, slot) if slot.cwd else Path(workspace_root)
    return str((base_dir / window_path).resolve())
