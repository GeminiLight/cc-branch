"""Agent adapters abstract the differences between AI CLI tools.

Each adapter knows how to:
- generate a launch command (create vs resume)
- generate a label / rename command
- declare its capabilities (resume modes, create modes)

This keeps ``planner.py`` free of per-agent conditional logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import AgentSpec
from .templates import render_template


class AgentAdapter(ABC):
    """Protocol for agent-specific behaviour."""

    @abstractmethod
    def build_launch_command(
        self,
        agent_spec: AgentSpec,
        context: dict[str, Any],
        *,
        session_id: str | None,
        bootstrapped: bool,
    ) -> tuple[str, list[str]]:
        """Return (launch_command, post_launch_commands)."""

    @abstractmethod
    def build_label_commands(
        self,
        agent_spec: AgentSpec,
        context: dict[str, Any],
        *,
        label: str | None,
    ) -> list[str]:
        """Return list of post-launch commands needed to set the label."""

    @abstractmethod
    def supports_create(self) -> bool:
        """Whether this adapter can generate a create command."""

    @abstractmethod
    def supports_resume(self) -> bool:
        """Whether this adapter can generate a resume command."""


class _NoneAdapter(AgentAdapter):
    """Fallback adapter when no agent is bound or agent has no special behaviour."""

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


class _FlagResumeAdapter(AgentAdapter):
    """Adapter for agents that resume via a CLI flag (e.g. ``codex resume <id>``)."""

    def __init__(self, agent_spec: AgentSpec | None = None) -> None:
        self._agent_spec = agent_spec

    def build_launch_command(
        self,
        agent_spec: AgentSpec,
        context: dict[str, Any],
        *,
        session_id: str | None,
        bootstrapped: bool,
    ) -> tuple[str, list[str]]:
        base = agent_spec.command or context.get("agent_name", "")
        if bootstrapped and agent_spec.create_template:
            launch = render_template(agent_spec.create_template, context)
            return launch, []
        if session_id and agent_spec.resume_template:
            launch = f"{base} {render_template(agent_spec.resume_template, context)}".strip()
            return launch, []
        return base, []

    def build_label_commands(
        self,
        agent_spec: AgentSpec,
        context: dict[str, Any],
        *,
        label: str | None,
    ) -> list[str]:
        if label and agent_spec.label_mode == "internal" and agent_spec.rename_template:
            return [render_template(agent_spec.rename_template, context)]
        return []

    def supports_create(self) -> bool:
        if self._agent_spec is not None:
            return bool(self._agent_spec.create_template)
        return False

    def supports_resume(self) -> bool:
        return True


class _InternalResumeAdapter(AgentAdapter):
    """Adapter for agents that resume via an internal post-launch command."""

    def build_launch_command(
        self,
        agent_spec: AgentSpec,
        context: dict[str, Any],
        *,
        session_id: str | None,
        bootstrapped: bool,
    ) -> tuple[str, list[str]]:
        base = agent_spec.command or context.get("agent_name", "")
        post: list[str] = []
        if bootstrapped and agent_spec.create_template:
            launch = render_template(agent_spec.create_template, context)
            return launch, post
        if session_id and agent_spec.resume_template:
            post.append(render_template(agent_spec.resume_template, context))
            return base, post
        return base, post

    def build_label_commands(
        self,
        agent_spec: AgentSpec,
        context: dict[str, Any],
        *,
        label: str | None,
    ) -> list[str]:
        if label and agent_spec.label_mode == "internal" and agent_spec.rename_template:
            return [render_template(agent_spec.rename_template, context)]
        return []

    def supports_create(self) -> bool:
        return True

    def supports_resume(self) -> bool:
        return True


def get_adapter(agent_spec: AgentSpec | None) -> AgentAdapter:
    """Return the appropriate adapter for *agent_spec*.

    The adapter is selected based on ``resume_mode``:
    - ``"flag"`` → ``_FlagResumeAdapter``
    - ``"internal"`` → ``_InternalResumeAdapter``
    - anything else → ``_NoneAdapter``
    """
    if agent_spec is None:
        return _NoneAdapter()
    mode = agent_spec.resume_mode
    if mode == "flag":
        return _FlagResumeAdapter(agent_spec)
    if mode == "internal":
        return _InternalResumeAdapter()
    return _NoneAdapter()
