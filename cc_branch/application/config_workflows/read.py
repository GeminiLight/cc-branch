"""Config read and project probe workflows."""

from __future__ import annotations

from pathlib import Path

from ...constants import DEFAULT_STATE
from ..results import ActionResult


def read_workspace_config(config_path: Path, state_path: Path) -> ActionResult:
    """Read config editor payload for an existing or not-yet-initialized project."""
    import cc_branch.application.config_workflows as workflows

    base_payload = {
        "content": "",
        "path": str(config_path),
        "project_path": str(config_path.parent),
        "state_path": str(state_path),
    }
    if not config_path.parent.exists():
        return ActionResult(
            ok=True,
            code="config_missing",
            message="Project directory does not exist",
            payload={"status": "missing", "exists": False, **base_payload},
        )
    if not config_path.exists():
        return ActionResult(
            ok=True,
            code="config_needs_init",
            message="Workspace config not found",
            payload={"status": "needs_init", "exists": False, **base_payload},
        )

    content = config_path.read_text(encoding="utf-8")
    validation_issues = workflows.collect_config_issues(content, config_path)
    return ActionResult(
        ok=True,
        code="config_ready",
        message="Config loaded",
        warnings=tuple(issue.message for issue in validation_issues if issue.severity == "warning"),
        payload={
            "status": "ready",
            "exists": True,
            **base_payload,
            "content": content,
            "issues": [issue.to_dict() for issue in validation_issues],
            **workflows.file_version_payload(config_path, content),
        },
    )


def probe_project(project_dir: Path) -> ActionResult:
    """Return project setup state for a possible cc-branch workspace."""
    import cc_branch.application.config_workflows as workflows

    path_exists = project_dir.exists() and project_dir.is_dir()
    config_path = workflows.resolve_config_path(project_dir)
    state_path = project_dir / DEFAULT_STATE
    config_exists = path_exists and config_path.exists()
    state_exists = path_exists and state_path.exists()

    status = "missing"
    project_name = project_dir.name or "project"
    slot_count = 0
    if path_exists and not config_exists:
        status = "needs_init"
    elif config_exists:
        try:
            workspace = workflows.load_workspace(config_path)
            project_name = workspace.project or project_name
            slot_count = len(workspace.slots)
            status = "ready"
        except Exception:
            status = "invalid_config"

    return ActionResult(
        ok=True,
        code="project_probe",
        message="Project probed",
        payload={
            "path": str(project_dir),
            "path_exists": path_exists,
            "config_exists": config_exists,
            "state_exists": state_exists,
            "project_name": project_name,
            "slots": slot_count,
            "status": status,
        },
    )
