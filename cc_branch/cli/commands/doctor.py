"""CLI doctor command."""

from __future__ import annotations

import argparse
import json

from ...context import WorkspaceContext
from ..output import output_format


def run_doctor(ctx: WorkspaceContext, args: argparse.Namespace, workspace, plan, state) -> int:
    """Render diagnostics and optionally apply safe fixes."""
    import cc_branch.cli as cli

    report = cli.get_doctor_report(workspace, plan, state)
    if output_format(args) == "json":
        print(json.dumps({"report": report.to_dict(), "text": cli.render_report(report)}, indent=2))
    else:
        print(cli.render_report(report))

    if getattr(args, "fix", False):
        from ...doctor import auto_fix_issues

        print("\n" + "=" * 50)
        print("Attempting to fix issues automatically...")
        print("=" * 50 + "\n")
        fixes_applied = auto_fix_issues(workspace, plan, ctx.state_path)
        if fixes_applied:
            print("\n✓ Some issues were fixed. Run 'cc-branch doctor' again to verify.")
        else:
            print("\n⚠ No automatic fixes were applied. Please fix issues manually.")
    return 0
