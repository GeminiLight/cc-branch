"""Agent-facing message delivery use cases."""

from __future__ import annotations

from ..exceptions import ConfigError
from ..models import WorkspaceConfig, WorkspacePlan
from ..runtime.backends import get_backend
from ..runtime.capabilities import is_managed_runtime
from ..targets import parse_target
from .agent_bus import AgentBusStore, Clock
from .results import ActionResult


def _resolve_target(plan: WorkspacePlan, target: str):
    try:
        parsed = parse_target(target)
    except ConfigError:
        return None, None
    slot = plan.get_slot(parsed.slot)
    if slot is None:
        return None, None
    if parsed.window is None:
        return slot, None
    for window in slot.windows:
        if window.name == parsed.window:
            return slot, window
    return slot, None


def send_agent_message(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    target: str,
    message: str,
    *,
    bus_store: AgentBusStore | None = None,
    sender: str = "user",
    now: Clock | None = None,
) -> ActionResult:
    """Paste a message into a managed agent pane."""
    del workspace
    normalized_message = message.strip()
    if not target.strip():
        return ActionResult(
            ok=False,
            code="missing_target",
            message="Message target is required",
            exit_code=1,
        )
    if not normalized_message:
        return ActionResult(
            ok=False,
            code="missing_message",
            message="Message text is required",
            exit_code=1,
        )

    slot, window = _resolve_target(plan, target)
    if slot is None:
        return ActionResult(
            ok=False,
            code="target_not_found",
            message=f"Cannot send message to target: {target}",
            exit_code=1,
        )
    if window is None:
        launchable = slot.launchable_windows()
        if len(launchable) == 1:
            window = launchable[0]
        else:
            return ActionResult(
                ok=False,
                code="target_requires_window",
                message=f"Target must identify one pane/window: {target}",
                exit_code=1,
            )
    if not is_managed_runtime(slot.runtime):
        return ActionResult(
            ok=False,
            code="unsupported_runtime",
            message=f"Cannot send message to {target}: {slot.runtime} runtime is external",
            exit_code=1,
        )
    if not get_backend().has_window(slot.tmux_session, window.name):
        return ActionResult(
            ok=False,
            code="target_not_running",
            message=f"Cannot send message to {target}: pane is not running",
            exit_code=1,
        )

    get_backend().send_keys(f"{slot.tmux_session}:{window.name}", normalized_message)
    store = bus_store or AgentBusStore()
    event_kwargs = {"now": now} if now is not None else {}
    store.record_message_sent(
        target=f"{slot.name}:{window.name}",
        message=normalized_message,
        sender=sender,
        delivery="tmux",
        **event_kwargs,
    )
    return ActionResult(
        ok=True,
        code="message_sent",
        message=f"Sent message to {slot.name}:{window.name}",
        changed_targets=(f"{slot.name}:{window.name}",),
    )
