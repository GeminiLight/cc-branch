"""Canonical data models for cc-branch workspace configuration and plans."""

from __future__ import annotations

from .agents import AgentSpec
from .config import DisplayConfig, SlotConfig, WindowConfig, WorkspaceConfig
from .diagnostics import DoctorReport, Issue
from .openers import OpenerSpec
from .plan import SlotPlan, WindowPlan, WorkspacePlan
from .state import AppliedWindowResult, SlotState, WindowState, WorkspaceState

__all__ = [
    "AgentSpec",
    "AppliedWindowResult",
    "DisplayConfig",
    "DoctorReport",
    "Issue",
    "OpenerSpec",
    "SlotConfig",
    "SlotPlan",
    "SlotState",
    "WindowConfig",
    "WindowPlan",
    "WindowState",
    "WorkspaceConfig",
    "WorkspacePlan",
    "WorkspaceState",
]
