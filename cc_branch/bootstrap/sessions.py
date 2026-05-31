"""Session metadata bootstrap helpers."""

from __future__ import annotations

from ..models import WorkspaceConfig, WorkspaceState


def bootstrap_sessions(
    workspace: WorkspaceConfig,
    state: WorkspaceState,
) -> WorkspaceState:
    """Generate missing session metadata for agents with generated IDs."""
    from ..planner import plan_workspace
    from ..state import merge_state

    plan = plan_workspace(workspace, state, bootstrap_missing=True)
    return merge_state(state, plan.state_updates)
