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

    slots, window = resolve_target_slots(plan, target)
    if not slots:
        return None, None
    return slots[0], window


def resolve_target_slots(
    plan: WorkspacePlan, target: str | None
) -> tuple[list[SlotPlan], WindowPlan | None]:
    """Resolve a target to one or more internal slots.

    Public ``tabs`` can expand into multiple runtime slots that share the same
    ``split_group``. Lifecycle operations use this helper so a target such as
    ``dev`` still addresses the full public tab after planning.
    """
    if not target:
        return [], None

    parsed = parse_target(target)
    slot = plan.get_slot(parsed.slot)
    if slot is None:
        grouped_slots = [candidate for candidate in plan.slots if candidate.split_group == parsed.slot]
        if not grouped_slots:
            raise SlotNotFoundError(f"unknown slot: {target}")
        if parsed.window is None:
            return grouped_slots, None
        for grouped_slot in grouped_slots:
            window = get_window(grouped_slot, parsed.window)
            if window is not None:
                return [grouped_slot], window
        raise WindowNotFoundError(f"unknown window: {target}")

    if parsed.window is None:
        grouped_slots = [candidate for candidate in plan.slots if candidate.split_group == parsed.slot]
        return (grouped_slots or [slot]), None

    window = get_window(slot, parsed.window)
    if window is None:
        raise WindowNotFoundError(f"unknown window: {target}")

    return [slot], window


def get_window(slot: SlotPlan, window_name: str) -> WindowPlan | None:
    """Return a window by name from a slot plan."""
    for window in slot.windows:
        if window.name == window_name:
            return window
    return None
