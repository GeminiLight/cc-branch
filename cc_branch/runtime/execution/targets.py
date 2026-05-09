"""Runtime target resolution."""

from __future__ import annotations

from ...exceptions import SlotNotFoundError, WindowNotFoundError
from ...models import SlotPlan, WindowPlan, WorkspacePlan
from ...targets import parse_target


def resolve_target(
    plan: WorkspacePlan, target: str | None
) -> tuple[SlotPlan | None, WindowPlan | None]:
    """Parse a target string like ``slot`` or ``slot:window``."""
    if not target:
        return None, None

    parsed = parse_target(target)
    slot = plan.get_slot(parsed.slot)
    if slot is None:
        raise SlotNotFoundError(f"unknown slot: {target}")

    if parsed.window is None:
        return slot, None

    window = get_window(slot, parsed.window)
    if window is None:
        raise WindowNotFoundError(f"unknown window: {target}")

    return slot, window


def get_window(slot: SlotPlan, window_name: str) -> WindowPlan | None:
    """Return a window by name from a slot plan."""
    for window in slot.windows:
        if window.name == window_name:
            return window
    return None
