"""Application-facing diagnostics use cases."""

from __future__ import annotations

from pathlib import Path

from ..config import load_workspace, project_dir_for_config
from ..doctor import collect_doctor_report, render_doctor_report
from ..models import DoctorReport, WorkspaceConfig, WorkspacePlan
from ..planner import plan_workspace
from ..state import load_state
from .results import ActionResult


def get_doctor_report(workspace: WorkspaceConfig, plan: WorkspacePlan) -> DoctorReport:
    """Return structured diagnostics for a workspace plan."""
    return collect_doctor_report(workspace, plan)


def render_report(report: DoctorReport) -> str:
    """Render diagnostics for text-oriented presentation surfaces."""
    return render_doctor_report(report)


def get_doctor_payload(config_path: Path, state_path: Path) -> ActionResult:
    """Load and render structured doctor diagnostics for presentation surfaces."""
    project_dir = project_dir_for_config(config_path)
    if not project_dir.exists():
        return ActionResult(
            ok=True,
            code="workspace_missing",
            message="Project directory does not exist",
            payload={
                "status": "missing",
                "report": f"Project directory does not exist: {project_dir}",
            },
        )
    if not config_path.exists():
        return ActionResult(
            ok=True,
            code="workspace_needs_init",
            message="Workspace config not found",
            payload={
                "status": "needs_init",
                "report": (
                    "No workspace config found. "
                    "Create one from a starter profile or open the YAML editor."
                ),
            },
        )

    try:
        workspace = load_workspace(config_path)
        state = load_state(state_path)
        plan = plan_workspace(workspace, state, False)
        report = get_doctor_report(workspace, plan)
        return ActionResult(
            ok=True,
            code="doctor_ready",
            message="Doctor report loaded",
            payload={
                "status": "ready",
                "report": report.to_dict(),
                "text": render_report(report),
            },
        )
    except Exception as exc:
        return ActionResult(
            ok=False,
            code="invalid_config",
            message=str(exc),
            exit_code=1,
            payload={"status": "invalid_config", "report": str(exc), "error": str(exc)},
        )
