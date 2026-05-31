"""Data contracts for first-run workspace bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ..models import WorkspaceState


@dataclass
class AgentStatus:
    """Status of a single agent CLI."""

    name: str
    command: str
    status: Literal["ok", "missing", "not_authenticated"]
    path: str | None
    install_hint: str


@dataclass
class EnvironmentReport:
    """Complete environment check report."""

    tmux_available: bool
    tmux_path: str | None
    agents: list[AgentStatus]
    config_exists: bool
    state_exists: bool
    has_write_permission: bool

    @property
    def available_agents(self) -> list[str]:
        """Return available agent names."""
        return [a.name for a in self.agents if a.status == "ok"]

    @property
    def can_proceed(self) -> bool:
        """Check if init can proceed."""
        return self.has_write_permission

    @property
    def has_blockers(self) -> bool:
        """Check if there are blocking issues."""
        return not self.has_write_permission


@dataclass(frozen=True)
class ConfigSummary:
    """Counts extracted from a generated config."""

    slots: int
    windows: int
    agents: int


@dataclass(frozen=True)
class WorkspaceInitResult:
    """Artifacts produced by workspace initialization."""

    config_path: Path
    state_path: Path
    config_summary: ConfigSummary
    state: WorkspaceState
    gitignore_created: bool
    gitignore_updated: bool
