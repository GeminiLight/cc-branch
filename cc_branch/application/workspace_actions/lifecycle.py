"""Workspace lifecycle action use cases."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...models import WorkspaceConfig, WorkspacePlan, WorkspaceState
from ...runtime.capabilities import (
    is_external_process_runtime,
    managed_slots,
)
from ..results import ActionResult
from .dependencies import WorkspaceActionDependencies
from .persistence import AppliedResultPersistence, applied_result_persistence
from .targets import WorkspaceTargetResolver, target_resolver


@dataclass(frozen=True)
class WorkspaceLifecycleActions:
    """Coordinates tmux/terminal lifecycle actions for a planned workspace."""

    dependencies: WorkspaceActionDependencies
    targets: WorkspaceTargetResolver = target_resolver
    persistence: AppliedResultPersistence = applied_result_persistence

    def stop_workspace(
        self,
        workspace: WorkspaceConfig,
        plan: WorkspacePlan,
        state: WorkspaceState,
        state_path: Path,
        *,
        target: str | None = None,
    ) -> ActionResult:
        target = self.targets.normalize_action_target(plan, target)
        target_slots = self.targets.target_slots(plan, target) if target else []
        managed_targets = self.targets.managed_action_targets(plan, target) if target else []
        if target and not target_slots:
            return ActionResult(
                ok=False,
                code="target_not_found",
                message=f"Cannot stop target: {target}",
                exit_code=1,
            )
        if target and not managed_targets:
            return ActionResult(
                ok=False,
                code="terminal_runtime_external",
                message="Terminal runtime is external; close the terminal window manually.",
                exit_code=1,
            )

        if target:
            for action_target in managed_targets:
                self.dependencies.stop_runtime_workspace(workspace, plan, action_target)
        else:
            self.dependencies.stop_runtime_workspace(workspace, plan, target)
        label = target or "workspace"
        return ActionResult(ok=True, code="stop_applied", message=f"Stopped {label}")

    def restart_workspace(
        self,
        workspace: WorkspaceConfig,
        plan: WorkspacePlan,
        state: WorkspaceState,
        state_path: Path,
        *,
        target: str | None = None,
        detach: bool = True,
    ) -> ActionResult:
        target = self.targets.normalize_action_target(plan, target)
        target_slots = self.targets.target_slots(plan, target) if target else []
        managed_targets = self.targets.managed_action_targets(plan, target) if target else []
        if target and not target_slots:
            return ActionResult(
                ok=False,
                code="target_not_found",
                message=f"Cannot restart target: {target}",
                exit_code=1,
            )
        if target and not managed_targets:
            return ActionResult(
                ok=False,
                code="terminal_runtime_external",
                message="Terminal runtime is external; open it with a terminal opener.",
                exit_code=1,
            )

        if target:
            results = []
            runtime_detach = True if len(managed_targets) > 1 else detach
            for action_target in managed_targets:
                results.extend(
                    self.dependencies.restart_runtime_workspace(
                        workspace,
                        plan,
                        action_target,
                        detach=runtime_detach,
                    )
                )
            self.persistence.persist(state_path, workspace, plan, results)
            if not detach and len(managed_targets) > 1:
                self.dependencies.attach_slot(plan, managed_targets[0])
            return ActionResult(
                ok=True,
                code="restart_applied",
                message=f"Restarted {target}",
                payload={"results": results},
            )

        tmux_slots = managed_slots(plan.slots)
        if not tmux_slots:
            return ActionResult(
                ok=False,
                code="no_tmux_runtime",
                message="No tmux runtime slots can be restarted in background.",
                exit_code=1,
            )

        self.dependencies.stop_runtime_workspace(workspace, plan)
        results = []
        for tmux_slot in tmux_slots:
            results.extend(self.dependencies.ensure_slot(tmux_slot, created_action="recreated"))
        self.persistence.persist(state_path, workspace, plan, results)
        if not detach:
            self.dependencies.attach_slot(plan, tmux_slots[0].name)
        return ActionResult(
            ok=True,
            code="restart_applied",
            message="Restarted workspace",
            payload={"results": results},
        )

    def launch_workspace(
        self,
        workspace: WorkspaceConfig,
        plan: WorkspacePlan,
        state: WorkspaceState,
        state_path: Path,
        *,
        target: str | None = None,
    ) -> ActionResult:
        target = self.targets.normalize_action_target(plan, target)
        target_slots = self.targets.target_slots(plan, target) if target else []
        managed_targets = self.targets.managed_action_targets(plan, target) if target else []
        if target and not target_slots:
            return ActionResult(
                ok=False,
                code="target_not_found",
                message=f"Cannot launch target: {target}",
                exit_code=1,
            )
        if target and not managed_targets:
            return ActionResult(
                ok=False,
                code="terminal_runtime_external",
                message="Terminal runtime is external; open it with a terminal opener.",
                exit_code=1,
            )

        slots = managed_slots(target_slots) if target else managed_slots(plan.slots)
        if not slots:
            return ActionResult(
                ok=False,
                code="no_tmux_runtime",
                message="No tmux runtime slots can be started in background. Open terminal slots directly.",
                exit_code=1,
            )

        results = []
        for planned_slot in slots:
            results.extend(
                self.dependencies.ensure_slot(
                    planned_slot,
                    custom_openers=plan.openers,
                    default_opener=plan.default_opener,
                )
            )
        self.persistence.persist(state_path, workspace, plan, results)

        label = target or "workspace"
        return ActionResult(
            ok=True,
            code="launch_applied",
            message=f"Launched {label}",
            payload={"results": results},
        )

    def start_workspace(
        self,
        workspace: WorkspaceConfig,
        plan: WorkspacePlan,
        state: WorkspaceState,
        state_path: Path,
        *,
        detach: bool = False,
    ) -> ActionResult:
        results = self.dependencies.apply_workspace(plan, detach=detach)
        self.persistence.persist(state_path, workspace, plan, results)
        return ActionResult(
            ok=True,
            code="start_applied",
            message="Started workspace",
            payload={"results": results},
        )

    def attach_workspace(
        self,
        workspace: WorkspaceConfig,
        plan: WorkspacePlan,
        state: WorkspaceState,
        state_path: Path,
        *,
        target: str,
    ) -> ActionResult:
        target = self.targets.normalize_action_target(plan, target) or target
        slot = self.targets.target_slot(plan, target)
        if slot is None:
            return ActionResult(
                ok=False,
                code="target_not_found",
                message=f"Cannot attach target: {target}",
                exit_code=1,
            )
        if is_external_process_runtime(slot.runtime):
            results = self.dependencies.ensure_slot(
                slot,
                custom_openers=plan.openers,
                default_opener=plan.default_opener,
            )
            self.persistence.persist(state_path, workspace, plan, results)
            return ActionResult(
                ok=True,
                code="attach_applied",
                message=f"Opened {target}",
                payload={"results": results},
            )

        self.dependencies.attach_slot(plan, target)
        return ActionResult(ok=True, code="attach_applied", message=f"Attached {target}")

    def open_dashboard_workspace(
        self,
        workspace: WorkspaceConfig,
        plan: WorkspacePlan,
        state: WorkspaceState,
        state_path: Path,
    ) -> ActionResult:
        results = []
        for slot in self.targets.tmux_slots(plan):
            results.extend(
                self.dependencies.ensure_slot(
                    slot,
                    custom_openers=plan.openers,
                    default_opener=plan.default_opener,
                )
            )
        self.persistence.persist(state_path, workspace, plan, results)
        self.dependencies.open_dashboard(workspace, plan)
        return ActionResult(
            ok=True,
            code="dashboard_opened",
            message="Opened dashboard",
            payload={"results": results},
        )
