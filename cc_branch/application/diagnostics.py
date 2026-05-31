"""Application-facing diagnostics use cases."""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import __version__
from ..config import load_workspace, project_dir_for_config
from ..doctor import collect_doctor_report, render_doctor_report
from ..models import DoctorReport, WorkspaceConfig, WorkspacePlan, WorkspaceState
from ..planner import plan_workspace
from ..schema import schema_summary
from ..state import load_state
from .results import ActionResult


def get_doctor_report(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    state: WorkspaceState | None = None,
) -> DoctorReport:
    """Return structured diagnostics for a workspace plan."""
    return collect_doctor_report(workspace, plan, state)


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
        report = get_doctor_report(workspace, plan, state)
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


def _redact_value(value: Any) -> Any:
    home = str(Path.home())
    if isinstance(value, str):
        return value.replace(home, "~")
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _redact_value(item) for key, item in value.items()}
    return value


def _file_info(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    stat = path.stat()
    return {
        "path": str(path),
        "exists": True,
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    }


def _default_log_dirs() -> list[Path]:
    home = Path.home()
    dirs = [
        home / ".cc-branch" / "logs",
        home / "Library" / "Logs" / "cc-branch",
        home / "Library" / "Logs" / "com.gemini-light.cc-branch",
        home
        / "Library"
        / "Application Support"
        / "com.gemini-light.cc-branch"
        / "logs",
    ]
    if sys.platform.startswith("win"):
        local_app_data = Path.home() / "AppData" / "Local"
        dirs.extend(
            [
                local_app_data / "cc-branch" / "logs",
                local_app_data / "com.gemini-light.cc-branch" / "logs",
            ]
        )
    else:
        dirs.extend(
            [
                home / ".local" / "state" / "cc-branch" / "logs",
                home / ".local" / "share" / "cc-branch" / "logs",
            ]
        )
    return dirs


def _tail_text(path: Path, *, limit: int = 64 * 1024) -> str:
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > limit:
            handle.seek(-limit, 2)
        return handle.read().decode("utf-8", errors="replace")


def collect_recent_logs(
    *,
    log_dirs: list[Path] | None = None,
    max_files: int = 5,
    max_lines: int = 80,
) -> dict[str, Any]:
    """Collect recent local logs from known app locations, redacted for support."""
    candidates = log_dirs or _default_log_dirs()
    files: list[Path] = []
    for directory in candidates:
        if not directory.exists() or not directory.is_dir():
            continue
        for path in directory.glob("*.log"):
            if path.is_file():
                files.append(path)
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)

    recent = []
    for path in files[:max_files]:
        lines = _tail_text(path).splitlines()[-max_lines:]
        recent.append(
            {
                "path": str(path),
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "lines": lines,
            }
        )
    return _redact_value(
        {
            "available": bool(recent),
            "candidate_dirs": [str(path) for path in candidates],
            "recent": recent,
            "note": None if recent else "No recent cc-branch log files were found in known app log locations.",
        }
    )


def get_diagnostic_bundle(
    config_path: Path,
    state_path: Path,
    *,
    backend_port: int | None = None,
    log_dirs: list[Path] | None = None,
) -> dict[str, Any]:
    """Return a redacted support bundle with workspace health metadata."""
    project_dir = project_dir_for_config(config_path)
    doctor_result = get_doctor_payload(config_path, state_path)
    project_name = project_dir.name
    try:
        if config_path.exists():
            project_name = load_workspace(config_path).project or project_name
    except Exception:
        pass

    bundle: dict[str, Any] = {
        "kind": "cc-branch-diagnostic-bundle",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "app": {
            "version": __version__,
        },
        "backend": {
            "port": backend_port,
            "source": os.environ.get("CC_BRANCH_BACKEND_SOURCE", "cli"),
        },
        "schema": schema_summary(),
        "project": {
            "name": project_name,
            "path": str(project_dir),
        },
        "files": {
            "config": _file_info(config_path),
            "state": _file_info(state_path),
        },
        "doctor": doctor_result.payload,
        "logs": collect_recent_logs(log_dirs=log_dirs),
    }
    return _redact_value(bundle)
