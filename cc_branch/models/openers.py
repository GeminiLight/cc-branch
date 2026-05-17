from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OpenerSpec:
    """User-defined local application opener."""

    label: str = ""
    kind: str = "terminal"
    command: str = ""
    args: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpenerSpec:
        raw_args = data.get("args", [])
        if isinstance(raw_args, str):
            raw_args = [raw_args]
        raw_capabilities = data.get("capabilities", [])
        if isinstance(raw_capabilities, str):
            raw_capabilities = [raw_capabilities]
        return cls(
            label=data.get("label", ""),
            kind=data.get("kind", "terminal"),
            command=data.get("command", ""),
            args=[str(arg) for arg in raw_args],
            capabilities=[str(capability) for capability in raw_capabilities],
        )

