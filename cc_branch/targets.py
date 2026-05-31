"""Public target parsing for tab and pane references."""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import ConfigError

TARGET_SEPARATOR = ":"
RESERVED_NAME_SEPARATORS = (":", ".")


@dataclass(frozen=True)
class Target:
    """A parsed public target.

    Public CLI syntax uses ``tab`` or ``tab:pane``.
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
    """Parse ``tab`` or ``tab:pane``."""
    target = value.strip()
    if not target:
        raise ConfigError("target cannot be empty")

    if "." in target:
        raise ConfigError(
            f"invalid target '{value}': use tab or tab:pane"
        )

    if TARGET_SEPARATOR not in target:
        slot, window = target, None
    else:
        parts = target.split(TARGET_SEPARATOR)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ConfigError(
                f"invalid target '{value}': expected tab or tab:pane"
            )
        slot, window = parts[0], parts[1]

    return Target(slot=slot, window=window)


def target_key(value: str) -> str:
    """Return the internal state key for a public target."""
    return parse_target(value).key


def reserved_target_separators(value: str) -> list[str]:
    """Return target separators that make a config name ambiguous."""
    return [separator for separator in RESERVED_NAME_SEPARATORS if separator in value]
