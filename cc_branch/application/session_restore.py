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
from .agent_sessions import AgentSessionOption, agent_session_options_for_project
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
    target: str | None = None,
    agent: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    limit: int = 20,
) -> ActionResult:
    """Bind unbound agent panes to matching local transcript/session records."""
    project_dir = Path(workspace.root)
    normalized_target = _normalize_target(target)
    normalized_agent = (agent or "").strip() or None
    candidates_by_agent: dict[str, list[AgentSessionOption]] = {}
    matched_target = normalized_target is None
    for slot, window in plan.iter_windows():
        if not window.agent:
            continue
        if normalized_target is not None and _window_key(slot.name, window.name) != normalized_target:
            continue
        matched_target = True
        if normalized_agent is not None and window.agent != normalized_agent:
            continue
        if window.agent not in candidates_by_agent:
            candidates_by_agent[window.agent] = agent_session_options_for_project(
                project_dir,
                window.agent,
                home=home,
                limit=limit,
            )
    if normalized_target is not None and not matched_target:
        raise ValueError(f"Unknown session target: {target}")

    changed: list[str] = []
    bindings: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    candidate_payload: dict[str, list[dict[str, object]]] = {}
    used_session_ids: set[str] = {
        entry.session_id
        for entry in state.windows.values()
        if entry.session_id
    }
    timestamp = now()
    for slot, window in plan.iter_windows():
        target_name = f"{slot.name}:{window.name}"
        key = _window_key(slot.name, window.name)
        if normalized_target is not None and key != normalized_target:
            continue
        if not window.agent:
            skipped.append({"target": target_name, "reason": "no_agent"})
            continue
        if normalized_agent is not None and window.agent != normalized_agent:
            skipped.append({"target": target_name, "agent": window.agent, "reason": "agent_mismatch"})
            continue
        existing = state.windows.get(window.key)
        if existing and existing.session_id and not force:
            skipped.append({"target": target_name, "agent": window.agent, "reason": "already_bound", "session_id": existing.session_id})
            continue
        if existing and existing.session_id and force:
            used_session_ids.discard(existing.session_id)
        candidates = [
            candidate
            for candidate in candidates_by_agent.get(window.agent, [])
            if candidate.id not in used_session_ids
        ]
        candidate_payload[target_name] = [_candidate_payload(candidate) for candidate in candidates[:limit]]
        if not candidates:
            skipped.append({"target": target_name, "agent": window.agent, "reason": "no_candidates"})
            continue
        candidate = candidates[0]
        binding = {
            "target": target_name,
            "key": window.key,
            "agent": window.agent,
            "session_id": candidate.id,
            "label": candidate.label,
            "source": candidate.source,
        }
        bindings.append(binding)
        if dry_run:
            used_session_ids.add(candidate.id)
            changed.append(target_name)
            continue
        state.windows[window.key] = _bound_window_state(
            existing,
            candidate,
            agent=window.agent,
            slot=slot.name,
            window=window.name,
            timestamp=timestamp,
        )
        used_session_ids.add(candidate.id)
        changed.append(target_name)

    payload = {
        "bindings": bindings,
        "skipped": skipped,
        "candidates": candidate_payload,
        "dry_run": dry_run,
        "force": force,
    }
    if changed and dry_run:
        return ActionResult(
            ok=True,
            code="sessions_restore_preview",
            message=f"Would restore {len(changed)} session binding(s)",
            changed_targets=tuple(changed),
            payload=payload,
        )
    if changed:
        save_state(state_path, state)
        return ActionResult(
            ok=True,
            code="sessions_restored",
            message=f"Restored {len(changed)} session binding(s)",
            changed_targets=tuple(changed),
            payload=payload,
        )
    return ActionResult(
        ok=True,
        code="sessions_restore_noop",
        message="No local transcript sessions matched selected panes",
        payload=payload,
    )


def _bound_window_state(
    existing: WindowState | None,
    candidate: AgentSessionOption,
    *,
    agent: str,
    slot: str,
    window: str,
    timestamp: str,
) -> WindowState:
    return WindowState(
        session_id=candidate.id,
        label=candidate.label,
        agent=agent,
        slot=slot,
        window=window,
        launch_fingerprint=(existing.launch_fingerprint if existing else None),
        launch_spec_version=(existing.launch_spec_version if existing else None),
        applied_at=(existing.applied_at if existing else None),
        managed_runtime=(existing.managed_runtime if existing else None),
        tmux_session=(existing.tmux_session if existing else None),
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


def _candidate_payload(candidate: AgentSessionOption) -> dict[str, object]:
    return {
        "agent": candidate.agent,
        "id": candidate.id,
        "label": candidate.label,
        "updated_at": candidate.updated_at,
        "source": candidate.source,
        "project_path": str(candidate.project_path) if candidate.project_path else None,
    }


def _normalize_target(target: str | None) -> str | None:
    raw = (target or "").strip()
    if not raw:
        return None
    return raw.replace(":", ".")


def _window_key(slot: str, window: str) -> str:
    return f"{slot}.{window}"


def restore_sessions_for_workspace(
    config_path: Path,
    state_path: Path,
    *,
    home: Path | None = None,
    target: str | None = None,
    agent: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    limit: int = 20,
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
        target=target,
        agent=agent,
        dry_run=dry_run,
        force=force,
        limit=limit,
    )
