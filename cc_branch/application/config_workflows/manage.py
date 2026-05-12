"""Create, rename, and delete project workspace config files."""

from __future__ import annotations

import re
from pathlib import Path

from ...constants import CONFIGS_DIR
from ...config import (
    config_options_payload,
    project_dir_for_config,
    resolve_config_path,
    resolve_config_selection,
    resolve_state_path,
)
from ..results import ActionResult
from .versioning import write_text_atomic


def create_workspace_config(project_dir: Path, name: str, source_config_path: Path | None = None) -> ActionResult:
    """Create a named workspace config under ``.cc-branch/configs``."""
    target = _named_config_path(project_dir, name)
    if target.exists():
        raise ValueError(f"workspace config already exists: {target.name}")

    source = source_config_path or resolve_config_path(project_dir)
    if source.exists():
        content = source.read_text(encoding="utf-8")
    else:
        content = f'version: 2\nproject: "{project_dir.name or "workspace"}"\nroot: .\ntabs: []\n'

    target.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(target, content)
    return _managed_payload(project_dir, target, "config_created", "Workspace config created")


def rename_workspace_config(project_dir: Path, config_path: Path, name: str) -> ActionResult:
    """Rename a non-default workspace config and its associated state file."""
    source = _project_config_path(project_dir, config_path)
    if source == resolve_config_path(project_dir):
        raise ValueError("default workspace config cannot be renamed")
    if not source.exists():
        raise ValueError(f"workspace config does not exist: {source}")

    target = _named_config_path(project_dir, name)
    if target == source:
        return _managed_payload(project_dir, source, "config_renamed", "Workspace config renamed")
    if target.exists():
        raise ValueError(f"workspace config already exists: {target.name}")

    target.parent.mkdir(parents=True, exist_ok=True)
    source.rename(target)
    _rename_state_file(project_dir, source, target)
    return _managed_payload(project_dir, target, "config_renamed", "Workspace config renamed")


def delete_workspace_config(project_dir: Path, config_path: Path) -> ActionResult:
    """Delete a non-default workspace config and its local state file."""
    target = _project_config_path(project_dir, config_path)
    if target == resolve_config_path(project_dir):
        raise ValueError("default workspace config cannot be deleted")
    if not target.exists():
        raise ValueError(f"workspace config does not exist: {target}")

    state_path = resolve_state_path(project_dir, target)
    target.unlink()
    if state_path.exists():
        state_path.unlink()
    return _managed_payload(project_dir, resolve_config_path(project_dir), "config_deleted", "Workspace config deleted")


def _named_config_path(project_dir: Path, name: str) -> Path:
    slug = _slug(name)
    if not slug:
        raise ValueError("workspace config name is required")
    return project_dir / CONFIGS_DIR / f"{slug}.yaml"


def _project_config_path(project_dir: Path, config_path: Path) -> Path:
    resolved = resolve_config_selection(project_dir, config_path, restrict_to_project=True)
    if project_dir_for_config(resolved).resolve(strict=False) != project_dir.resolve(strict=False):
        raise ValueError("config_path must belong to the selected project")
    return resolved


def _rename_state_file(project_dir: Path, source_config: Path, target_config: Path) -> None:
    source_state = resolve_state_path(project_dir, source_config)
    target_state = resolve_state_path(project_dir, target_config)
    if not source_state.exists():
        return
    target_state.parent.mkdir(parents=True, exist_ok=True)
    if target_state.exists():
        target_state.unlink()
    source_state.rename(target_state)


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip(".-_").lower()


def _managed_payload(project_dir: Path, selected: Path, code: str, message: str) -> ActionResult:
    return ActionResult(
        ok=True,
        code=code,
        message=message,
        payload=config_options_payload(project_dir, selected),
    )
