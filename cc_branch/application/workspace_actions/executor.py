"""User-facing workspace action executor."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from ...config import load_workspace
from ...openers import OpenIntent
from ...planner import plan_workspace
from ...runtime.capabilities import is_external_process_runtime
from ...state import load_state
from ..results import ActionResult
from .dependencies import WorkspaceActionDependencies
from .lifecycle import WorkspaceLifecycleActions
from .open import WorkspaceOpenActions
from .sync import WorkspaceSyncActions
from .targets import WorkspaceTargetResolver, target_resolver


@dataclass(frozen=True)
class WorkspaceActionExecutor:
    """Loads workspace state and routes user-facing action requests to use cases."""

    dependencies: WorkspaceActionDependencies
    targets: WorkspaceTargetResolver = target_resolver

    def execute(
        self,
        config_path: Path,
        state_path: Path,
        *,
        action: str | None,
        target: str | None = None,
        opener: str | None = None,
        intent: str | None = None,
        stop_removed: bool = False,
        cli: str = "cc-branch",
    ) -> ActionResult:
        workspace = load_workspace(config_path)
        state = load_state(state_path)
        plan = plan_workspace(workspace, state, False)
        public_target = self.targets.normalize_action_target(plan, target)
        opener_id = opener or "auto-terminal"

        lifecycle = WorkspaceLifecycleActions(self.dependencies, targets=self.targets)
        opener_actions = WorkspaceOpenActions(self.dependencies, targets=self.targets)
        sync_actions = WorkspaceSyncActions(self.dependencies)

        if action == "stop":
            return lifecycle.stop_workspace(workspace, plan, state, state_path, target=public_target)

        if action == "restart":
            if public_target:
                slot = self.targets.target_slot(plan, public_target)
                if slot is None:
                    return ActionResult(
                        ok=False,
                        code="target_not_found",
                        message=f"Cannot restart target: {public_target}",
                        exit_code=1,
                    )
                if is_external_process_runtime(slot.runtime):
                    return opener_actions.open_workspace(
                        workspace,
                        plan,
                        state,
                        state_path,
                        cwd=config_path.parent,
                        cli=cli,
                        opener=opener_id,
                        target=public_target,
                        intent=OpenIntent(kind="attach_target", target=public_target),
                    )
            return lifecycle.restart_workspace(
                workspace,
                plan,
                state,
                state_path,
                target=public_target,
                detach=True,
            )

        if action == "launch":
            if public_target:
                slot = self.targets.target_slot(plan, public_target)
                if slot is None:
                    return ActionResult(
                        ok=False,
                        code="target_not_found",
                        message=f"Cannot launch target: {public_target}",
                        exit_code=1,
                    )
                if is_external_process_runtime(slot.runtime):
                    return opener_actions.open_workspace(
                        workspace,
                        plan,
                        state,
                        state_path,
                        cwd=config_path.parent,
                        cli=cli,
                        opener=opener_id,
                        target=public_target,
                        intent=OpenIntent(kind="attach_target", target=public_target),
                    )
            result = lifecycle.launch_workspace(workspace, plan, state, state_path, target=public_target)
            if public_target is None and result.ok and self.targets.terminal_slots(plan):
                return replace(result, message="Launched tmux slots; terminal slots open separately")
            return result

        if action == "open":
            return opener_actions.open_workspace(
                workspace,
                plan,
                state,
                state_path,
                cwd=config_path.parent,
                cli=cli,
                opener=opener_id,
                target=public_target,
                intent=self.targets.resolve_open_intent(intent, public_target),
            )

        if action == "sync":
            result = sync_actions.sync_workspace(
                workspace,
                plan,
                state,
                state_path,
                target=public_target,
                stop_removed=stop_removed,
                apply_changes=True,
            )
            if result.code == "sync_noop":
                return replace(result, message="No config changes to sync")
            return result

        return ActionResult(
            ok=False,
            code="invalid_action",
            message="Unknown or invalid action",
            exit_code=1,
        )
