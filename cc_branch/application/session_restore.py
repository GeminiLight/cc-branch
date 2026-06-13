"""Session restore helpers that reconcile local agent transcripts with state."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..config import load_workspace
from ..models import WindowState, WorkspaceConfig, WorkspacePlan, WorkspaceState
from ..planner import plan_workspace
from ..state import load_state
from ..state import save_state
from .agent_sessions import agent_session_options_for_project
from .results import ActionResult

Clock = Callable[[], str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def restore_sessions_from_local_transcripts(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    state_path: Path,
    state: WorkspaceState,
    *,
    home: Path | None = None,
    now: Clock = _utc_now,
) -> ActionResult:
    """Bind unbound agent panes to matching local transcript/session records."""
    project_dir = Path(workspace.root)
    candidates_by_agent: dict[str, list] = {}
    for _slot, window in plan.iter_windows():
        if not window.agent:
            continue
        if window.agent not in candidates_by_agent:
            candidates_by_agent[window.agent] = agent_session_options_for_project(
                project_dir,
                window.agent,
                home=home,
                limit=20,
            )

    changed: list[str] = []
    used_session_ids: set[str] = {
        entry.session_id
        for entry in state.windows.values()
        if entry.session_id
    }
    timestamp = now()
    for slot, window in plan.iter_windows():
        if not window.agent:
            continue
        existing = state.windows.get(window.key)
        if existing and existing.session_id:
            continue
        candidates = [
            candidate
            for candidate in candidates_by_agent.get(window.agent, [])
            if candidate.id not in used_session_ids
        ]
        if not candidates:
            continue
        candidate = candidates[0]
        state.windows[window.key] = WindowState(
            session_id=candidate.id,
            label=candidate.label,
            agent=window.agent,
            slot=slot.name,
            window=window.name,
            session_binding_status="bound",
            session_binding_source=candidate.source,
            session_binding_updated_at=timestamp,
            session_runtime_status=(existing.session_runtime_status if existing else None),
            session_transcript_path=candidate.source,
            session_hook_event=(existing.session_hook_event if existing else None),
            session_hook_updated_at=(existing.session_hook_updated_at if existing else None),
            session_pid=(existing.session_pid if existing else None),
            session_exit_code=(existing.session_exit_code if existing else None),
        )
        used_session_ids.add(candidate.id)
        changed.append(f"{slot.name}:{window.name}")

    if changed:
        save_state(state_path, state)
        return ActionResult(
            ok=True,
            code="sessions_restored",
            message=f"Restored {len(changed)} session binding(s)",
            changed_targets=tuple(changed),
        )
    return ActionResult(
        ok=True,
        code="sessions_restore_noop",
        message="No local transcript sessions matched unbound panes",
    )


def restore_sessions_for_workspace(
    config_path: Path,
    state_path: Path,
    *,
    home: Path | None = None,
) -> ActionResult:
    """Load a workspace and restore matching local transcript sessions."""
    workspace = load_workspace(config_path)
    state = load_state(state_path)
    plan = plan_workspace(workspace, state, bootstrap_missing=False)
    return restore_sessions_from_local_transcripts(
        workspace,
        plan,
        state_path,
        state,
        home=home,
    )
