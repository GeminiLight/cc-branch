"""Built-in workspace profile templates."""

from __future__ import annotations

PROFILES = {
    "solo-dev": {
        "description": "Single developer workspace with planner, builder, review, and scratch",
        "slots": [
            {
                "name": "dev",
                "windows": [
                    {"name": "planner", "preferred_agents": ["codex", "claude", "gemini"]},
                    {"name": "builder", "preferred_agents": ["codex", "claude", "gemini"]},
                    {"name": "review", "preferred_agents": ["claude", "codex", "gemini"]},
                ],
            },
            {"name": "scratch", "runtime": "terminal"},
        ],
    },
    "ai-pair": {
        "description": "AI coding pair workflow with separate coder and reviewer",
        "slots": [
            {
                "name": "coder",
                "windows": [
                    {"name": "implement", "preferred_agents": ["codex", "claude", "gemini"]},
                ],
            },
            {
                "name": "reviewer",
                "windows": [
                    {"name": "review", "preferred_agents": ["claude", "codex", "gemini"]},
                ],
            },
            {"name": "scratch", "runtime": "terminal"},
        ],
    },
    "minimal": {
        "description": "Minimal workspace with single agent window and scratch",
        "slots": [
            {
                "name": "main",
                "windows": [
                    {"name": "agent", "preferred_agents": ["claude", "codex", "gemini"]},
                ],
            },
            {"name": "scratch", "runtime": "terminal"},
        ],
    },
}
