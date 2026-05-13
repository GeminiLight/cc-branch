"""Built-in workspace profile templates."""

from __future__ import annotations

PROFILES = {
    "development": {
        "description": "Development workspace with one tab for frontend, backend, algorithm, and docs panes",
        "tabs": [
            {
                "name": "development",
                "panes": [
                    {"name": "frontend", "preferred_agents": ["codex", "claude", "gemini"]},
                    {"name": "backend", "preferred_agents": ["codex", "gemini", "claude"]},
                    {"name": "algorithm", "preferred_agents": ["gemini", "codex", "claude"]},
                    {"name": "docs", "preferred_agents": ["claude", "gemini", "codex"]},
                ],
            },
        ],
    },
    "design": {
        "description": "Design workspace with product discussion, product implementation, and design direction tabs",
        "tabs": [
            {
                "name": "product",
                "panes": [
                    {"name": "discussion", "preferred_agents": ["claude", "gemini", "codex"]},
                    {"name": "implementation", "preferred_agents": ["codex", "claude", "gemini"]},
                ],
            },
            {
                "name": "design",
                "panes": [
                    {"name": "directions", "preferred_agents": ["claude", "gemini", "codex"]},
                    {"name": "review", "preferred_agents": ["claude", "codex", "gemini"]},
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
