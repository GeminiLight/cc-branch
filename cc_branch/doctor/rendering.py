from __future__ import annotations

from ..models import DoctorReport, WorkspaceConfig, WorkspacePlan
from .checks import collect_doctor_report
from .messages import _describe_issue, _get_fix_suggestion


def render_doctor_report(report: DoctorReport) -> str:
    """Render a structured doctor report as human-readable text."""
    return _format_report(report)


def build_doctor_report(workspace: WorkspaceConfig, plan: WorkspacePlan) -> str:
    """Build a human-readable doctor report.

    Compatibility wrapper for existing callers. New code should use
    ``collect_doctor_report`` and render at the presentation edge.
    """
    return render_doctor_report(collect_doctor_report(workspace, plan))


def _format_report(report: DoctorReport) -> str:
    lines = [f"doctor: {report.project}", ""]
    has_errors = report.has_errors
    has_warnings = report.has_warnings

    for issue in report.issues:
        if issue.severity == "info":
            prefix = "✓"
        elif issue.severity == "warning":
            prefix = "⚠"
        else:
            prefix = "✗"

        desc = _describe_issue(issue.issue_type, issue.context)
        if issue.target.startswith("slot:"):
            lines.append(f"  {prefix} {issue.target[5:]}: {desc}")
        elif issue.target.startswith("agent:"):
            lines.append(f"  {prefix} {issue.target[6:]}: {desc}")
        elif "." in issue.target:
            lines.append(f"  {prefix} {issue.target}: {desc}")
        else:
            lines.append(f"{prefix} {desc}")

        suggestion = _get_fix_suggestion(issue.issue_type, issue.context)
        if suggestion:
            lines.append(f"    → {suggestion}")

    lines.append("")
    if has_errors:
        lines.append("✗ Issues found. Please fix the errors above before running 'cc-branch start'.")
    elif has_warnings:
        lines.append("⚠ Warnings found, but workspace should work.")
    else:
        lines.append("✓ All checks passed! Your workspace is ready to use.")
        lines.append("  Run: cc-branch start")

    return "\n".join(lines)

