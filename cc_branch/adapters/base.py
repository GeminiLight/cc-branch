"""Agent adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import AgentSpec


class AgentAdapter(ABC):
    """Protocol for agent-specific behavior."""

    @abstractmethod
    def build_launch_command(
        self,
        agent_spec: AgentSpec,
        context: dict[str, Any],
        *,
        session_id: str | None,
        bootstrapped: bool,
    ) -> tuple[str, list[str]]:
        """Return ``(launch_command, post_launch_commands)``."""

    @abstractmethod
    def build_label_commands(
        self,
        agent_spec: AgentSpec,
        context: dict[str, Any],
        *,
        label: str | None,
    ) -> list[str]:
        """Return post-launch commands needed to set the label."""

    @abstractmethod
    def supports_create(self) -> bool:
        """Whether this adapter can generate a create command."""

    @abstractmethod
    def supports_resume(self) -> bool:
        """Whether this adapter can generate a resume command."""
