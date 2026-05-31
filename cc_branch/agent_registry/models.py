"""Agent registry data contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentDefinition:
    """Normalized agent metadata used by the planner and doctor."""

    name: str
    command: str
    install_hint: str = ""
    resume_mode: str = "none"
    resume_template: str = ""
    create_mode: str = "none"
    create_template: str = ""
    label_template: str = ""
    label_mode: str = "metadata"
    rename_template: str = ""

    def to_agent_spec(self) -> dict[str, Any]:
        """Return a dict compatible with ``AgentSpec.from_dict``."""
        return {
            "command": self.command,
            "resume_mode": self.resume_mode,
            "resume_template": self.resume_template,
            "create_mode": self.create_mode,
            "create_template": self.create_template,
            "label_template": self.label_template,
            "label_mode": self.label_mode,
            "rename_template": self.rename_template,
        }

    def to_yaml_block(self) -> str:
        """Render the agent definition as a YAML block for ``.cc-branch/config.yaml``."""
        lines = [f'  {self.name}:']
        lines.append(f'    command: "{self.command}"')
        if self.resume_mode and self.resume_mode != "none":
            lines.append(f'    resume_mode: "{self.resume_mode}"')
        if self.create_mode and self.create_mode != "none":
            lines.append(f'    create_mode: "{self.create_mode}"')
        if self.create_template:
            lines.append(f'    create_template: "{self.create_template}"')
        if self.resume_template:
            lines.append(f'    resume_template: "{self.resume_template}"')
        if self.label_template:
            lines.append(f'    label_template: "{self.label_template}"')
        if self.label_mode and self.label_mode != "metadata":
            lines.append(f'    label_mode: "{self.label_mode}"')
        if self.rename_template:
            lines.append(f'    rename_template: "{self.rename_template}"')
        return "\n".join(lines)
