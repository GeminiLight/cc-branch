"""Target parsing and slot/window resolution for workspace actions."""

from __future__ import annotations

from dataclasses import dataclass

from ...models import WorkspacePlan
from ...openers import OpenIntent, OpenerError
from ...runtime.capabilities import external_process_slots, managed_slots
from ...targets import parse_target


@dataclass(frozen=True)
class WorkspaceTargetResolver:
    """Resolves user-facing workspace targets against a planned workspace."""

    def target_slot(self, plan: WorkspacePlan, target: str | None):
        if not target:
            return None
        slot, window = self.resolve_target(plan, target)
        if slot is None:
            return None
        if window is None:
            return slot
        return slot

    def resolve_target(self, plan: WorkspacePlan, target: str):
        parsed = parse_target(target)
        slot = plan.get_slot(parsed.slot)
        if slot is None:
            return None, None
        if parsed.window is None:
            return slot, None
        for window in slot.windows:
            if window.name == parsed.window:
                return slot, window
        return None, None

    def normalize_action_target(self, plan: WorkspacePlan, target: str | None) -> str | None:
        """Accept public targets plus older tmux session names from previous UIs."""
        if not target:
            return None
        for slot in plan.slots:
            if target == slot.tmux_session:
                return slot.name
        return target

    def resolve_open_intent(self, intent_name: str | None, public_target: str | None) -> OpenIntent:
        if intent_name is None:
            return (
                OpenIntent(kind="attach_target", target=public_target)
                if public_target
                else OpenIntent(kind="workspace_dashboard")
            )
        if intent_name == "project_folder":
            return OpenIntent(kind="project_folder")
        if intent_name == "workspace_dashboard":
            return OpenIntent(kind="workspace_dashboard")
        if intent_name == "attach_target":
            return OpenIntent(kind="attach_target", target=public_target)
        raise OpenerError(f"Unknown open intent: {intent_name}")

    def managed_slots(self, plan: WorkspacePlan):
        return managed_slots(plan.slots)

    def external_process_slots(self, plan: WorkspacePlan):
        return external_process_slots(plan.slots)

    def tmux_slots(self, plan: WorkspacePlan):
        return self.managed_slots(plan)

    def terminal_slots(self, plan: WorkspacePlan):
        return self.external_process_slots(plan)


target_resolver = WorkspaceTargetResolver()


def _target_slot(plan: WorkspacePlan, target: str | None):
    return target_resolver.target_slot(plan, target)


def _resolve_target(plan: WorkspacePlan, target: str):
    return target_resolver.resolve_target(plan, target)


def _normalize_action_target(plan: WorkspacePlan, target: str | None) -> str | None:
    return target_resolver.normalize_action_target(plan, target)


def _resolve_open_intent(intent_name: str | None, public_target: str | None) -> OpenIntent:
    return target_resolver.resolve_open_intent(intent_name, public_target)


def _tmux_slots(plan: WorkspacePlan):
    return target_resolver.tmux_slots(plan)


def _terminal_slots(plan: WorkspacePlan):
    return target_resolver.terminal_slots(plan)
