"""Public target parsing for slot and window references."""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import ConfigError


@dataclass(frozen=True)
class Target:
    """A parsed public target.

    Public CLI syntax uses ``slot`` or ``slot:window``. The legacy
    ``slot.window`` form is accepted as compatibility input.
    """

    slot: str
    window: str | None = None

    @property
    def key(self) -> str:
        if self.window is None:
            return self.slot
        return f"{self.slot}.{self.window}"

    @property
    def public(self) -> str:
        if self.window is None:
            return self.slot
        return f"{self.slot}:{self.window}"


def parse_target(value: str) -> Target:
    """Parse ``slot``, ``slot:window``, or legacy ``slot.window``."""
    target = value.strip()
    if not target:
        raise ConfigError("target cannot be empty")

    has_colon = ":" in target
    has_dot = "." in target
    if has_colon and has_dot:
        raise ConfigError(
            f"invalid target '{value}': use slot or slot:window, not mixed separators"
        )

    separator = ":" if has_colon else "." if has_dot else None
    if separator is None:
        slot, window = target, None
    else:
        parts = target.split(separator)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ConfigError(
                f"invalid target '{value}': expected slot or slot:window"
            )
        slot, window = parts[0], parts[1]

    return Target(slot=slot, window=window)


def target_key(value: str) -> str:
    """Return the internal state key for a public target."""
    return parse_target(value).key
