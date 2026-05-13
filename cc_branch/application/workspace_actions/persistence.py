"""State persistence helpers for workspace action results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...models import WorkspaceConfig, WorkspacePlan
from ...runtime.sync import record_applied_results
from ..session_binding import SessionBindingResult, bind_discovered_agent_sessions
from ..state_store import StateStore


@dataclass(frozen=True)
class AppliedResultPersistence:
    """Persists runtime application results into the workspace state file."""

    def persist(
        self,
        state_path: Path,
        workspace: WorkspaceConfig,
        plan: WorkspacePlan,
        results: list,
    ) -> list[SessionBindingResult]:
        if not results:
            return []
        bindings: list[SessionBindingResult] = []

        def _update(latest_state):
            nonlocal bindings
            next_state = record_applied_results(latest_state, workspace, plan, results)
            next_state, bindings = bind_discovered_agent_sessions(
                next_state,
                workspace,
                plan,
                results,
                project_dir=Path(workspace.root).resolve(),
            )
            return next_state

        StateStore(state_path).update(_update)
        return bindings


applied_result_persistence = AppliedResultPersistence()


def _persist_applied_results(
    state_path: Path,
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    results: list,
) -> list[SessionBindingResult]:
    return applied_result_persistence.persist(state_path, workspace, plan, results)
