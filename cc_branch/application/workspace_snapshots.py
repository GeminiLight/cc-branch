"""Workspace snapshot capture and restore."""

from __future__ import annotations

import json
import base64
import hashlib
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, cast

from ..app_state.paths import app_data_dir
from ..models import WorkspaceConfig, WorkspacePlan, WorkspaceState
from ..config import load_workspace
from ..planner import plan_workspace
from ..state import load_state
from ..state import save_state
from .workspace_status import SessionExists, WindowExists, build_workspace_status

Clock = Callable[[], str]
GitProbe = Callable[[Path], dict[str, object]]

DEFAULT_EXCLUDED_FILE_DIRS = {
    ".git",
    ".cc-branch/app",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
}
DEFAULT_MAX_FILE_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 50 * 1024 * 1024


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class WorkspaceSnapshotStore:
    """JSON-backed local snapshot store."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_data_dir() / "snapshots.json"

    def list(self) -> list[dict[str, object]]:
        return list(cast(list[dict[str, object]], self._data()["snapshots"]))

    def get(self, snapshot_id: str) -> dict[str, object]:
        for snapshot in self.list():
            if snapshot.get("id") == snapshot_id or snapshot.get("name") == snapshot_id:
                return snapshot
        raise ValueError(f"Snapshot not found: {snapshot_id}")

    def save(self, snapshot: dict[str, object]) -> dict[str, object]:
        snapshots = [item for item in self.list() if item.get("id") != snapshot.get("id")]
        snapshots.append(snapshot)
        snapshots.sort(key=lambda item: str(item.get("created_at") or ""))
        self._write({"version": 1, "snapshots": snapshots})
        return snapshot

    def _data(self) -> dict[str, object]:
        if not self.path.exists():
            return {"version": 1, "snapshots": []}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"version": 1, "snapshots": []}
        if not isinstance(raw, dict):
            return {"version": 1, "snapshots": []}
        snapshots = raw.get("snapshots")
        if not isinstance(snapshots, list):
            snapshots = []
        return {
            "version": int(raw.get("version") or 1),
            "snapshots": [cast(dict[str, object], item) for item in snapshots if isinstance(item, dict)],
        }

    def _write(self, data: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp_path.replace(self.path)


def capture_workspace_snapshot(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    state: WorkspaceState,
    *,
    config_path: Path,
    state_path: Path,
    store: WorkspaceSnapshotStore | None = None,
    name: str | None = None,
    now: Clock = _utc_now,
    git_probe: GitProbe | None = None,
    session_exists: SessionExists | None = None,
    window_exists: WindowExists | None = None,
    include_files: bool = False,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> dict[str, object]:
    """Capture workspace config/state/runtime status into a local snapshot."""
    store = store or WorkspaceSnapshotStore()
    created_at = now()
    status = build_workspace_status(
        workspace,
        plan,
        state,
        config_path=config_path,
        state_path=state_path,
        session_exists=session_exists,
        window_exists=window_exists,
    )
    snapshot = {
        "id": uuid.uuid4().hex,
        "name": name or f"{workspace.project or 'workspace'}-{created_at}",
        "created_at": created_at,
        "project": workspace.project,
        "root": str(workspace.root),
        "config_path": str(config_path),
        "state_path": str(state_path),
        "git": (git_probe or probe_git)(Path(str(workspace.root))),
        "slots": status.get("slots", []),
        "agents": status.get("agents", []),
        "runtime_sync": status.get("runtime_sync"),
        "state": state.to_dict(),
    }
    if include_files:
        snapshot["files"] = capture_workspace_files(
            Path(str(workspace.root)),
            max_file_bytes=max_file_bytes,
            max_total_bytes=max_total_bytes,
        )
    return store.save(snapshot)


def restore_workspace_snapshot(
    snapshot_id: str,
    *,
    store: WorkspaceSnapshotStore | None = None,
    state_path: Path | None = None,
    dry_run: bool = False,
    restore_files: bool | None = None,
) -> dict[str, object]:
    """Restore saved session/runtime metadata from a snapshot into state.yaml."""
    store = store or WorkspaceSnapshotStore()
    snapshot = store.get(snapshot_id)
    target_state_path = state_path or Path(str(snapshot.get("state_path") or ""))
    if not target_state_path:
        raise ValueError("Snapshot does not include a state path")
    raw_state = snapshot.get("state")
    if not isinstance(raw_state, dict):
        raise ValueError("Snapshot does not include restorable state")
    if dry_run:
        preview = preview_workspace_snapshot_restore(snapshot_id, store=store, state_path=target_state_path)
        return {"success": True, "dry_run": True, **preview}
    files_payload = snapshot.get("files")
    should_restore_files = bool(files_payload) if restore_files is None else restore_files
    file_result: dict[str, object] | None = None
    if should_restore_files and isinstance(files_payload, dict):
        file_result = restore_workspace_files(files_payload)
    save_state(target_state_path, WorkspaceState.from_dict(raw_state))
    result = {
        "success": True,
        "snapshot_id": snapshot.get("id"),
        "name": snapshot.get("name"),
        "state_path": str(target_state_path),
        "config_path": snapshot.get("config_path"),
        "files_restored": bool(file_result),
    }
    if file_result:
        result["files"] = file_result
    return result


def preview_workspace_snapshot_restore(
    snapshot_id: str,
    *,
    store: WorkspaceSnapshotStore | None = None,
    state_path: Path | None = None,
) -> dict[str, object]:
    """Return a dry-run diff of what restoring a snapshot would change."""
    store = store or WorkspaceSnapshotStore()
    snapshot = store.get(snapshot_id)
    target_state_path = state_path or Path(str(snapshot.get("state_path") or ""))
    if not target_state_path:
        raise ValueError("Snapshot does not include a state path")
    raw_state = snapshot.get("state")
    if not isinstance(raw_state, dict):
        raise ValueError("Snapshot does not include restorable state")
    snapshot_state = WorkspaceState.from_dict(raw_state).to_dict()
    current_state = load_state(target_state_path).to_dict() if target_state_path.exists() else WorkspaceState().to_dict()
    window_changes = _state_section_diff(
        cast(dict[str, object], current_state.get("windows") or {}),
        cast(dict[str, object], snapshot_state.get("windows") or {}),
    )
    slot_changes = _state_section_diff(
        cast(dict[str, object], current_state.get("slots") or {}),
        cast(dict[str, object], snapshot_state.get("slots") or {}),
    )
    file_changes: dict[str, object] | None = None
    files_payload = snapshot.get("files")
    if isinstance(files_payload, dict):
        file_changes = preview_workspace_files_restore(files_payload)
    return {
        "snapshot_id": snapshot.get("id"),
        "name": snapshot.get("name"),
        "created_at": snapshot.get("created_at"),
        "state_path": str(target_state_path),
        "config_path": snapshot.get("config_path"),
        "git": snapshot.get("git"),
        "changes": {
            "windows": window_changes,
            "slots": slot_changes,
            **({"files": file_changes} if file_changes is not None else {}),
        },
        "summary": {
            "windows": _section_counts(window_changes),
            "slots": _section_counts(slot_changes),
            **({"files": _section_counts(file_changes)} if file_changes is not None else {}),
        },
    }


def export_workspace_snapshot(
    snapshot_id: str,
    output_path: Path,
    *,
    store: WorkspaceSnapshotStore | None = None,
    now: Clock = _utc_now,
) -> dict[str, object]:
    """Export a snapshot to a portable JSON file."""
    store = store or WorkspaceSnapshotStore()
    snapshot = store.get(snapshot_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "exported_at": now(),
        "snapshot": snapshot,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "success": True,
        "snapshot_id": snapshot.get("id"),
        "name": snapshot.get("name"),
        "path": str(output_path),
    }


def import_workspace_snapshot(
    input_path: Path,
    *,
    store: WorkspaceSnapshotStore | None = None,
    name: str | None = None,
    now: Clock = _utc_now,
) -> dict[str, object]:
    """Import a snapshot JSON file into the local snapshot store."""
    store = store or WorkspaceSnapshotStore()
    try:
        raw = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid snapshot export: {input_path}") from error
    if isinstance(raw, dict) and isinstance(raw.get("snapshot"), dict):
        snapshot = dict(cast(dict[str, object], raw["snapshot"]))
    elif isinstance(raw, dict) and isinstance(raw.get("state"), dict):
        snapshot = dict(cast(dict[str, object], raw))
    else:
        raise ValueError("Snapshot export does not include a snapshot")
    if not isinstance(snapshot.get("state"), dict):
        raise ValueError("Snapshot export does not include restorable state")

    existing_ids = {str(item.get("id") or "") for item in store.list()}
    original_id = str(snapshot.get("id") or "")
    if not original_id or original_id in existing_ids:
        snapshot["id"] = uuid.uuid4().hex
        if original_id:
            snapshot["original_id"] = original_id
    if name:
        snapshot["name"] = name
    elif not str(snapshot.get("name") or "").strip():
        snapshot["name"] = f"imported-{snapshot['id']}"
    snapshot["imported_at"] = now()
    snapshot["imported_from"] = str(input_path)
    saved = store.save(snapshot)
    return {
        "success": True,
        "snapshot_id": saved.get("id"),
        "name": saved.get("name"),
        "imported_from": str(input_path),
    }


def capture_snapshot_for_workspace(
    config_path: Path,
    state_path: Path,
    *,
    name: str | None = None,
    include_files: bool = False,
) -> dict[str, object]:
    """Load config/state and capture a snapshot for API callers."""
    workspace = load_workspace(config_path)
    state = load_state(state_path)
    plan = plan_workspace(workspace, state, False)
    return capture_workspace_snapshot(
        workspace,
        plan,
        state,
        config_path=config_path,
        state_path=state_path,
        name=name,
        include_files=include_files,
    )


def capture_workspace_files(
    root: Path,
    *,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> dict[str, object]:
    """Capture a bounded file-level image of the workspace root."""
    root = root.resolve(strict=False)
    entries: dict[str, object] = {}
    skipped: list[dict[str, object]] = []
    total_bytes = 0
    for path in _iter_snapshot_file_candidates(root):
        rel = path.relative_to(root).as_posix()
        try:
            if path.is_symlink():
                target = os.readlink(path)
                entries[rel] = {"kind": "symlink", "target": target}
                continue
            size = path.stat().st_size
            if size > max_file_bytes:
                skipped.append({"path": rel, "reason": "too_large", "size": size})
                continue
            if total_bytes + size > max_total_bytes:
                skipped.append({"path": rel, "reason": "total_limit", "size": size})
                continue
            content = path.read_bytes()
        except OSError as error:
            skipped.append({"path": rel, "reason": "read_error", "error": str(error)})
            continue
        total_bytes += len(content)
        entries[rel] = {
            "kind": "file",
            "encoding": "base64",
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "content": base64.b64encode(content).decode("ascii"),
        }
    return {
        "version": 1,
        "root": str(root),
        "entries": entries,
        "skipped": skipped,
        "limits": {
            "max_file_bytes": max_file_bytes,
            "max_total_bytes": max_total_bytes,
        },
        "summary": {
            "files": sum(1 for item in entries.values() if isinstance(item, dict) and item.get("kind") == "file"),
            "symlinks": sum(1 for item in entries.values() if isinstance(item, dict) and item.get("kind") == "symlink"),
            "bytes": total_bytes,
            "skipped": len(skipped),
        },
    }


def _iter_snapshot_file_candidates(root: Path) -> list[Path]:
    paths: list[Path] = []
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for dirname in sorted(dirnames):
            rel = (current_path / dirname).relative_to(root).as_posix()
            if _is_excluded_snapshot_path(rel):
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs
        for filename in sorted(filenames):
            path = current_path / filename
            rel = path.relative_to(root).as_posix()
            if _is_excluded_snapshot_path(rel):
                continue
            paths.append(path)
    return paths


def preview_workspace_files_restore(files_payload: dict[str, object]) -> dict[str, object]:
    root = Path(str(files_payload.get("root") or ""))
    if not root:
        raise ValueError("Snapshot file payload does not include a root")
    target = _snapshot_file_entries(files_payload)
    current_payload = capture_workspace_files(root, **_snapshot_limits(files_payload))
    current = _snapshot_file_entries(current_payload)
    return _state_section_diff(current, target)


def restore_workspace_files(files_payload: dict[str, object]) -> dict[str, object]:
    root = Path(str(files_payload.get("root") or ""))
    if not root:
        raise ValueError("Snapshot file payload does not include a root")
    root = root.resolve(strict=False)
    preview = preview_workspace_files_restore(files_payload)
    entries = _snapshot_file_entries(files_payload)
    for rel in cast(list[str], preview.get("removed") or []):
        target = _safe_snapshot_path(root, rel)
        if target.is_symlink() or target.is_file():
            target.unlink()
            _remove_empty_parents(target.parent, root)
    for rel, raw_entry in entries.items():
        entry = raw_entry if isinstance(raw_entry, dict) else {}
        target = _safe_snapshot_path(root, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            if target.is_dir() and not target.is_symlink():
                raise ValueError(f"Cannot restore file over directory: {rel}")
            target.unlink()
        kind = entry.get("kind")
        if kind == "symlink":
            os.symlink(str(entry.get("target") or ""), target)
        elif kind == "file":
            content = base64.b64decode(str(entry.get("content") or "").encode("ascii"))
            expected = str(entry.get("sha256") or "")
            actual = hashlib.sha256(content).hexdigest()
            if expected and expected != actual:
                raise ValueError(f"Snapshot content hash mismatch: {rel}")
            target.write_bytes(content)
        else:
            raise ValueError(f"Unknown snapshot file entry kind for {rel}: {kind}")
    return {
        "root": str(root),
        "changes": preview,
        "summary": _section_counts(preview),
    }


def _state_section_diff(current: dict[str, object], target: dict[str, object]) -> dict[str, object]:
    current_keys = set(current)
    target_keys = set(target)
    added = sorted(target_keys - current_keys)
    removed = sorted(current_keys - target_keys)
    changed = sorted(key for key in current_keys & target_keys if current.get(key) != target.get(key))
    unchanged = sorted(key for key in current_keys & target_keys if current.get(key) == target.get(key))
    details = {
        key: {
            "before": current.get(key),
            "after": target.get(key),
        }
        for key in changed
    }
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
        "details": details,
    }


def _section_counts(section: dict[str, object]) -> dict[str, int]:
    return {
        "added": len(cast(list[object], section.get("added") or [])),
        "removed": len(cast(list[object], section.get("removed") or [])),
        "changed": len(cast(list[object], section.get("changed") or [])),
        "unchanged": len(cast(list[object], section.get("unchanged") or [])),
    }


def _snapshot_file_entries(files_payload: dict[str, object]) -> dict[str, object]:
    entries = files_payload.get("entries")
    if not isinstance(entries, dict):
        raise ValueError("Snapshot file payload does not include entries")
    return {str(key): value for key, value in entries.items()}


def _snapshot_limits(files_payload: dict[str, object]) -> dict[str, int]:
    raw_limits = files_payload.get("limits")
    limits = raw_limits if isinstance(raw_limits, dict) else {}
    return {
        "max_file_bytes": int(limits.get("max_file_bytes") or DEFAULT_MAX_FILE_BYTES),
        "max_total_bytes": int(limits.get("max_total_bytes") or DEFAULT_MAX_TOTAL_BYTES),
    }


def _is_excluded_snapshot_path(rel: str) -> bool:
    parts = Path(rel).parts
    if not parts:
        return True
    joined_prefixes = ["/".join(parts[:idx]) for idx in range(1, len(parts) + 1)]
    return any(prefix in DEFAULT_EXCLUDED_FILE_DIRS for prefix in joined_prefixes)


def _safe_snapshot_path(root: Path, rel: str) -> Path:
    candidate = Path(rel)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Unsafe snapshot file path: {rel}")
    target = (root / candidate).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as error:
        raise ValueError(f"Unsafe snapshot file path: {rel}") from error
    return target


def _remove_empty_parents(path: Path, root: Path) -> None:
    current = path
    while current != root:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def probe_git(path: Path) -> dict[str, object]:
    """Return current git branch/worktree metadata for *path*."""
    repo_root = _git(path, "rev-parse", "--show-toplevel")
    if repo_root is None:
        return {"repo_root": None, "branch": None, "commit": None, "worktree": str(path), "dirty": False, "changed_files": 0}
    root = Path(repo_root)
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    commit = _git(root, "rev-parse", "--short", "HEAD")
    porcelain = _git(root, "status", "--porcelain") or ""
    changed = [line for line in porcelain.splitlines() if line.strip()]
    return {
        "repo_root": str(root),
        "branch": branch,
        "commit": commit,
        "worktree": str(path),
        "dirty": bool(changed),
        "changed_files": len(changed),
    }


def _git(path: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(path), *args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()
