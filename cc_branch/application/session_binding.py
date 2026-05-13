"""Best-effort binding of newly created agent sessions."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..models import (
    AppliedWindowResult,
    SlotPlan,
    WindowPlan,
    WindowState,
    WorkspaceConfig,
    WorkspacePlan,
    WorkspaceState,
)
from ..runtime.sync import desired_fingerprint
from ..runtime.sync.models import LAUNCH_SPEC_VERSION
from ..runtime.sync.state import now_iso
from .agent_sessions import AgentSessionOption, agent_session_options_for_project

_LAUNCH_ACTIONS = {"created", "recreated", "opened_external"}


@dataclass(frozen=True)
class SessionBindingResult:
    """Outcome of attempting to bind a concrete agent session to a planned window."""

    key: str
    agent: str
    status: str
    session_id: str | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "key": self.key,
            "agent": self.agent,
            "status": self.status,
            "session_id": self.session_id,
            "source": self.source,
        }


def bind_discovered_agent_sessions(
    state: WorkspaceState,
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    results: list[AppliedWindowResult],
    *,
    project_dir: Path,
    home: Path | None = None,
    poll_timeout: float = 2.0,
    poll_interval: float = 0.4,
) -> tuple[WorkspaceState, list[SessionBindingResult]]:
    """Attach newly discoverable agent session IDs to ``session: auto`` windows.

    The binding is intentionally conservative. We only bind windows that launched without
    a resolved session id, only for agents whose stores we can scan, and only to sessions
    updated after the launch window. Ambiguous launches remain in ``pending_capture``.
    """
    eligible = _eligible_windows(plan, state, results)
    if not eligible:
        return state, []

    next_state = _clone_state(state)
    started_at = datetime.now(timezone.utc)
    cutoff = started_at - timedelta(seconds=90)
    deadline = time.monotonic() + max(0.0, poll_timeout)
    outcomes: dict[str, SessionBindingResult] = {}

    while True:
        discovered = _discover_recent_sessions(
            project_dir,
            sorted({window.agent for _, window in eligible if window.agent}),
            cutoff,
            home=home,
        )
        outcomes = _apply_bindings(next_state, workspace, eligible, discovered)
        if all(result.status == "bound" for result in outcomes.values()) or time.monotonic() >= deadline:
            break
        time.sleep(max(0.05, poll_interval))

    timestamp = now_iso()
    for slot, window in eligible:
        if window.key in outcomes:
            continue
        _upsert_binding_state(next_state, workspace, slot, window, status="pending_capture", updated_at=timestamp)
        outcomes[window.key] = SessionBindingResult(
            key=window.key,
            agent=window.agent or "",
            status="pending_capture",
        )

    return next_state, [outcomes[key] for key in sorted(outcomes)]


def _eligible_windows(
    plan: WorkspacePlan,
    state: WorkspaceState,
    results: list[AppliedWindowResult],
) -> list[tuple[SlotPlan, WindowPlan]]:
    launched_keys = {result.key for result in results if result.action in _LAUNCH_ACTIONS}
    eligible: list[tuple[SlotPlan, WindowPlan]] = []
    for slot, window in plan.iter_windows():
        if window.key not in launched_keys:
            continue
        existing = state.get_window(window.key)
        if existing and existing.session_id:
            continue
        if not window.agent or window.session_mode != "auto":
            continue
        if window.resolved_session_id or window.resume_mode == "none":
            continue
        eligible.append((slot, window))
    return eligible


def _discover_recent_sessions(
    project_dir: Path,
    agents: list[str],
    cutoff: datetime,
    *,
    home: Path | None,
) -> dict[str, list[AgentSessionOption]]:
    by_agent: dict[str, list[AgentSessionOption]] = {}
    for agent in agents:
        sessions = agent_session_options_for_project(project_dir, agent, home=home, limit=20)
        recent = [session for session in sessions if _is_recent(session.updated_at, cutoff)]
        by_agent[agent] = sorted(recent, key=lambda item: item.updated_at or "", reverse=True)
    return by_agent


def _apply_bindings(
    state: WorkspaceState,
    workspace: WorkspaceConfig,
    eligible: list[tuple[SlotPlan, WindowPlan]],
    discovered: dict[str, list[AgentSessionOption]],
) -> dict[str, SessionBindingResult]:
    outcomes: dict[str, SessionBindingResult] = {}
    used_ids = {entry.session_id for entry in state.windows.values() if entry.session_id}
    timestamp = now_iso()

    by_agent: dict[str, list[tuple[SlotPlan, WindowPlan]]] = {}
    for slot, window in eligible:
        by_agent.setdefault(window.agent or "", []).append((slot, window))

    for agent, windows in by_agent.items():
        candidates = [session for session in discovered.get(agent, []) if session.id not in used_ids]
        if len(candidates) >= len(windows):
            for slot, window in windows:
                candidate = candidates.pop(0)
                used_ids.add(candidate.id)
                _upsert_binding_state(
                    state,
                    workspace,
                    slot,
                    window,
                    session_id=candidate.id,
                    label=candidate.label,
                    status="bound",
                    source=candidate.source,
                    updated_at=timestamp,
                )
                outcomes[window.key] = SessionBindingResult(
                    key=window.key,
                    agent=agent,
                    status="bound",
                    session_id=candidate.id,
                    source=candidate.source,
                )
        elif candidates:
            for slot, window in windows:
                _upsert_binding_state(state, workspace, slot, window, status="ambiguous", updated_at=timestamp)
                outcomes[window.key] = SessionBindingResult(key=window.key, agent=agent, status="ambiguous")
    return outcomes


def _upsert_binding_state(
    state: WorkspaceState,
    workspace: WorkspaceConfig,
    slot: SlotPlan,
    window: WindowPlan,
    *,
    session_id: str | None = None,
    label: str | None = None,
    status: str,
    source: str | None = None,
    updated_at: str,
) -> None:
    existing = state.windows.get(window.key)
    state.windows[window.key] = WindowState(
        session_id=session_id or (existing.session_id if existing else None),
        label=label or window.resolved_label or (existing.label if existing else None),
        agent=window.agent or (existing.agent if existing else None),
        slot=slot.name,
        window=window.name,
        launch_fingerprint=desired_fingerprint(workspace, slot, window),
        launch_spec_version=LAUNCH_SPEC_VERSION,
        applied_at=existing.applied_at if existing else None,
        managed_runtime=slot.runtime,
        tmux_session=slot.tmux_session,
        session_binding_status=status,
        session_binding_source=source or (existing.session_binding_source if existing else None),
        session_binding_updated_at=updated_at,
    )


def _clone_state(state: WorkspaceState) -> WorkspaceState:
    next_state = WorkspaceState(version=state.version)
    next_state.windows.update(state.windows)
    next_state.slots.update(state.slots)
    return next_state


def _is_recent(value: str | None, cutoff: datetime) -> bool:
    parsed = _parse_datetime(value)
    return parsed is not None and parsed >= cutoff


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
