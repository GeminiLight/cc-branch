"""User-level agent registry settings."""

from __future__ import annotations

from pathlib import Path

import yaml

from ..agent_registry.io import load_yaml
from ..agent_registry.loader import parse_agent_definitions
from ..agent_registry.paths import builtin_agents_path, user_override_path
from .config_workflows.options import agent_payload
from .config_workflows.versioning import (
    base_version_matches,
    content_hash,
    file_version_payload,
    write_text_atomic,
)
from .results import ActionResult

DEFAULT_GLOBAL_AGENTS = """# User-level agent overrides for cc-branch.
# Built-in agents load first; this file overrides them for all projects.
# A project can still override these values in .cc-branch/agents.yaml or config.yaml.
agents: {}
"""


def read_global_agents() -> ActionResult:
    """Return the editable user-level agents file."""
    path = user_override_path()
    exists = path.exists()
    content = path.read_text(encoding="utf-8") if exists else DEFAULT_GLOBAL_AGENTS
    return ActionResult(
        ok=True,
        code="global_agents_loaded",
        message="Global agents loaded",
        payload=_payload(path, content, exists=exists),
    )


def save_global_agents(
    content: str,
    *,
    base_mtime: object | None = None,
    base_content_hash: str | None = None,
) -> ActionResult:
    """Validate and save the user-level agents file."""
    path = user_override_path()
    current_content = path.read_text(encoding="utf-8") if path.exists() else DEFAULT_GLOBAL_AGENTS
    current_version: dict[str, object] = (
        file_version_payload(path, current_content)
        if path.exists()
        else {
            "mtime": None,
            "content_hash": content_hash(current_content),
        }
    )
    if not base_version_matches(
        current_version,
        base_mtime=base_mtime,
        base_content_hash=base_content_hash,
    ):
        return ActionResult(
            ok=False,
            code="global_agents_conflict",
            message="Global agents file changed on disk. Reload before saving.",
            payload={
                **_payload(path, current_content, exists=path.exists()),
                "current_content": current_content,
            },
        )

    issue = _validate_global_agents(content)
    if issue:
        return ActionResult(
            ok=False,
            code="invalid_global_agents",
            message=issue,
            payload={"issues": [{"message": issue}]},
        )

    write_text_atomic(path, _ensure_trailing_newline(content))
    saved_content = path.read_text(encoding="utf-8")
    return ActionResult(
        ok=True,
        code="global_agents_saved",
        message="Global agents saved",
        payload=_payload(path, saved_content, exists=True),
    )


def _payload(path: Path, content: str, *, exists: bool) -> dict:
    try:
        user_data = yaml.safe_load(content) or {}
    except yaml.YAMLError:
        user_data = {}
    user_data = user_data if isinstance(user_data, dict) else {}
    builtin_data = load_yaml(builtin_agents_path())
    effective_data = _effective_global_agent_data(user_data)
    definitions = parse_agent_definitions(effective_data)
    builtin_definitions = parse_agent_definitions(builtin_data if isinstance(builtin_data, dict) else {})
    user_definitions = parse_agent_definitions(user_data)
    version = file_version_payload(path, content) if path.exists() else {
        "mtime": None,
        "content_hash": content_hash(content),
    }
    return {
        "path": str(path),
        "exists": exists,
        "content": content,
        **version,
        "agents": _agent_list(definitions),
        "builtin_agents": _agent_list(builtin_definitions),
        "user_agents": _agent_list(user_definitions),
    }


def _effective_global_agent_data(user_data: dict) -> dict:
    merged: dict[str, object] = {}
    for source in (load_yaml(builtin_agents_path()), user_data):
        agents = source.get("agents")
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
    return {"agents": merged}


def _global_agent_payload(name: str, definition) -> dict:
    payload = agent_payload(name, definition.to_agent_spec())
    payload["install_hint"] = definition.install_hint
    return payload


def _agent_list(definitions: dict) -> list[dict]:
    return [
        _global_agent_payload(name, definition)
        for name, definition in sorted(definitions.items())
    ]


def _validate_global_agents(content: str) -> str | None:
    try:
        data = yaml.safe_load(content) or {}
    except yaml.YAMLError as error:
        return str(error)
    if not isinstance(data, dict):
        return "Global agents YAML must be a mapping."
    agents = data.get("agents", {})
    if agents is None:
        return None
    if not isinstance(agents, dict):
        return "Global agents YAML must contain an 'agents' mapping."
    for name, spec in agents.items():
        if not isinstance(name, str) or not name.strip():
            return "Agent names must be non-empty strings."
        if not isinstance(spec, dict):
            return f"Agent '{name}' must be a mapping."
    return None


def _ensure_trailing_newline(content: str) -> str:
    return content if content.endswith("\n") else f"{content}\n"
