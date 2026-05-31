"""State persistence with atomic writes.

Public API operates on typed :class:`cc_branch.models.WorkspaceState`.
"""

from __future__ import annotations

from pathlib import Path

from .models import WorkspaceState
from .repository import StateRepository


def load_state(path: Path) -> WorkspaceState:
    """Load workspace state from *path*.

    Returns an empty state if the file does not exist.
    """
    repo = StateRepository(path)
    return repo.load()


def merge_state(state: WorkspaceState, plan_state_updates: dict[str, dict]) -> WorkspaceState:
    """Merge *plan_state_updates* into *state*.

    Existing window metadata is preserved unless overwritten.
    """
    from .models import WindowState

    merged = WorkspaceState(version=state.version)
    for key, window_entry in state.windows.items():
        merged.windows[key] = window_entry
    for key, slot_entry in state.slots.items():
        merged.slots[key] = slot_entry
    for key, update in plan_state_updates.items():
        existing = merged.windows.get(key)
        if existing:
            merged.windows[key] = WindowState(
                session_id=update.get("session_id", existing.session_id),
                label=update.get("label", existing.label),
                agent=update.get("agent", existing.agent),
                slot=update.get("slot", existing.slot),
                window=update.get("window", existing.window),
                launch_fingerprint=existing.launch_fingerprint,
                launch_spec_version=existing.launch_spec_version,
                applied_at=existing.applied_at,
                managed_runtime=existing.managed_runtime,
                tmux_session=existing.tmux_session,
                session_binding_status=existing.session_binding_status,
                session_binding_source=existing.session_binding_source,
                session_binding_updated_at=existing.session_binding_updated_at,
            )
        else:
            merged.windows[key] = WindowState(
                session_id=update.get("session_id"),
                label=update.get("label"),
                agent=update.get("agent"),
                slot=update.get("slot"),
                window=update.get("window"),
            )
    return merged


def save_state(path: Path, state: WorkspaceState) -> None:
    """Save *state* atomically.

    Uses a temporary file + rename strategy so the on-disk state is
    never half-written.
    """
    repo = StateRepository(path)
    repo.save(state)
