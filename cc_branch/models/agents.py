from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentSpec:
    """Reusable agent definition."""

    command: str = ""
    resume_mode: str = "none"
    resume_template: str = ""
    create_mode: str = "none"
    create_template: str = ""
    label_template: str = ""
    label_mode: str = "metadata"
    rename_template: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentSpec:
        return cls(
            command=data.get("command", ""),
            resume_mode=data.get("resume_mode", "none"),
            resume_template=data.get("resume_template", ""),
            create_mode=data.get("create_mode", "none"),
            create_template=data.get("create_template", ""),
            label_template=data.get("label_template", ""),
            label_mode=data.get("label_mode", "metadata"),
            rename_template=data.get("rename_template", ""),
        )

