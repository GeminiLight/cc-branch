"""Config save workflow."""

from __future__ import annotations

from pathlib import Path

from ..results import ActionResult


def save_workspace_config(
    config_path: Path,
    state_path: Path,
    content: str,
    *,
    base_mtime: object | None = None,
    base_content_hash: str | None = None,
) -> ActionResult:
    """Validate and save workspace config content with conflict detection."""
    import cc_branch.application.config_workflows as workflows

    if config_path.exists() and (base_mtime is not None or base_content_hash):
        current_content = config_path.read_text(encoding="utf-8")
        current_version = workflows.file_version_payload(config_path, current_content)
        if not workflows.base_version_matches(
            current_version,
            base_mtime=base_mtime,
            base_content_hash=base_content_hash,
        ):
            return ActionResult(
                ok=False,
                code="config_conflict",
                message="Config changed on disk since it was opened.",
                payload={
                    "current_content": current_content,
                    **current_version,
                },
            )

    try:
        validation_issues = workflows.collect_config_issues(content, config_path)
        validation_errors = [issue for issue in validation_issues if issue.severity == "error"]
        if validation_errors:
            return ActionResult(
                ok=False,
                code="invalid_config",
                message=validation_errors[0].message,
                payload={"issues": [issue.to_dict() for issue in validation_issues]},
            )
        workspace = workflows.load_workspace_from_text(content, config_path)
        state = workflows.load_state(state_path)
        plan = workflows.plan_workspace(workspace, state, False)
        diagnostics = workflows.render_report(workflows.get_doctor_report(workspace, plan))
    except Exception as exc:
        return ActionResult(
            ok=False,
            code="invalid_config",
            message=str(exc),
        )

    workflows._write_text_atomic(config_path, content)
    saved_content = config_path.read_text(encoding="utf-8")
    return ActionResult(
        ok=True,
        code="config_saved",
        message="Config saved",
        payload={
            "path": str(config_path),
            "diagnostics": diagnostics,
            "issues": [issue.to_dict() for issue in validation_issues],
            **workflows.file_version_payload(config_path, saved_content),
        },
        warnings=tuple(issue.message for issue in validation_issues if issue.severity == "warning"),
    )
