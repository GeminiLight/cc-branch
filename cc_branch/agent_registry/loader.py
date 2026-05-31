"""Agent registry merge and normalization logic."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import load_yaml
from .models import AgentDefinition
from .paths import builtin_agents_path, user_override_path, workspace_override_path


def parse_agent_definitions(data: dict[str, Any]) -> dict[str, AgentDefinition]:
    """Parse raw registry data into normalized agent definitions."""
    raw = data.get("agents", {})
    if not isinstance(raw, dict):
        return {}

    result: dict[str, AgentDefinition] = {}
    for name, spec in raw.items():
        if not isinstance(spec, dict):
            continue
        result[name] = AgentDefinition(
            name=name,
            command=str(spec.get("command") or name),
            install_hint=str(spec.get("install_hint") or ""),
            resume_mode=str(spec.get("resume_mode") or "none"),
            resume_template=str(spec.get("resume_template") or ""),
            create_mode=str(spec.get("create_mode") or "none"),
            create_template=str(spec.get("create_template") or ""),
            label_template=str(spec.get("label_template") or ""),
            label_mode=str(spec.get("label_mode") or "metadata"),
            rename_template=str(spec.get("rename_template") or ""),
        )
    return result


def load_agent_registry(
    cwd: Path | None = None,
    extra_path: Path | None = None,
) -> dict[str, AgentDefinition]:
    """Load merged agent definitions from all registry layers."""
    merged: dict[str, Any] = {}

    for path in (
        builtin_agents_path(),
        user_override_path(),
        workspace_override_path(cwd),
        extra_path,
    ):
        if path is None:
            continue
        agents = load_yaml(path).get("agents")
        if not isinstance(agents, dict):
            continue
        for name, spec in agents.items():
            if not isinstance(spec, dict):
                continue
            base = merged.get(name)
            merged[name] = {
                **(base if isinstance(base, dict) else {}),
                **spec,
            }

    return parse_agent_definitions({"agents": merged})
