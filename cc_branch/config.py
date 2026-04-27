"""Workspace configuration loading and initialization.

Public API operates on typed :class:`cc_branch.models.WorkspaceConfig`.
"""

from __future__ import annotations

from pathlib import Path

from .constants import DEFAULT_CONFIG, DEFAULT_STATE, LEGACY_CONFIGS
from .models import WorkspaceConfig, WorkspaceState
from .planner import plan_workspace
from .shells import default_shell_command
from .state import merge_state, save_state

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        tomllib = None  # type: ignore

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


def resolve_config_path(target_dir: Path) -> Path:
    """Return the path to the workspace config file.

    Prefers ``.cc-branch.yaml``, but falls back to legacy names.
    """
    preferred = target_dir / DEFAULT_CONFIG
    if preferred.exists():
        return preferred
    for legacy_name in LEGACY_CONFIGS:
        legacy_path = target_dir / legacy_name
        if legacy_path.exists():
            return legacy_path
    return preferred


def _load_config_data(path: Path) -> dict:
    """Parse a YAML or TOML config file into a raw dict."""
    suffix = path.suffix.lower()
    if suffix == ".toml":
        if tomllib is None:  # pragma: no cover
            raise RuntimeError(
                "TOML support on Python 3.10 requires the 'tomli' package"
            )
        with path.open("rb") as handle:
            return tomllib.load(handle)
    if suffix in {".yaml", ".yml"}:
        if yaml is None:  # pragma: no cover
            raise RuntimeError("YAML support requires PyYAML to be installed")
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise TypeError("workspace config must deserialize to a mapping")
        return data
    raise ValueError(f"unsupported config format: {path.suffix}")


def _normalize_raw_config(data: dict, path: Path) -> dict:
    """Apply defaults and resolve paths on a raw config dict."""
    data.setdefault("version", 1)
    data.setdefault("project", path.parent.name)
    data.setdefault("display", {})
    data.setdefault("agents", {})
    data.setdefault("slots", [])
    data["display"].setdefault("mode", "grid")
    data["display"].setdefault("columns", 2)
    data["display"].setdefault("dashboard", False)

    root_value = data.get("root", ".")
    root_path = (path.parent / root_value).resolve()
    data["root"] = str(root_path)
    data["_config_path"] = str(path.resolve())
    return data


def load_workspace(path: Path) -> WorkspaceConfig:
    """Load workspace configuration.

    Internally the config is validated through ``WorkspaceConfig`` so that
    unknown fields or type mismatches are caught early.
    """
    raw = _load_config_data(path)
    normalized = _normalize_raw_config(raw, path)
    return WorkspaceConfig.from_dict(normalized)


def init_workspace(target_dir: Path, force: bool, bootstrap_sessions: bool) -> tuple[Path, Path]:
    """Create starter workspace config and state files."""
    config_path = resolve_config_path(target_dir)
    state_path = target_dir / DEFAULT_STATE
    shell_command = default_shell_command()

    if config_path.exists() and not force:
        raise FileExistsError(f"{config_path} already exists (use --force to overwrite)")

    config_path = target_dir / DEFAULT_CONFIG
    project = target_dir.name
    config_body = f"""version: 1
project: "{project}"
root: "."

display:
  mode: "grid"
  columns: 2
  dashboard: true

agents:
  codex:
    command: "codex"
    resume_mode: "flag"
    resume_template: "resume {{session_id}}"
    label_template: "{{project}}/{{slot}}/{{window}}"

  claude:
    command: "claude"
    create_mode: "generated_uuid"
    create_template: "claude --session-id {{session_id}}"
    resume_mode: "flag"
    resume_template: "-r {{session_id}}"
    label_template: "{{project}}/{{slot}}/{{window}}"

slots:
  - name: "dev"
    backend: "tmux"
    cwd: "."
    windows:
      - name: "planner"
        agent: "codex"
      - name: "review"
        agent: "claude"

  - name: "scratch"
    backend: "shell"
    cwd: "."
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
