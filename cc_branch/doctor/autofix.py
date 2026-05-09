from __future__ import annotations

import uuid
from pathlib import Path

from ..constants import DEFAULT_STATE
from ..models import WindowState, WorkspaceConfig, WorkspacePlan
from ..state import load_state, save_state
from . import checks


def _fix_missing_directories(plan: WorkspacePlan) -> bool:
    """Create any working directories that do not yet exist."""
    fixed = False
    print("Checking for missing directories...")
    for slot in plan.slots:
        for window in slot.windows:
            cwd = Path(window.cwd)
            if not cwd.exists():
                try:
                    cwd.mkdir(parents=True, exist_ok=True)
                    print(f"  ✓ Created directory: {cwd}")
                    fixed = True
                except OSError as e:
                    print(f"  ✗ Failed to create {cwd}: {e}")
    return fixed


def _fix_missing_session_ids(plan: WorkspacePlan, state_path: Path) -> bool:
    """Generate UUID session IDs for windows that need them."""

    print("\nChecking for missing session IDs...")
    state = load_state(state_path)
    fixed = False
    needs_save = False

    for slot in plan.slots:
        for window in slot.windows:
            if (
                window.agent
                and window.resume_mode != "none"
                and not window.resolved_session_id
                and window.create_mode == "generated_uuid"
            ):
                needs_save = True
                key = f"{slot.name}.{window.name}"
                existing = state.get_window(key)
                if not existing or not existing.session_id:
                    session_id = str(uuid.uuid4())
                    state.set_window(
                        key,
                        WindowState(
                            session_id=session_id,
                            label=window.resolved_label or (existing.label if existing else ""),
                            agent=window.agent,
                            slot=slot.name,
                            window=window.name,
                        ),
                    )
                    print(f"  ✓ Generated session ID for {key}")
                    fixed = True

    if needs_save:
        save_state(state_path, state)
        print(f"  ✓ Saved updated state to {state_path}")

    return fixed




def _fix_gitignore_state(workspace_root: Path) -> bool:
    """Ensure the state file is listed in ``.gitignore``."""
    print("\nChecking .gitignore...")
    gitignore_path = workspace_root / ".gitignore"
    state_filename = DEFAULT_STATE

    if gitignore_path.exists():
        content = gitignore_path.read_text()
        lines = [line.strip() for line in content.splitlines()]
        if state_filename not in lines:
            try:
                with gitignore_path.open("a") as f:
                    f.write(f"\n# CC Branch state (machine-specific)\n{state_filename}\n")
                print(f"  ✓ Added {state_filename} to .gitignore")
                return True
            except OSError as e:
                print(f"  ✗ Failed to update .gitignore: {e}")
                return False
        else:
            print(f"  ✓ {state_filename} already in .gitignore")
            return False

    try:
        gitignore_path.write_text(f"# CC Branch state (machine-specific)\n{state_filename}\n")
        print(f"  ✓ Created .gitignore with {state_filename}")
        return True
    except OSError as e:
        print(f"  ✗ Failed to create .gitignore: {e}")
        return False


def _report_manual_issues(workspace: WorkspaceConfig, plan: WorkspacePlan) -> None:
    """Print a list of issues that still require manual attention."""
    print("\nIssues that require manual fixing:")
    issues = checks._build_agent_issues(workspace) + checks._build_slot_issues(plan) + checks._build_window_issues(plan)
    manual = [i for i in issues if i.severity == "error" and not i.fixable]
    for issue in manual:
        print(f"  ✗ {issue.message}")
        if issue.context.get("hint"):
            print(f"    → {issue.context['hint']}")
    if not manual:
        print("  ✓ No manual fixes needed")


def auto_fix_issues(
    workspace: WorkspaceConfig, plan: WorkspacePlan, state_path: Path
) -> bool:
    """Automatically fix simple issues. Returns True if any fixes were applied."""
    fixes_applied = (
        _fix_missing_directories(plan)
        | _fix_missing_session_ids(plan, state_path)
        | _fix_gitignore_state(Path(workspace.root))
    )
    _report_manual_issues(workspace, plan)
    return fixes_applied
