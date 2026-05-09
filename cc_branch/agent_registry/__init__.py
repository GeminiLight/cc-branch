"""Agent registry facade.

Agent definitions are loaded from built-in, user-level, and workspace-level
YAML layers. This package keeps source discovery, YAML IO, merge behavior, and
cached built-in helpers separate while preserving the historical
``cc_branch.agent_registry`` imports.
"""

from __future__ import annotations

from .builtins import get_builtin_agent, get_builtin_agent_names, list_builtin_agents
from .loader import load_agent_registry, parse_agent_definitions
from .models import AgentDefinition
from .paths import builtin_agents_path, user_override_path, workspace_override_path

_builtin_agents_path = builtin_agents_path
_parse_agent_definitions = parse_agent_definitions
_user_override_path = user_override_path
_workspace_override_path = workspace_override_path

__all__ = [
    "AgentDefinition",
    "builtin_agents_path",
    "get_builtin_agent",
    "get_builtin_agent_names",
    "list_builtin_agents",
    "load_agent_registry",
    "parse_agent_definitions",
    "user_override_path",
    "workspace_override_path",
]
