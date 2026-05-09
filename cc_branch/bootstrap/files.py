"""Workspace file creation for first-run bootstrap."""

from __future__ import annotations

from pathlib import Path

from ..config import load_workspace
from ..constants import DEFAULT_CONFIG, DEFAULT_STATE, STATES_DIR
from ..models import WorkspaceState
from ..state import save_state
from .generation import generate_starter_config, summarize_config
from .models import WorkspaceInitResult
from .sessions import bootstrap_sessions


def ensure_state_gitignored(target_dir: Path, state_filename: str) -> tuple[bool, bool]:
    """Ensure the local state file is ignored without clobbering existing edits."""
    gitignore_path = target_dir / ".gitignore"
    state_entries = [state_filename, f"{STATES_DIR}/"]
    block = "# CC Branch state (machine-specific)\n" + "\n".join(state_entries) + "\n"

    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        missing_entries = [entry for entry in state_entries if entry not in content.splitlines()]
        if not missing_entries:
            return False, False
        with gitignore_path.open("a", encoding="utf-8") as handle:
            prefix = "" if content.endswith("\n") or not content else "\n"
            handle.write(f"{prefix}# CC Branch state (machine-specific)\n")
            handle.write("\n".join(missing_entries) + "\n")
        return False, True

    gitignore_path.write_text(block, encoding="utf-8")
    return True, False


def initialize_workspace_files(
    target_dir: Path,
    *,
    profile: str,
    available_agents: list[str],
    bootstrap_sessions_requested: bool,
    tmux_available: bool = True,
) -> WorkspaceInitResult:
    """Create config, state, and gitignore entries for a new workspace."""
    config_content = generate_starter_config(
        target_dir.name,
        available_agents,
        profile,
        tmux_available=tmux_available,
    )
    config_path = target_dir / DEFAULT_CONFIG
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config_content, encoding="utf-8")

    summary = summarize_config(config_content)
    workspace = load_workspace(config_path)
    state = WorkspaceState()

    if bootstrap_sessions_requested or available_agents:
        state = bootstrap_sessions(workspace, state)

    state_path = target_dir / DEFAULT_STATE
    state_path.parent.mkdir(parents=True, exist_ok=True)
    save_state(state_path, state)
    gitignore_created, gitignore_updated = ensure_state_gitignored(target_dir, DEFAULT_STATE)

    return WorkspaceInitResult(
        config_path=config_path,
        state_path=state_path,
        config_summary=summary,
        state=state,
        gitignore_created=gitignore_created,
        gitignore_updated=gitignore_updated,
    )
