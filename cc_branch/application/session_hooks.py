"""Session lifecycle hook handling.

Agent hook scripts can call into this module after a CLI agent starts, updates
its transcript, or exits. The only durable side effect is updating
``.cc-branch/state.yaml`` so future launches can resume the same pane.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..models import WindowState, WorkspaceState
from ..runtime.sync.state import now_iso
from ..state import load_state, save_state

_EVENTS = {"started", "updated", "exited", "error"}


@dataclass(frozen=True)
class SessionHookEvent:
    """A lifecycle update emitted by an agent hook for one pane."""

    key: str
    event: str
    agent: str | None = None
    session_id: str | None = None
    transcript_path: str | None = None
    label: str | None = None
    pid: int | None = None
    exit_code: int | None = None
    timestamp: str | None = None


def apply_session_hook_event(state_path: Path, event: SessionHookEvent) -> WorkspaceState:
    """Apply one session hook event to ``state_path`` and return the saved state."""
    _validate_event(event)
    state = load_state(state_path)
    key = _normalize_key(event.key)
    existing = state.windows.get(key)
    slot, window = _split_key(key)
    updated_at = event.timestamp or now_iso()
    transcript_path = event.transcript_path or (existing.session_transcript_path if existing else None)
    session_id = event.session_id or (existing.session_id if existing else None)

    state.windows[key] = WindowState(
        session_id=session_id,
        label=event.label or (existing.label if existing else None),
        agent=event.agent or (existing.agent if existing else None),
        slot=(existing.slot if existing and existing.slot else slot),
        window=(existing.window if existing and existing.window else window),
        launch_fingerprint=existing.launch_fingerprint if existing else None,
        launch_spec_version=existing.launch_spec_version if existing else None,
        applied_at=existing.applied_at if existing else None,
        managed_runtime=existing.managed_runtime if existing else None,
        tmux_session=existing.tmux_session if existing else None,
        session_binding_status=_binding_status(event, existing, session_id),
        session_binding_source=transcript_path or (existing.session_binding_source if existing else None),
        session_binding_updated_at=updated_at,
        session_hook_event=event.event,
        session_hook_updated_at=updated_at,
        session_runtime_status=_runtime_status(event),
        session_transcript_path=transcript_path,
        session_pid=event.pid if event.pid is not None else (existing.session_pid if existing else None),
        session_exit_code=(
            event.exit_code
            if event.exit_code is not None
            else (existing.session_exit_code if existing else None)
        ),
    )
    save_state(state_path, state)
    return state


def normalize_session_hook_key(value: str) -> str:
    """Return the internal ``tab.pane`` key accepted by session hooks."""
    return _normalize_key(value)


def _validate_event(event: SessionHookEvent) -> None:
    if event.event not in _EVENTS:
        raise ValueError(f"unsupported session hook event: {event.event}")
    _normalize_key(event.key)


def _normalize_key(value: str) -> str:
    key = value.strip().replace(":", ".")
    if not key or key.count(".") != 1:
        raise ValueError("session hook target must be tab:pane")
    slot, window = _split_key(key)
    if not slot or not window:
        raise ValueError("session hook target must be tab:pane")
    return key


def _split_key(key: str) -> tuple[str, str]:
    slot, _, window = key.partition(".")
    return slot, window


def _binding_status(
    event: SessionHookEvent,
    existing: WindowState | None,
    session_id: str | None,
) -> str | None:
    if session_id:
        return "bound"
    if event.event == "error":
        return "capture_failed"
    return existing.session_binding_status if existing else "pending_capture"


def _runtime_status(event: SessionHookEvent) -> str:
    if event.event in {"started", "updated"}:
        return "running"
    if event.event == "error":
        return "failed"
    if event.exit_code not in (None, 0):
        return "failed"
    return "stopped"
