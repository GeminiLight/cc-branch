"""Workspace snapshot capture and restore."""

from __future__ import annotations

import json
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
    return store.save(snapshot)


def restore_workspace_snapshot(
    snapshot_id: str,
    *,
    store: WorkspaceSnapshotStore | None = None,
    state_path: Path | None = None,
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
    save_state(target_state_path, WorkspaceState.from_dict(raw_state))
    return {
        "success": True,
        "snapshot_id": snapshot.get("id"),
        "name": snapshot.get("name"),
        "state_path": str(target_state_path),
        "config_path": snapshot.get("config_path"),
    }


def capture_snapshot_for_workspace(
    config_path: Path,
    state_path: Path,
    *,
    name: str | None = None,
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
    )


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
