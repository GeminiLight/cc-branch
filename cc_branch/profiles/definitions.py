"""Built-in workspace profile templates."""

from __future__ import annotations

PROFILES = {
    "solo-dev": {
        "description": "Four-agent coding workspace with planning, building, testing, and review",
        "slots": [
            {
                "name": "dev",
                "windows": [
                    {"name": "planner", "preferred_agents": ["codex", "claude", "gemini"]},
                    {"name": "builder", "preferred_agents": ["codex", "claude", "gemini"]},
                    {"name": "tester", "preferred_agents": ["codex", "claude", "gemini"]},
                    {"name": "reviewer", "preferred_agents": ["claude", "codex", "gemini"]},
                ],
            },
        ],
    },
    "ai-pair": {
        "description": "Adversarial AI coding workflow with separate implementation and critique",
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
