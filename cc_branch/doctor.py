"""Workspace diagnostics with structured reports and safe auto-fixes.

Public API operates on typed models.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from .models import (
    DoctorReport,
    Issue,
    WindowState,
    WorkspaceConfig,
    WorkspacePlan,
)
from .runtime import which
from .shells import tmux_install_hint
from .state import load_state, save_state

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _duplicate_names(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    return sorted(duplicates)


def _valid_env_key(key: str) -> bool:
    return re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key) is not None


def _get_install_suggestion(agent_name: str, command: str) -> str:
    suggestions = {
        "claude": "Install Claude Code: https://docs.anthropic.com/claude/docs/claude-code",
        "codex": "Install Codex: npm install -g @openai/codex-cli",
        "gemini": "Install Gemini CLI: pip install google-generativeai-cli",
        "cursor": "Install Cursor CLI: https://cursor.sh/cli",
        "kimi": "Install Kimi CLI: pip install kimi-cli",
    }
    for key, suggestion in suggestions.items():
        if key in agent_name.lower() or key in command.lower():
            return suggestion
    return f"Make sure '{command}' is installed and in your PATH"


def _get_fix_suggestion(issue_type: str, context: dict) -> str:
    suggestions = {
        "duplicate_tmux_session": "Rename one of the slots to avoid tmux session name collision",
        "duplicate_window": f"Rename duplicate window in slot '{context.get('slot', 'unknown')}'",
        "unknown_agent": f"Add agent '{context.get('agent', 'unknown')}' to the 'agents' section in your config",
        "missing_session_id": "Run: cc-branch plan --bootstrap-if-missing",
        "missing_command": f"Install the required command: {context.get('command', 'unknown')}",
        "invalid_env_key": f"Fix environment variable name '{context.get('key', 'unknown')}' (must start with letter/underscore)",
        "missing_cwd": f"Create directory: mkdir -p {context.get('cwd', 'unknown')}",
        "missing_launch_command": "Add a 'command' or 'agent' to this window",
        "missing_tmux": tmux_install_hint(),
    }
    return suggestions.get(issue_type, "Check your configuration")


def _describe_issue(issue_type: str, context: dict) -> str:
    if issue_type == "duplicate_tmux_session":
        return f"duplicate tmux session '{context.get('session', 'unknown')}'"
    if issue_type == "duplicate_window":
        return f"duplicate window '{context.get('window', 'unknown')}'"
    if issue_type == "unknown_agent":
        return f"unknown agent '{context.get('agent', 'unknown')}'"
    if issue_type == "missing_session_id":
        return "missing session_id"
    if issue_type == "missing_command":
        return f"missing command '{context.get('command', 'unknown')}'"
    if issue_type == "invalid_env_key":
        return f"invalid env key '{context.get('key', 'unknown')}'"
    if issue_type == "missing_cwd":
        return f"missing cwd '{context.get('cwd', 'unknown')}'"
    if issue_type == "missing_launch_command":
        return "missing launch command"
    if issue_type == "missing_tmux":
        return "missing tmux"
    return issue_type.replace("_", " ")


# ---------------------------------------------------------------------------
# Structured issue builders
# ---------------------------------------------------------------------------


def _build_tmux_issue() -> Issue | None:
    tmux_path = which("tmux")
    if tmux_path:
        return Issue("tmux_ok", "info", f"tmux: ok ({tmux_path})", target="tmux")
    return Issue(
        "missing_tmux",
        "error",
        "tmux is missing",
        target="tmux",
        context={"hint": tmux_install_hint()},
    )


def _build_agent_issues(workspace: WorkspaceConfig) -> list[Issue]:
    issues: list[Issue] = []
    if not workspace.agents:
        issues.append(Issue("no_agents", "warning", "No agents declared", target="agents"))
        return issues

    for name, spec in sorted(workspace.agents.items()):
        command = spec.command or name
        command_binary = command.split()[0]
        resolved = which(command_binary)
        if resolved:
            issues.append(
                Issue("agent_ok", "info", f"{name}: ok ({command})", target=f"agent:{name}")
            )
        else:
            issues.append(
                Issue(
                    "missing_command",
                    "error",
                    f"Agent '{name}' command not found: {command}",
                    target=f"agent:{name}",
                    context={"command": command, "hint": _get_install_suggestion(name, command)},
                )
            )
    return issues


def _build_slot_issues(plan: WorkspacePlan) -> list[Issue]:
    issues: list[Issue] = []
    seen_sessions: set[str] = set()
    for slot in plan.slots:
        if slot.tmux_session in seen_sessions:
            issues.append(
                Issue(
                    "duplicate_tmux_session",
                    "error",
                    f"Duplicate tmux session '{slot.tmux_session}'",
                    target=f"slot:{slot.name}",
                    context={"session": slot.tmux_session, "slot": slot.name},
                )
            )
        else:
            seen_sessions.add(slot.tmux_session)

        duplicate_windows = _duplicate_names([w.name for w in slot.windows])
        for name in duplicate_windows:
            issues.append(
                Issue(
                    "duplicate_window",
                    "error",
                    f"Duplicate window '{name}' in slot '{slot.name}'",
                    target=f"slot:{slot.name}",
                    context={"slot": slot.name, "window": name},
                )
            )
    return issues


def _build_window_issues(plan: WorkspacePlan) -> list[Issue]:
    issues: list[Issue] = []
    # Cache repeated filesystem lookups across windows
    command_cache: dict[str, str | None] = {}
    cwd_cache: dict[str, bool] = {}

    for slot in plan.slots:
        for window in slot.windows:
            target = f"{slot.name}.{window.name}"
            ctx: dict = {"slot": slot.name, "window": window.name}

            if window.agent and not window.agent_declared:
                issues.append(
                    Issue(
                        "unknown_agent",
                        "error",
                        f"Unknown agent '{window.agent}'",
                        target=target,
                        context={**ctx, "agent": window.agent},
                    )
                )

            if (
                window.resume_mode != "none"
                and not window.resolved_session_id
                and window.create_mode == "none"
            ):
                issues.append(
                    Issue(
                        "missing_session_id",
                        "error",
                        "Window requires a session_id for resume but has none",
                        target=target,
                        context=ctx,
                        fixable=True,
                    )
                )

            if window.command_binary:
                path = command_cache.get(window.command_binary)
                if path is None and window.command_binary not in command_cache:
                    path = which(window.command_binary)
                    command_cache[window.command_binary] = path
                if path is None:
                    issues.append(
                        Issue(
                            "missing_command",
                            "error",
                            f"Command not found: {window.command_binary}",
                            target=target,
                            context={**ctx, "command": window.command_binary},
                        )
                    )

            invalid_env_keys = sorted(key for key in window.env if not _valid_env_key(key))
            for key in invalid_env_keys:
                issues.append(
                    Issue(
                        "invalid_env_key",
                        "error",
                        f"Invalid environment variable name: {key}",
                        target=target,
                        context={**ctx, "key": key},
                    )
                )

            cwd_exists = cwd_cache.get(window.cwd)
            if cwd_exists is None:
                cwd_exists = Path(window.cwd).exists()
                cwd_cache[window.cwd] = cwd_exists
            if not cwd_exists:
                issues.append(
                    Issue(
                        "missing_cwd",
                        "error",
                        f"Working directory does not exist: {window.cwd}",
                        target=target,
                        context={**ctx, "cwd": window.cwd},
                        fixable=True,
                    )
                )

            if not window.launch_command:
                issues.append(
                    Issue(
                        "missing_launch_command",
                        "error",
                        "Window has no launch command",
                        target=target,
                        context=ctx,
                    )
                )
    return issues


# ---------------------------------------------------------------------------
# Structured report builder
# ---------------------------------------------------------------------------


def build_doctor_report(workspace: WorkspaceConfig, plan: WorkspacePlan) -> str:
    """Build a human-readable doctor report."""
    issues: list[Issue] = []

    tmux_issue = _build_tmux_issue()
    if tmux_issue:
        issues.append(tmux_issue)

    issues.extend(_build_agent_issues(workspace))
    issues.extend(_build_slot_issues(plan))
    issues.extend(_build_window_issues(plan))

    report = DoctorReport(project=workspace.project, issues=issues)
    return _format_report(report)


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
        lines.append("  Run: cc-branch start --bootstrap-if-missing")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Auto-fix
# ---------------------------------------------------------------------------


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
    from .constants import DEFAULT_STATE

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
    issues = _build_agent_issues(workspace) + _build_slot_issues(plan) + _build_window_issues(plan)
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
