from __future__ import annotations

from ..models import SlotConfig, WindowConfig
from ..runtime.capabilities import is_external_process_runtime


def _slot_windows(slot: SlotConfig) -> list[WindowConfig]:
    """Normalise a slot's windows.

    Terminal runtime slots launch one visible process. If a config still has
    window entries from a previous tmux setup, use the first one only as a
    fallback source instead of opening N terminals.
    """
    if is_external_process_runtime(slot.runtime):
        fallback = slot.windows[0] if slot.windows else WindowConfig()
        uses_fallback = slot.command is None and slot.agent is None and bool(slot.windows)
        return [
            WindowConfig(
                name=slot.title or fallback.name or "main",
                command=slot.command if slot.command is not None else fallback.command,
                agent=slot.agent if slot.agent is not None else fallback.agent,
                cwd=fallback.cwd if uses_fallback else None,
                env=fallback.env if uses_fallback else {},
                session_id=slot.session_id or fallback.session_id,
                label=slot.label or fallback.label,
                label_template=fallback.label_template if uses_fallback else None,
                resume_mode=fallback.resume_mode if uses_fallback else None,
                resume_template=fallback.resume_template if uses_fallback else None,
                create_mode=fallback.create_mode if uses_fallback else None,
                create_template=fallback.create_template if uses_fallback else None,
                label_mode=fallback.label_mode if uses_fallback else None,
                rename_template=fallback.rename_template if uses_fallback else None,
            )
        ]

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
