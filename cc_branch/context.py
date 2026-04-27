"""Workspace execution context.

Provides a single object that encapsulates the config → state → plan
pipeline so that CLI commands do not repeat the loading boilerplate.
"""

from __future__ import annotations

from pathlib import Path

from .config import load_workspace, resolve_config_path
from .constants import DEFAULT_STATE
from .models import WorkspaceConfig, WorkspacePlan, WorkspaceState
from .planner import plan_workspace
from .state import load_state, merge_state, save_state


class WorkspaceContext:
    """Holds the resolved workspace, state, and plan for a single command."""

    def __init__(
        self,
        cwd: Path,
        *,
        config_path: Path | str | None = None,
        state_path: Path | str | None = None,
    ) -> None:
        import os

        self._cwd = cwd
        # Allow the desktop wrapper (Tauri) to override paths via env vars.
        config_env = os.environ.get("CC_BRANCH_CONFIG")
        state_env = os.environ.get("CC_BRANCH_STATE")
        self._config_path = (
            Path(config_path)
            if config_path
            else Path(config_env)
            if config_env
            else resolve_config_path(cwd)
        )
        self._state_path = (
            Path(state_path)
            if state_path
            else Path(state_env)
            if state_env
            else cwd / DEFAULT_STATE
        )
        self._workspace: WorkspaceConfig | None = None
        self._state: WorkspaceState | None = None
        self._plan: WorkspacePlan | None = None

    @property
    def config_path(self) -> Path:
        return self._config_path

    @property
    def state_path(self) -> Path:
        return self._state_path

    def load(self, *, bootstrap_missing: bool = False) -> tuple[WorkspaceConfig, WorkspacePlan]:
        """Load workspace and state, resolving the plan.

        State is persisted immediately if bootstrapping produces new metadata.
        """
        workspace = load_workspace(self._config_path)
        state = load_state(self._state_path)
        plan = plan_workspace(workspace, state, bootstrap_missing)

        merged_state = merge_state(state, plan.state_updates)
        if merged_state != state:
            save_state(self._state_path, merged_state)
            state = merged_state

        self._workspace = workspace
        self._state = state
        self._plan = plan
        return workspace, plan

    @property
    def workspace(self) -> WorkspaceConfig:
        if self._workspace is None:
            raise RuntimeError("WorkspaceContext.load() must be called first")
        return self._workspace

    @property
    def plan(self) -> WorkspacePlan:
        if self._plan is None:
            raise RuntimeError("WorkspaceContext.load() must be called first")
        return self._plan

    @property
    def state(self) -> WorkspaceState:
        if self._state is None:
            raise RuntimeError("WorkspaceContext.load() must be called first")
        return self._state
