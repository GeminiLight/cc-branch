"""State persistence helpers for workspace action results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...models import WorkspaceConfig, WorkspacePlan
from ...runtime.sync import record_applied_results
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
    ) -> None:
        if not results:
            return
        StateStore(state_path).update(
            lambda latest_state: record_applied_results(latest_state, workspace, plan, results)
        )


applied_result_persistence = AppliedResultPersistence()


def _persist_applied_results(
    state_path: Path,
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    results: list,
) -> None:
    applied_result_persistence.persist(state_path, workspace, plan, results)
