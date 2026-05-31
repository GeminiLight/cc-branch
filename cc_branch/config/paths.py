"""Workspace config path resolution."""

from __future__ import annotations

import re
from pathlib import Path

from ..constants import CONFIG_DIR, CONFIGS_DIR, DEFAULT_CONFIG, DEFAULT_STATE, STATES_DIR

_CONFIG_SUFFIXES = {".yaml", ".yml"}
_RESERVED_DIRECT_CONFIG_NAMES = {
    "agents.yaml",
    "agents.yml",
    "state.yaml",
    "state.yml",
}


def resolve_config_path(target_dir: Path) -> Path:
    """Return the canonical workspace config path for *target_dir*."""
    return target_dir / DEFAULT_CONFIG


def resolve_config_selection(
    target_dir: Path,
    selection: Path | str | None = None,
    *,
    restrict_to_project: bool = False,
) -> Path:
    """Resolve a user-supplied config selection to a concrete config path.

    ``selection`` may be an absolute path, project-relative path, or a short
    name such as ``review`` which maps to ``.cc-branch/configs/review.yaml``.
    """
    if selection is None or str(selection).strip() in {"", "default"}:
        config_path = resolve_config_path(target_dir)
    else:
        raw = str(selection).strip()
        selected_path = Path(raw).expanduser()
        if selected_path.is_absolute():
            config_path = selected_path
        elif _looks_like_config_path(raw):
            config_path = target_dir / selected_path
        else:
            config_path = target_dir / CONFIGS_DIR / f"{raw}.yaml"

    if restrict_to_project:
        _ensure_project_config_path(target_dir, config_path)
    return config_path


def resolve_state_path(target_dir: Path, config_path: Path | None = None) -> Path:
    """Return the canonical workspace state path for *target_dir*."""
    if config_path is None or _is_default_config_path(target_dir, config_path):
        return target_dir / DEFAULT_STATE
    state_name = f"{_safe_state_name(config_path)}.yaml"
    return target_dir / STATES_DIR / state_name


def config_options(project_dir: Path, selected_config_path: Path | None = None) -> list[dict[str, object]]:
    """Return selectable config files for *project_dir*."""
    selected = selected_config_path or resolve_config_path(project_dir)
    candidates = _config_candidates(project_dir)
    return [_config_option(project_dir, path, selected) for path in candidates]


def config_options_payload(project_dir: Path, selected_config_path: Path | None = None) -> dict[str, object]:
    """Return the Web/API payload for selectable project configs."""
    selected = selected_config_path or resolve_config_path(project_dir)
    return {
        "project_path": str(project_dir),
        "default_config_path": str(resolve_config_path(project_dir)),
        "selected_config_path": str(selected),
        "state_path": str(resolve_state_path(project_dir, selected)),
        "configs": config_options(project_dir, selected),
    }


def _looks_like_config_path(raw: str) -> bool:
    return "/" in raw or "\\" in raw or Path(raw).suffix.lower() in _CONFIG_SUFFIXES


def _is_default_config_path(project_dir: Path, config_path: Path) -> bool:
    return _normalize(config_path) == _normalize(resolve_config_path(project_dir))


def _safe_state_name(config_path: Path) -> str:
    name = config_path.stem.strip() or "config"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def _config_candidates(project_dir: Path) -> list[Path]:
    default = resolve_config_path(project_dir)
    seen = {str(_normalize(default))}
    candidates = [default]

    metadata_dir = project_dir / CONFIG_DIR
    configs_dir = project_dir / CONFIGS_DIR
    for path in sorted(configs_dir.glob("*.yml")) + sorted(configs_dir.glob("*.yaml")):
        _append_candidate(candidates, seen, path)

    for path in sorted(metadata_dir.glob("*.yml")) + sorted(metadata_dir.glob("*.yaml")):
        if path.name in _RESERVED_DIRECT_CONFIG_NAMES or path == default:
            continue
        _append_candidate(candidates, seen, path)
    return candidates


def _append_candidate(candidates: list[Path], seen: set[str], path: Path) -> None:
    key = str(_normalize(path))
    if key not in seen:
        candidates.append(path)
        seen.add(key)


def _config_option(project_dir: Path, config_path: Path, selected_config_path: Path) -> dict[str, object]:
    is_default = _is_default_config_path(project_dir, config_path)
    return {
        "id": "default" if is_default else config_path.stem,
        "label": "Default" if is_default else config_path.stem,
        "path": str(config_path),
        "state_path": str(resolve_state_path(project_dir, config_path)),
        "exists": config_path.exists(),
        "is_default": is_default,
        "selected": _normalize(config_path) == _normalize(selected_config_path),
    }


def _ensure_project_config_path(project_dir: Path, config_path: Path) -> None:
    metadata_dir = _normalize(project_dir / CONFIG_DIR)
    normalized = _normalize(config_path)
    if normalized != metadata_dir and metadata_dir not in normalized.parents:
        raise ValueError("config_path must be inside the selected project's .cc-branch directory")


def _normalize(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _project_dir_for_nested_config(config_path: Path) -> Path | None:
    if config_path.parent.name == "configs" and config_path.parent.parent.name == CONFIG_DIR:
        return config_path.parent.parent.parent
    return None


def _project_dir_for_direct_config(config_path: Path) -> Path | None:
    if config_path.parent.name == CONFIG_DIR:
        return config_path.parent.parent
    return None


def _project_dir_for_config(config_path: Path) -> Path:
    return (
        _project_dir_for_nested_config(config_path)
        or _project_dir_for_direct_config(config_path)
        or config_path.parent
    )


def project_dir_for_config(config_path: Path) -> Path:
    """Return the project root that owns *config_path*."""
    return _project_dir_for_config(config_path)
