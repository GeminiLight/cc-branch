"""Optional git worktree lifecycle for agent panes."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from ..app_state.paths import app_data_dir
from ..config import load_workspace
from ..models import WorkspaceConfig, WorkspacePlan
from ..planner import plan_workspace
from ..state import load_state

CommandRunner = Callable[[list[str]], dict[str, object]]
Clock = Callable[[], str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class AgentWorktreeStore:
    """JSON-backed registry for agent-owned worktrees."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_data_dir() / "agent-worktrees.json"

    def records(self) -> list[dict[str, object]]:
        return list(self._data().get("worktrees", []))

    def find(self, target: str) -> dict[str, object] | None:
        for record in self.records():
            if record.get("target") == target:
                return record
        return None

    def upsert(self, record: dict[str, object]) -> dict[str, object]:
        records = [item for item in self.records() if item.get("target") != record.get("target")]
        records.append(record)
        records.sort(key=lambda item: str(item.get("target") or ""))
        self._write({"version": 1, "worktrees": records})
        return record

    def remove(self, target: str) -> dict[str, object]:
        records = self.records()
        removed = next((item for item in records if item.get("target") == target), None)
        if removed is None:
            raise ValueError(f"No worktree record for target: {target}")
        self._write({"version": 1, "worktrees": [item for item in records if item.get("target") != target]})
        return removed

    def _data(self) -> dict[str, object]:
        if not self.path.exists():
            return {"version": 1, "worktrees": []}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"version": 1, "worktrees": []}
        if not isinstance(raw, dict):
            return {"version": 1, "worktrees": []}
        records = raw.get("worktrees")
        if not isinstance(records, list):
            records = []
        return {"version": int(raw.get("version") or 1), "worktrees": [item for item in records if isinstance(item, dict)]}

    def _write(self, data: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp_path.replace(self.path)


def setup_agent_worktree(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    target: str,
    *,
    store: AgentWorktreeStore | None = None,
    repo_root: Path | None = None,
    path: Path | None = None,
    branch: str | None = None,
    base_ref: str = "HEAD",
    copy_ignored: Iterable[str] | None = None,
    symlink_ignored: Iterable[str] | None = None,
    setup_hook: str | None = None,
    runner: CommandRunner | None = None,
    now: Clock = _utc_now,
    lock_path: Path | None = None,
) -> dict[str, object]:
    """Create or update the git worktree assigned to an agent target."""
    slot, window = _resolve_agent_target(plan, target)
    if window.remote is not None:
        raise ValueError("Agent worktrees are local-only; remote panes should use the remote repo directly")
    store = store or AgentWorktreeStore()
    runner = runner or _run
    repo = (repo_root or Path(str(workspace.root))).resolve()
    target_slug = _target_slug(target)
    branch_name = branch or f"cc-branch/{target_slug}"
    worktree_path = (path or (app_data_dir() / "worktrees" / _target_slug(workspace.project or repo.name) / target_slug)).resolve()

    with _repo_operation_lock(store, lock_path):
        _ensure_success(runner(["git", "-C", str(repo), "worktree", "add", "-B", branch_name, str(worktree_path), base_ref]))
        worktree_path.mkdir(parents=True, exist_ok=True)
        copied = _copy_or_link(repo, worktree_path, copy_ignored or [], symlink=False)
        linked = _copy_or_link(repo, worktree_path, symlink_ignored or [], symlink=True)
        hook_result = None
        if setup_hook:
            hook_result = runner(["/bin/sh", "-lc", setup_hook])
            _ensure_success(hook_result)

        record = {
            "id": uuid.uuid4().hex,
            "target": target,
            "agent": window.agent,
            "slot": slot.name,
            "window": window.name,
            "repo_root": str(repo),
            "path": str(worktree_path),
            "branch": branch_name,
            "base_ref": base_ref,
            "status": "active",
            "created_at": now(),
            "copied": copied,
            "symlinked": linked,
            "setup_hook": setup_hook,
            "setup_hook_status": hook_result.get("returncode") if isinstance(hook_result, dict) else None,
        }
        return store.upsert(record)


def setup_agent_worktree_for_workspace(
    config_path: Path,
    state_path: Path,
    target: str,
    *,
    path: Path | None = None,
    branch: str | None = None,
    base_ref: str = "HEAD",
    copy_ignored: Iterable[str] | None = None,
    symlink_ignored: Iterable[str] | None = None,
    setup_hook: str | None = None,
    runner: CommandRunner | None = None,
    lock_path: Path | None = None,
) -> dict[str, object]:
    """Load config/state and create a worktree for API callers."""
    workspace = load_workspace(config_path)
    state = load_state(state_path)
    plan = plan_workspace(workspace, state, False)
    return setup_agent_worktree(
        workspace,
        plan,
        target,
        path=path,
        branch=branch,
        base_ref=base_ref,
        copy_ignored=copy_ignored,
        symlink_ignored=symlink_ignored,
        setup_hook=setup_hook,
        runner=runner,
        lock_path=lock_path,
    )


def import_agent_worktree(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    target: str,
    *,
    path: Path,
    branch: str | None = None,
    store: AgentWorktreeStore | None = None,
    repo_root: Path | None = None,
    now: Clock = _utc_now,
) -> dict[str, object]:
    """Record an existing git worktree for an agent target."""
    slot, window = _resolve_agent_target(plan, target)
    store = store or AgentWorktreeStore()
    record = {
        "id": uuid.uuid4().hex,
        "target": target,
        "agent": window.agent,
        "slot": slot.name,
        "window": window.name,
        "repo_root": str((repo_root or Path(str(workspace.root))).resolve()),
        "path": str(path.resolve()),
        "branch": branch,
        "status": "active",
        "created_at": now(),
        "imported": True,
    }
    return store.upsert(record)


def worktree_status_for_agents(
    *,
    store: AgentWorktreeStore | None = None,
    runner: CommandRunner | None = None,
) -> list[dict[str, object]]:
    """Return registered worktrees enriched with current branch and diff counts."""
    store = store or AgentWorktreeStore()
    runner = runner or _run
    statuses: list[dict[str, object]] = []
    for record in store.records():
        path = Path(str(record.get("path") or ""))
        branch_result = runner(["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"])
        status_result = runner(["git", "-C", str(path), "status", "--porcelain"])
        porcelain = str(status_result.get("stdout") or "") if status_result.get("returncode") == 0 else ""
        changed = [line for line in porcelain.splitlines() if line.strip()]
        enriched = dict(record)
        if branch_result.get("returncode") == 0:
            enriched["branch"] = str(branch_result.get("stdout") or "").strip()
        enriched["dirty"] = bool(changed)
        enriched["changed_files"] = len(changed)
        statuses.append(enriched)
    return statuses


def cleanup_agent_worktree(
    target: str,
    *,
    store: AgentWorktreeStore | None = None,
    runner: CommandRunner | None = None,
    force: bool = False,
    lock_path: Path | None = None,
) -> dict[str, object]:
    """Remove an agent worktree and delete its registry entry."""
    store = store or AgentWorktreeStore()
    runner = runner or _run
    record = store.find(target)
    if record is None:
        raise ValueError(f"No worktree record for target: {target}")
    command = ["git", "-C", str(record.get("repo_root")), "worktree", "remove", str(record.get("path"))]
    if force:
        command.append("--force")
    with _repo_operation_lock(store, lock_path):
        _ensure_success(runner(command))
        return store.remove(target)


def finish_agent_worktree(
    target: str,
    *,
    store: AgentWorktreeStore | None = None,
    runner: CommandRunner | None = None,
    now: Clock = _utc_now,
) -> dict[str, object]:
    """Mark an agent worktree as finished while preserving it for review/merge."""
    store = store or AgentWorktreeStore()
    runner = runner or _run
    record = store.find(target)
    if record is None:
        raise ValueError(f"No worktree record for target: {target}")
    current = next((item for item in worktree_status_for_agents(store=store, runner=runner) if item.get("target") == target), dict(record))
    current["status"] = "finished"
    current["finished_at"] = now()
    return store.upsert(current)


def _resolve_agent_target(plan: WorkspacePlan, target: str):
    normalized = target.replace(".", ":", 1)
    for slot in plan.slots:
        for window in slot.windows:
            if f"{slot.name}:{window.name}" == normalized:
                if not window.agent:
                    raise ValueError(f"Target is not an agent pane: {target}")
                return slot, window
    raise ValueError(f"Unknown agent target: {target}")


def _target_slug(value: str) -> str:
    slug = "".join(ch if ch.isalnum() else "-" for ch in value.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "agent"


def _copy_or_link(repo: Path, worktree: Path, paths: Iterable[str], *, symlink: bool) -> list[str]:
    processed: list[str] = []
    for relative in paths:
        rel_path = Path(relative)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise ValueError(f"Ignored file path must stay inside the repo: {relative}")
        source = repo / rel_path
        destination = worktree / rel_path
        if not source.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        if symlink:
            os.symlink(source, destination)
        elif source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        processed.append(str(rel_path))
    return processed


def _run(command: list[str]) -> dict[str, object]:
    try:
        completed = subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as error:
        return {"returncode": 127, "stdout": "", "stderr": str(error)}
    return {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def _ensure_success(result: dict[str, object]) -> None:
    if int(result.get("returncode") or 0) != 0:
        stderr = str(result.get("stderr") or "").strip()
        raise ValueError(stderr or "Command failed")


@contextmanager
def _repo_operation_lock(store: AgentWorktreeStore, lock_path: Path | None = None):
    path = lock_path or (store.path.parent / "locks" / "repo-operations.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise ValueError("Another worktree operation is already running for this repo") from error
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(str(os.getpid()))
        yield
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
