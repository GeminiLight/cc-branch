"""Small text-formatting helpers for user-facing messages."""

from __future__ import annotations


def count_label(count: int, singular: str, plural: str | None = None) -> str:
    """Return a compact English count label, such as ``1 target`` or ``2 targets``."""

    noun = singular if count == 1 else plural or f"{singular}s"
    return f"{count} {noun}"
