"""Selecting runtime sync report targets."""

from __future__ import annotations

from .models import RuntimeSyncReport, SlotSyncStatus, WindowSyncStatus


def sync_report_for_target(report: RuntimeSyncReport, target: str | None) -> list[tuple[SlotSyncStatus, WindowSyncStatus | None]]:
    """Return report entries selected by a public target string."""
    if not target:
        return [(slot, window) for slot in report.slots for window in slot.windows]
    if ":" in target:
        slot_name, window_name = target.split(":", 1)
        return [
            (slot, window)
            for slot in report.slots
            if slot.name == slot_name
            for window in slot.windows
            if window.name == window_name
        ]
    return [
        (slot, window)
        for slot in report.slots
        if slot.name == target
        for window in slot.windows
    ]


def reconcilable_targets(report: RuntimeSyncReport, target: str | None) -> list[str]:
    """Return public targets that explicit apply can reconcile."""
    return sorted(
        {
            f"{slot.name}:{window.name}"
            for slot, window in sync_report_for_target(report, target)
            if window is not None and window.sync_status in {"changed", "missing", "untracked"}
        }
    )


def changed_or_missing_targets(report: RuntimeSyncReport, target: str | None) -> list[str]:
    """Compatibility alias for callers using the original helper name."""
    return reconcilable_targets(report, target)


def extra_window_targets(report: RuntimeSyncReport, target: str | None) -> list[str]:
    """Return tmux targets for extra windows selected by a public target."""
    selected: list[str] = []
    if target and ":" in target:
        slot_name, window_name = target.split(":", 1)
        for slot in report.slots:
            if slot.name != slot_name:
                continue
            selected.extend(
                f"{slot.tmux_session}:{window.name}"
                for window in slot.extra_windows
                if window.name == window_name
            )
        return sorted(set(selected))

    for slot in report.slots:
        if target and slot.name != target:
            continue
        selected.extend(f"{slot.tmux_session}:{window.name}" for window in slot.extra_windows)
    return sorted(set(selected))
