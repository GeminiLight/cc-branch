"""Resume-capable agent adapters."""

from __future__ import annotations

from typing import Any

from ..models import AgentSpec
from ..templates import render_template
from .base import AgentAdapter


class FlagResumeAdapter(AgentAdapter):
    """Adapter for agents that resume via a CLI flag."""

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


class InternalResumeAdapter(AgentAdapter):
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
