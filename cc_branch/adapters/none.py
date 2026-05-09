"""Fallback agent adapter."""

from __future__ import annotations

from typing import Any

from ..models import AgentSpec
from .base import AgentAdapter


class NoneAdapter(AgentAdapter):
    """Adapter for unbound agents or agents without special behavior."""

    def build_launch_command(
        self,
        agent_spec: AgentSpec,
        context: dict[str, Any],
        *,
        session_id: str | None,
        bootstrapped: bool,
    ) -> tuple[str, list[str]]:
        base = agent_spec.command or context.get("agent_name", "")
        return base, []

    def build_label_commands(
        self,
        agent_spec: AgentSpec,
        context: dict[str, Any],
        *,
        label: str | None,
    ) -> list[str]:
        return []

    def supports_create(self) -> bool:
        return False

    def supports_resume(self) -> bool:
        return False
