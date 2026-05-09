"""Environment inspection for first-run bootstrap."""

from __future__ import annotations

import os
from pathlib import Path

from ..agent_registry import load_agent_registry
from ..constants import DEFAULT_CONFIG, DEFAULT_STATE
from ..runtime import which
from .models import AgentStatus, EnvironmentReport


def check_environment(
    target_dir: Path,
    timeout: float = 2.0,
) -> EnvironmentReport:
    """Check runtime and agent CLI availability.

    ``timeout`` is retained for API compatibility. Current checks use PATH
    lookup only, so they are bounded by the operating system.
    """
    del timeout

    tmux_path = which("tmux")
    tmux_available = tmux_path is not None

    agents: list[AgentStatus] = []
    registry = load_agent_registry(cwd=target_dir)
    for name, definition in registry.items():
        command = definition.command
        try:
            agent_path = which(command)
        except Exception:
            agent_path = None

        agents.append(
            AgentStatus(
                name=name,
                command=command,
                status="ok" if agent_path else "missing",
                path=agent_path,
                install_hint=definition.install_hint,
            )
        )

    config_path = target_dir / DEFAULT_CONFIG
    state_path = target_dir / DEFAULT_STATE

    return EnvironmentReport(
        tmux_available=tmux_available,
        tmux_path=tmux_path,
        agents=agents,
        config_exists=config_path.exists(),
        state_exists=state_path.exists(),
        has_write_permission=os.access(target_dir, os.W_OK),
    )
