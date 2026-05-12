from __future__ import annotations

from ..models import SlotConfig, WindowConfig
from ..runtime.capabilities import is_external_process_runtime


def _slot_windows(slot: SlotConfig) -> list[WindowConfig]:
    """Normalise a slot's windows.

    A public v2 tab can contain multiple terminal panes. Each pane should become
    one visible external terminal command.
    """
    if is_external_process_runtime(slot.runtime):
        if slot.windows:
            return list(slot.windows)
        return [WindowConfig(name=slot.title or "main", command=slot.command, agent=slot.agent)]

    if not slot.windows:
        return [
            WindowConfig(
                name=slot.title or "main",
                command=slot.command,
                agent=slot.agent,
                cwd=None,
                env={},
                session_id=slot.session_id,
                label=slot.label,
            )
        ]
    return list(slot.windows)
