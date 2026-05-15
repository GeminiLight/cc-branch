"""Workspace opener policy use case."""

from __future__ import annotations

import shlex
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ...config import project_dir_for_config, resolve_config_path
from ...models import SlotPlan, WorkspaceConfig, WorkspacePlan, WorkspaceState
from ...openers import OpenIntent
from ...runtime.capabilities import is_external_process_runtime, is_managed_runtime
from ..results import ActionResult
from .command_specs import WorkspaceCommandSpecs, command_specs
from .dependencies import WorkspaceActionDependencies
from .persistence import AppliedResultPersistence, applied_result_persistence
from .targets import WorkspaceTargetResolver, target_resolver


@dataclass(frozen=True)
class WorkspaceOpenActions:
    """Applies opener-specific policy for workspace, project, and target opens."""

    dependencies: WorkspaceActionDependencies
    targets: WorkspaceTargetResolver = target_resolver
    specs: WorkspaceCommandSpecs = command_specs
    persistence: AppliedResultPersistence = applied_result_persistence

    def open_workspace(
        self,
        workspace: WorkspaceConfig,
        plan: WorkspacePlan,
        state: WorkspaceState,
        state_path: Path,
        *,
        cwd: Path,
        cli: str,
        opener: str,
        target: str | None = None,
        intent: OpenIntent | None = None,
    ) -> ActionResult:
        target = self.targets.normalize_action_target(plan, target)
        custom_openers = plan.openers
        opener_name = self.dependencies.opener_label(opener, custom_openers)
        if intent is None:
            intent = OpenIntent(kind="attach_target", target=target) if target else OpenIntent(kind="workspace_dashboard")
        elif intent.kind == "attach_target":
            intent = OpenIntent(kind="attach_target", target=target)

        if intent.kind == "project_folder":
            self.dependencies.open_with(
                opener_id=opener,
                cwd=cwd,
                cli=cli,
                intent=intent,
                custom_openers=custom_openers,
            )
            return ActionResult(ok=True, code="open_applied", message=f"Opened project in {opener_name}")

        if intent.kind == "attach_target" and target:
            return self._open_target(
                workspace,
                plan,
                state_path,
                cwd=cwd,
                cli=cli,
                opener=opener,
                opener_name=opener_name,
                target=target,
                custom_openers=custom_openers,
            )

        return self._open_whole_workspace(
            workspace,
            plan,
            state_path,
            cwd=cwd,
            cli=cli,
            opener=opener,
            opener_name=opener_name,
            custom_openers=custom_openers,
        )

    def _open_target(
        self,
        workspace: WorkspaceConfig,
        plan: WorkspacePlan,
        state_path: Path,
        *,
        cwd: Path,
        cli: str,
        opener: str,
        opener_name: str,
        target: str,
        custom_openers,
    ) -> ActionResult:
        attach_cli = self._attach_cli(workspace, cli)
        slot, window = self.targets.resolve_target(plan, target)
        if slot is None:
            return ActionResult(
                ok=False,
                code="target_not_found",
                message=f"Cannot open target: {target}",
                exit_code=1,
            )
        if self.dependencies.opener_supports(opener, "workspace_file", custom_openers):
            if is_managed_runtime(slot.runtime):
                self._ensure_tmux_slots(
                    workspace,
                    plan,
                    state_path,
                    [slot],
                )
            specs = self.specs.attach_target_specs(slot, window, target, attach_cli)
            self.dependencies.open_workspace_file(
                opener,
                cwd=cwd,
                commands=specs,
                custom_openers=custom_openers,
            )
            return ActionResult(ok=True, code="open_applied", message=f"Opened {target} in {opener_name}")
        if self._opens_as_project_folder(opener, custom_openers):
            self.dependencies.open_with(
                opener_id=opener,
                cwd=cwd,
                cli=cli,
                intent=OpenIntent(kind="project_folder"),
                custom_openers=custom_openers,
            )
            return ActionResult(ok=True, code="open_applied", message=f"Opened project in {opener_name}")
        if is_external_process_runtime(slot.runtime):
            specs = self.specs.attach_target_specs(slot, window, target, attach_cli)
            self.dependencies.open_command_layout(opener, specs, custom_openers=custom_openers)
            return ActionResult(ok=True, code="open_applied", message=f"Opened {target} in {opener_name}")

        if self.dependencies.opener_supports(opener, "layout", custom_openers):
            self._ensure_tmux_slots(workspace, plan, state_path, [slot])
            specs = self.specs.attach_target_specs(slot, window, target, attach_cli)
            self.dependencies.open_command_layout(opener, specs, custom_openers=custom_openers)
            return ActionResult(ok=True, code="open_applied", message=f"Opened {target} in {opener_name}")

        if not self.dependencies.opener_supports(opener, "attach_target", custom_openers):
            return ActionResult(
                ok=False,
                code="unsupported_opener",
                message=f"Opener {opener} does not support attach_target",
                exit_code=1,
            )

        self._ensure_tmux_slots(workspace, plan, state_path, [slot])
        self.dependencies.open_with(
            opener_id=opener,
            cwd=cwd,
            cli=cli,
            intent=OpenIntent(kind="attach_target", target=target),
            custom_openers=custom_openers,
        )
        return ActionResult(ok=True, code="open_applied", message=f"Opened {target} in {opener_name}")

    def _open_whole_workspace(
        self,
        workspace: WorkspaceConfig,
        plan: WorkspacePlan,
        state_path: Path,
        *,
        cwd: Path,
        cli: str,
        opener: str,
        opener_name: str,
        custom_openers,
    ) -> ActionResult:
        attach_cli = self._attach_cli(workspace, cli)
        tmux_slots = self.targets.tmux_slots(plan)
        terminal_slots = self.targets.terminal_slots(plan)
        if not tmux_slots and not terminal_slots:
            return ActionResult(ok=False, code="no_slots", message="No slots configured", exit_code=1)

        if self.dependencies.opener_supports(opener, "layout", custom_openers):
            self._ensure_tmux_slots(workspace, plan, state_path, tmux_slots)
            specs = [
                *self.specs.tmux_slot_attach_specs(tmux_slots, attach_cli),
                *self.specs.terminal_command_specs(terminal_slots),
            ]
            self.dependencies.open_command_layout(opener, specs, custom_openers=custom_openers)
            return ActionResult(ok=True, code="open_applied", message=f"Opened workspace in {opener_name}")

        if self.dependencies.opener_supports(opener, "workspace_file", custom_openers):
            self._ensure_tmux_slots(workspace, plan, state_path, tmux_slots)
            specs = [
                *self.specs.tmux_slot_attach_specs(tmux_slots, attach_cli),
                *self.specs.terminal_command_specs(terminal_slots),
            ]
            self.dependencies.open_workspace_file(opener, cwd=cwd, commands=specs, custom_openers=custom_openers)
            return ActionResult(ok=True, code="open_applied", message=f"Opened workspace in {opener_name}")

        if self._opens_as_project_folder(opener, custom_openers):
            self.dependencies.open_with(
                opener_id=opener,
                cwd=cwd,
                cli=cli,
                intent=OpenIntent(kind="project_folder"),
                custom_openers=custom_openers,
            )
            return ActionResult(ok=True, code="open_applied", message=f"Opened project in {opener_name}")

        if not tmux_slots:
            self.dependencies.open_command_layout(
                opener,
                self.specs.terminal_command_specs(terminal_slots),
                custom_openers=custom_openers,
            )
            return ActionResult(ok=True, code="open_applied", message="Opened terminal slots")

        self._ensure_tmux_slots(workspace, plan, state_path, tmux_slots)
        self.dependencies.open_with(
            opener_id=opener,
            cwd=cwd,
            cli=cli,
            intent=OpenIntent(kind="workspace_dashboard"),
            custom_openers=custom_openers,
        )
        if terminal_slots:
            self.dependencies.open_command_layout(
                opener,
                self.specs.terminal_command_specs(terminal_slots),
                custom_openers=custom_openers,
            )
            return ActionResult(
                ok=True,
                code="open_applied",
                message=f"Opened tmux dashboard and terminal slots in {opener_name}",
            )
        return ActionResult(ok=True, code="open_applied", message=f"Opened workspace dashboard in {opener_name}")

    def _attach_cli(self, workspace: WorkspaceConfig, cli: str) -> str:
        config_path = getattr(workspace, "_config_path", "")
        if not config_path:
            return cli
        selected = Path(str(config_path))
        default = resolve_config_path(project_dir_for_config(selected))
        if selected.resolve(strict=False) == default.resolve(strict=False):
            return cli
        return f"{cli} --config {shlex.quote(str(selected))}"

    def _opens_as_project_folder(self, opener: str, custom_openers) -> bool:
        return (
            self.dependencies.opener_supports(opener, "open_project", custom_openers)
            and not self.dependencies.opener_supports(opener, "run_command", custom_openers)
            and not self.dependencies.opener_supports(opener, "layout", custom_openers)
        )

    def _ensure_tmux_slots(
        self,
        workspace: WorkspaceConfig,
        plan: WorkspacePlan,
        state_path: Path,
        slots: Iterable[SlotPlan],
    ) -> list:
        results = []
        for slot in slots:
            if not is_managed_runtime(slot.runtime):
                continue
            results.extend(
                self.dependencies.ensure_slot(
                    slot,
                    custom_openers=plan.openers,
                    default_opener=plan.default_opener,
                )
            )
        self.persistence.persist(state_path, workspace, plan, results)
        return results
