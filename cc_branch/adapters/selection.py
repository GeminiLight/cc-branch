"""Agent adapter selection."""

from __future__ import annotations

from ..models import AgentSpec
from .base import AgentAdapter
from .none import NoneAdapter
from .resume import FlagResumeAdapter, InternalResumeAdapter


def get_adapter(agent_spec: AgentSpec | None) -> AgentAdapter:
    """Return the adapter matching an agent specification."""
    if agent_spec is None:
        return NoneAdapter()
    if agent_spec.resume_mode == "flag":
        return FlagResumeAdapter(agent_spec)
    if agent_spec.resume_mode == "internal":
        return InternalResumeAdapter()
    return NoneAdapter()
