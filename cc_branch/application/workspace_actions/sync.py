"""Workspace runtime sync use case."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...models import WorkspaceConfig, WorkspacePlan, WorkspaceState
from ...runtime.sync import (
    build_runtime_sync_report,
    extra_window_targets,
    reconcilable_targets,
    record_applied_results,
)
from ..results import ActionResult
from .dependencies import WorkspaceActionDependencies
from .persistence import AppliedResultPersistence, applied_result_persistence
from .targets import WorkspaceTargetResolver, target_resolver


@dataclass(frozen=True)
class WorkspaceSyncActions:
    """Reconciles runtime tmux windows with the current workspace plan."""

    dependencies: WorkspaceActionDependencies
    persistence: AppliedResultPersistence = applied_result_persistence
    targets: WorkspaceTargetResolver = target_resolver

    def sync_workspace(
        self,
        workspace: WorkspaceConfig,
        plan: WorkspacePlan,
        state: WorkspaceState,
        state_path: Path,
        *,
        target: str | None = None,
        stop_removed: bool = False,
        apply_changes: bool = True,
    ) -> ActionResult:
        target = self.targets.normalize_action_target(plan, target)
        report = build_runtime_sync_report(workspace, plan, state)
        targets = tuple(reconcilable_targets(report, target))
        extra_targets = tuple(extra_window_targets(report, target)) if stop_removed else ()

        if not apply_changes:
            if targets or extra_targets:
                return ActionResult(
                    ok=False,
                    code="sync_pending",
                    message="Runtime changes need sync",
                    changed_targets=targets,
                    payload={"extra_targets": extra_targets},
                )
            return ActionResult(
                ok=True,
                code="sync_noop",
                message="No changed, missing, or untracked tmux windows need sync",
                payload={"extra_targets": extra_targets},
            )

        current_state = state
        results = []
        applied_targets = 0
        for sync_target in targets:
            current_report = build_runtime_sync_report(workspace, plan, current_state)
            if sync_target not in reconcilable_targets(current_report, target):
                continue
            target_results = self.dependencies.restart_runtime_workspace(
                workspace,
                plan,
                sync_target,
                detach=True,
            )
            applied_targets += 1
            results.extend(target_results)
            current_state = record_applied_results(current_state, workspace, plan, target_results)

        stopped_extra = tuple(self.dependencies.stop_extra_windows(report, target) if stop_removed else [])
        if results:
            self.persistence.persist(state_path, workspace, plan, results)

        if targets or stopped_extra:
            message = f"Synced {applied_targets} target(s)"
            if stopped_extra:
                message += f" and stopped {len(stopped_extra)} extra window(s)"
            return ActionResult(
                ok=True,
                code="sync_applied",
                message=message,
                changed_targets=targets,
                payload={
                    "extra_targets": extra_targets,
                    "stopped_extra": stopped_extra,
                    "applied_targets": applied_targets,
                    "results": results,
                },
            )

        return ActionResult(
            ok=True,
            code="sync_noop",
            message="No changed, missing, or untracked tmux windows need sync",
            payload={"extra_targets": extra_targets, "stopped_extra": stopped_extra},
        )
