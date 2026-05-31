"""Workspace diagnostics facade."""

from __future__ import annotations

from pathlib import Path

from ..models import DoctorReport, WorkspaceConfig, WorkspacePlan, WorkspaceState
from ..runtime import which
from . import autofix as _autofix
from . import checks as _checks
from .rendering import render_doctor_report


def collect_doctor_report(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    state: WorkspaceState | None = None,
) -> DoctorReport:
    _checks.which = which
    return _checks.collect_doctor_report(workspace, plan, state)


def build_doctor_report(
    workspace: WorkspaceConfig,
    plan: WorkspacePlan,
    state: WorkspaceState | None = None,
) -> str:
    return render_doctor_report(collect_doctor_report(workspace, plan, state))


def auto_fix_issues(workspace: WorkspaceConfig, plan: WorkspacePlan, state_path: Path) -> bool:
    _checks.which = which
    _autofix.checks.which = which
    return _autofix.auto_fix_issues(workspace, plan, state_path)


__all__ = [
    "auto_fix_issues",
    "build_doctor_report",
    "collect_doctor_report",
    "render_doctor_report",
    "which",
]
