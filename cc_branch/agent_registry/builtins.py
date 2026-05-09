"""Cached access to built-in agent definitions."""

from __future__ import annotations

from .io import load_yaml
from .loader import parse_agent_definitions
from .models import AgentDefinition
from .paths import builtin_agents_path

_BUILTIN_REGISTRY: dict[str, AgentDefinition] | None = None


def builtin_registry() -> dict[str, AgentDefinition]:
    """Return the cached built-in registry."""
    global _BUILTIN_REGISTRY
    if _BUILTIN_REGISTRY is None:
        _BUILTIN_REGISTRY = parse_agent_definitions(load_yaml(builtin_agents_path()))
    return _BUILTIN_REGISTRY


def get_builtin_agent_names() -> list[str]:
    """Return names of agents shipped with the package."""
    return list(builtin_registry().keys())


def get_builtin_agent(name: str) -> AgentDefinition | None:
    """Return a single built-in agent definition, if present."""
    return builtin_registry().get(name)


def list_builtin_agents() -> list[AgentDefinition]:
    """Return all built-in agent definitions."""
    return list(builtin_registry().values())
