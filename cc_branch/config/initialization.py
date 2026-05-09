"""Default workspace config creation."""

from __future__ import annotations

from pathlib import Path

from ..constants import DEFAULT_CONFIG, DEFAULT_STATE
from ..models import WorkspaceState
from ..planner import plan_workspace
from ..runtime.shells import default_shell_command
from ..state import merge_state, save_state
from .loading import load_workspace
from .paths import resolve_config_path
from .paths import resolve_state_path


def init_workspace(target_dir: Path, force: bool, bootstrap_sessions: bool) -> tuple[Path, Path]:
    """Create starter workspace config and state files."""
    config_path = resolve_config_path(target_dir)
    state_path = resolve_state_path(target_dir, config_path)
    shell_command = default_shell_command()

    if config_path.exists() and not force:
        raise FileExistsError(f"{config_path} already exists (use --force to overwrite)")

    config_path = target_dir / DEFAULT_CONFIG
    state_path = target_dir / DEFAULT_STATE
    config_path.parent.mkdir(parents=True, exist_ok=True)
    project = target_dir.name
    config_body = f"""version: 1
project: "{project}"
root: "."

display:
  mode: "grid"
  columns: 2
  dashboard: true

slots:
  - name: "dev"
    runtime: "tmux"
    cwd: "."
    windows:
      - name: "planner"
        agent: "codex"
      - name: "review"
        agent: "claude"

  - name: "scratch"
    runtime: "terminal"
    cwd: "."
    title: "scratch"
    command: "{shell_command}"
"""
    config_path.write_text(config_body, encoding="utf-8")

    state = WorkspaceState()
    if bootstrap_sessions:
        workspace = load_workspace(config_path)
        plan = plan_workspace(workspace, state, bootstrap_missing=True)
        state = merge_state(state, plan.state_updates)
    save_state(state_path, state)
    return config_path, state_path
