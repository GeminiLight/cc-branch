"""Workspace window launch-state updates."""

from __future__ import annotations

from pathlib import Path

import yaml

from ...models import WindowConfig
from ...planner import plan_workspace
from ...state import load_state
from ..results import ActionResult
from .versioning import file_version_payload, write_text_atomic


def set_window_enabled(
    config_path: Path,
    state_path: Path,
    target: str,
    enabled: bool,
) -> ActionResult:
    """Persist whether a planned window should be opened by launch/restart."""
    import cc_branch.application.config_workflows as workflows
    from cc_branch.application.workspace_actions.targets import target_resolver

    workspace = workflows.load_workspace(config_path)
    state = load_state(state_path)
    plan = plan_workspace(workspace, state, False)
    slot, window = target_resolver.resolve_target(plan, target)
    if slot is None:
        return ActionResult(
            ok=False,
            code="target_not_found",
            message=f"Cannot update window: {target}",
            exit_code=1,
        )
    if window is None:
        if len(slot.windows) != 1:
            return ActionResult(
                ok=False,
                code="window_target_required",
                message=f"Target must identify one pane/window: {target}",
                exit_code=1,
            )
        window = slot.windows[0]

    config_slot = workspace.get_slot(slot.name)
    if config_slot is None:
        return ActionResult(
            ok=False,
            code="target_not_found",
            message=f"Cannot update window: {target}",
            exit_code=1,
        )

    if not config_slot.windows:
        config_slot.windows = [
            WindowConfig(
                name=window.name,
                enabled=enabled,
                agent=config_slot.agent,
                command=config_slot.command,
                cwd=None,
                env={},
                remote=None,
                session=config_slot.session,
                label=config_slot.label,
            )
        ]
    else:
        config_window = next((item for item in config_slot.windows if item.name == window.name), None)
        if config_window is None:
            return ActionResult(
                ok=False,
                code="target_not_found",
                message=f"Cannot update window: {target}",
                exit_code=1,
            )
        config_window.enabled = enabled

    content = _workspace_yaml(workspace)
    try:
        validation_issues = workflows.collect_config_issues(content, config_path)
        validation_errors = [issue for issue in validation_issues if issue.severity == "error"]
        if validation_errors:
            return ActionResult(
                ok=False,
                code="invalid_config",
                message=validation_errors[0].message,
                payload={"issues": [issue.to_dict() for issue in validation_issues]},
                exit_code=1,
            )
    except Exception as exc:
        return ActionResult(ok=False, code="invalid_config", message=str(exc), exit_code=1)

    write_text_atomic(config_path, content)
    saved_content = config_path.read_text(encoding="utf-8")
    return ActionResult(
        ok=True,
        code="window_enabled_updated",
        message=f"{'Enabled' if enabled else 'Disabled'} {slot.name}:{window.name}",
        payload={
            "target": f"{slot.name}:{window.name}",
            "enabled": enabled,
            "path": str(config_path),
            "issues": [issue.to_dict() for issue in validation_issues],
            **file_version_payload(config_path, saved_content),
        },
    )


def _workspace_yaml(workspace) -> str:
    data = workspace.to_dict()
    data.pop("_config_path", None)
    if not data.get("openers"):
        data.pop("openers", None)
    display = data.get("display")
    if display == {"mode": "grid", "columns": 2, "dashboard": False}:
        data.pop("display", None)
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
