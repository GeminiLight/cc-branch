"""Transport-independent application result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ActionResult:
    """Result returned by application workspace actions."""

    ok: bool
    code: str
    message: str
    exit_code: int = 0
    changed_targets: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
