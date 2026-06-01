"""Built-in workspace profile templates."""

from __future__ import annotations

from typing import Any

PROFILES: dict[str, dict[str, Any]] = {
    "development": {
        "description": "Development workspace with one terminal tab for frontend, backend, algorithm, and docs panes",
        "tabs": [
            {
                "name": "development",
                "layoutBackend": "direct",
                "panes": [
                    {"name": "frontend", "preferred_agents": ["codex", "claude", "gemini"]},
                    {"name": "backend", "preferred_agents": ["codex", "claude", "gemini"]},
                    {"name": "algorithm", "preferred_agents": ["claude", "gemini", "codex"]},
                    {"name": "docs", "preferred_agents": ["claude", "gemini", "codex"]},
                ],
            },
        ],
    },
    "research": {
        "description": "Research workspace with idea, paper, code, and experiment panes",
        "tabs": [
            {
                "name": "idea",
                "layoutBackend": "direct",
                "panes": [
                    {"name": "idea", "preferred_agents": ["codex", "claude", "gemini"]},
                    {"name": "paper", "preferred_agents": ["codex", "claude", "gemini"]},
                ],
            },
            {
                "name": "code",
                "layoutBackend": "direct",
                "panes": [
                    {"name": "code", "preferred_agents": ["claude", "codex", "gemini"]},
                    {"name": "exp", "preferred_agents": ["claude", "codex", "gemini"]},
                ],
            },
        ],
    },
    "minimal": {
        "description": "Minimal workspace with one tab and one agent pane",
        "tabs": [
            {
                "name": "main",
                "panes": [
                    {"name": "agent", "preferred_agents": ["codex", "claude", "gemini"]},
                ],
            },
        ],
    },
}
