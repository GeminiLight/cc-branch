"""Agent registry – loads agent definitions from YAML and supports user overrides.

Agent definitions live in three layers (later layers override earlier ones):

1.  Built-in ``cc_branch/agents.yaml`` (shipped with the package)
2.  User-level ``~/.cc-branch/agents.yaml`` (optional)
3.  Workspace-level ``.cc-branch.agents.yaml`` in cwd (optional)

This makes it possible to add new agents without touching the source code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


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
        """Render the agent definition as a YAML block for ``.cc-branch.yaml``."""
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


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _parse_agent_definitions(data: dict[str, Any]) -> dict[str, AgentDefinition]:
    raw = data.get("agents", {})
    if not isinstance(raw, dict):
        return {}
    result: dict[str, AgentDefinition] = {}
    for name, spec in raw.items():
        if not isinstance(spec, dict):
            continue
        result[name] = AgentDefinition(
            name=name,
            command=spec.get("command", name),
            install_hint=spec.get("install_hint", ""),
            resume_mode=spec.get("resume_mode", "none"),
            resume_template=spec.get("resume_template", ""),
            create_mode=spec.get("create_mode", "none"),
            create_template=spec.get("create_template", ""),
            label_template=spec.get("label_template", ""),
            label_mode=spec.get("label_mode", "metadata"),
            rename_template=spec.get("rename_template", ""),
        )
    return result


def _builtin_agents_path() -> Path:
    from importlib.resources import files

    return files("cc_branch") / "agents.yaml"


def _user_override_path() -> Path:
    return Path.home() / ".cc-branch" / "agents.yaml"


def _workspace_override_path(cwd: Path | None = None) -> Path:
    return (cwd or Path.cwd()) / ".cc-branch.agents.yaml"


def load_agent_registry(
    cwd: Path | None = None,
    extra_path: Path | None = None,
) -> dict[str, AgentDefinition]:
    """Load merged agent definitions from all layers.

    Layers (later override earlier):
        1. Built-in ``cc_branch/agents.yaml``
        2. ``~/.cc-branch/agents.yaml``
        3. ``.cc-branch.agents.yaml`` in *cwd*
        4. *extra_path* if provided
    """
    merged: dict[str, Any] = {}

    for path in (
        _builtin_agents_path(),
        _user_override_path(),
        _workspace_override_path(cwd),
        extra_path,
    ):
        if path is None:
            continue
        data = _load_yaml(path)
        agents = data.get("agents")
        if isinstance(agents, dict):
            merged.update(agents)

    return _parse_agent_definitions({"agents": merged})


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

_BUILTIN_REGISTRY: dict[str, AgentDefinition] | None = None


def _builtin_registry() -> dict[str, AgentDefinition]:
    global _BUILTIN_REGISTRY
    if _BUILTIN_REGISTRY is None:
        _BUILTIN_REGISTRY = _parse_agent_definitions(
            _load_yaml(_builtin_agents_path())
        )
    return _BUILTIN_REGISTRY


def get_builtin_agent_names() -> list[str]:
    """Return names of agents shipped with the package."""
    return list(_builtin_registry().keys())


def get_builtin_agent(name: str) -> AgentDefinition | None:
    """Return a single built-in agent definition or None."""
    return _builtin_registry().get(name)


def list_builtin_agents() -> list[AgentDefinition]:
    """Return all built-in agent definitions."""
    return list(_builtin_registry().values())
