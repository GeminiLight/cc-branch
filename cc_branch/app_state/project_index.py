"""Global project index persistence."""

from __future__ import annotations

import secrets
import shutil
import time
from pathlib import Path
from typing import Any

from .paths import projects_index_path

_yaml: Any | None
try:
    import yaml as _yaml
except ModuleNotFoundError:  # pragma: no cover
    _yaml = None

yaml: Any | None = _yaml


_EMPTY_INDEX: dict[str, object] = {
    "version": 1,
    "active_project_id": None,
    "projects": [],
}


class ProjectIndexStore:
    """Load and mutate the global project index stored under ~/.cc-branch/app."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or projects_index_path()

    @property
    def path(self) -> Path:
        return self._path

    def payload(self) -> dict[str, object]:
        """Return the current index payload with storage metadata."""
        data = self._load()
        return {
            "version": _int_or_default(data.get("version"), 1),
            "active_project_id": data.get("active_project_id"),
            "projects": data.get("projects", []),
            "storage_path": str(self._path),
        }

    def add_project(self, path: str, *, name: str | None = None) -> dict[str, object]:
        normalized_path = _normalize_path(path)
        if not normalized_path:
            raise ValueError("path is required")
        data = self._load()
        projects = _project_list(data)

        existing_path_idx = next(
            (idx for idx, item in enumerate(projects) if _normalize_path(item.get("path", "")) == normalized_path),
            -1,
        )
        if existing_path_idx >= 0:
            project = dict(projects[existing_path_idx])
            project["path"] = normalized_path
            project["name"] = name or project.get("name") or _project_name(normalized_path)
            projects[existing_path_idx] = project
            data["active_project_id"] = project["id"]
        else:
            project_id = _generate_project_id(projects)
            projects.append({
                "id": project_id,
                "name": name or _project_name(normalized_path),
                "path": normalized_path,
            })
            data["active_project_id"] = project_id

        data["projects"] = projects
        self._save(data)
        return self.payload()

    def remove_project(self, project_id: str) -> dict[str, object]:
        if not project_id:
            raise ValueError("id is required")
        data = self._load()
        projects = _project_list(data)
        index = next((idx for idx, item in enumerate(projects) if item.get("id") == project_id), -1)
        if index < 0:
            return self.payload()
        projects.pop(index)
        data["projects"] = projects

        active_id = data.get("active_project_id")
        if active_id == project_id:
            replacement = projects[index - 1]["id"] if projects and index > 0 else (projects[0]["id"] if projects else None)
            data["active_project_id"] = replacement
        self._save(data)
        return self.payload()

    def activate_project(self, project_id: str) -> dict[str, object]:
        if not project_id:
            raise ValueError("id is required")
        data = self._load()
        projects = _project_list(data)
        if not any(item.get("id") == project_id for item in projects):
            raise ValueError(f"unknown project id: {project_id}")
        data["active_project_id"] = project_id
        self._save(data)
        return self.payload()

    def inject_current_project(
        self,
        project_path: str,
        *,
        selected_config_path: str | None = None,
    ) -> dict[str, object]:
        normalized_path = _normalize_path(project_path)
        if not normalized_path:
            raise ValueError("project_path is required")

        data = self._load()
        projects = _project_list(data)
        normalized_config = _normalize_path(selected_config_path) if selected_config_path else None
        previous_active_id = str(data.get("active_project_id") or "").strip()

        same_path_idx = next(
            (idx for idx, item in enumerate(projects) if _normalize_path(item.get("path", "")) == normalized_path),
            -1,
        )
        current_idx = next((idx for idx, item in enumerate(projects) if item.get("id") == "current"), -1)
        same_path_id = str(projects[same_path_idx].get("id") or "") if same_path_idx >= 0 else ""

        if same_path_idx >= 0:
            project = dict(projects[same_path_idx])
            project["id"] = "current"
            project["name"] = project.get("name") or _project_name(normalized_path)
            project["path"] = normalized_path
            if normalized_config:
                project["selected_config_path"] = normalized_config
            projects[same_path_idx] = project
            if current_idx >= 0 and current_idx != same_path_idx:
                projects.pop(current_idx)
        elif current_idx >= 0:
            project = dict(projects[current_idx])
            project["id"] = "current"
            project["name"] = project.get("name") or _project_name(normalized_path)
            project["path"] = normalized_path
            if normalized_config:
                project["selected_config_path"] = normalized_config
            projects[current_idx] = project
        else:
            project = {
                "id": "current",
                "name": _project_name(normalized_path),
                "path": normalized_path,
            }
            if normalized_config:
                project["selected_config_path"] = normalized_config
            projects.insert(0, project)

        data["projects"] = projects
        data["active_project_id"] = _active_after_current_injection(
            projects,
            previous_active_id=previous_active_id,
            injected_path=normalized_path,
            replaced_project_id=same_path_id,
        )
        self._save(data)
        return self.payload()

    def set_project_config(self, project_path: str, config_path: str) -> dict[str, object]:
        normalized_project = _normalize_path(project_path)
        normalized_config = _normalize_path(config_path)
        if not normalized_project:
            raise ValueError("project_path is required")
        if not normalized_config:
            raise ValueError("config_path is required")

        data = self._load()
        projects = _project_list(data)
        for idx, item in enumerate(projects):
            if _normalize_path(item.get("path", "")) == normalized_project:
                next_item = dict(item)
                next_item["selected_config_path"] = normalized_config
                projects[idx] = next_item
                data["projects"] = projects
                self._save(data)
                return self.payload()

        raise ValueError(f"project not found: {normalized_project}")

    def _load(self) -> dict[str, object]:
        if yaml is None:  # pragma: no cover
            raise RuntimeError("YAML support requires PyYAML to be installed")
        if not self._path.exists():
            return dict(_EMPTY_INDEX)
        try:
            raw: Any = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        except Exception:
            return dict(_EMPTY_INDEX)
        if not isinstance(raw, dict):
            return dict(_EMPTY_INDEX)
        return _normalize_data(raw)

    def _save(self, data: dict[str, object]) -> None:
        if yaml is None:  # pragma: no cover
            raise RuntimeError("YAML support requires PyYAML to be installed")
        normalized = _normalize_data(data)
        content = yaml.safe_dump(
            normalized,
            sort_keys=False,
            allow_unicode=False,
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        backup_path = self._path.with_suffix(self._path.suffix + ".bak")
        temp_path.write_text(content, encoding="utf-8")
        if self._path.exists():
            shutil.copy2(self._path, backup_path)
        temp_path.replace(self._path)


def _normalize_data(raw: dict[str, object]) -> dict[str, object]:
    projects: list[dict[str, object]] = []
    raw_projects = raw.get("projects", [])
    if isinstance(raw_projects, list):
        for item in raw_projects:
            if not isinstance(item, dict):
                continue
            project_id = str(item.get("id") or "").strip()
            project_path = _normalize_path(item.get("path"))
            if not project_id or not project_path:
                continue
            record: dict[str, object] = {
                "id": project_id,
                "name": str(item.get("name") or _project_name(project_path)),
                "path": project_path,
            }
            selected = str(item.get("selected_config_path") or "").strip()
            if selected:
                record["selected_config_path"] = _normalize_path(selected)
            projects.append(record)

    active_raw = raw.get("active_project_id")
    active_project_id = str(active_raw).strip() if active_raw is not None else None
    if active_project_id and not any(item["id"] == active_project_id for item in projects):
        active_project_id = str(projects[0]["id"]) if projects else None

    return {
        "version": _int_or_default(raw.get("version"), 1),
        "active_project_id": active_project_id,
        "projects": projects,
    }


def _project_list(data: dict[str, object]) -> list[dict[str, object]]:
    value = data.get("projects")
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    return []


def _project_name(path: str) -> str:
    return Path(path).name or "project"


def _normalize_path(value: object | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return str(Path(raw).expanduser().resolve(strict=False))


def _int_or_default(value: object | None, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, (str, bytes, bytearray, int, float)):
        return int(value)
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _generate_project_id(projects: list[dict[str, object]]) -> str:
    existing = {str(item.get("id") or "") for item in projects}
    for _attempt in range(16):
        candidate = f"proj_{int(time.time() * 1000):x}_{secrets.token_hex(2)}"
        if candidate not in existing and candidate != "current":
            return candidate
    raise RuntimeError("could not allocate a unique project id")


def _active_after_current_injection(
    projects: list[dict[str, object]],
    *,
    previous_active_id: str,
    injected_path: str,
    replaced_project_id: str,
) -> str | None:
    """Preserve the user's selected project when merely ensuring current exists."""
    if not projects:
        return None
    if not previous_active_id:
        return "current"
    if previous_active_id == "current" or previous_active_id == replaced_project_id:
        return "current"

    for project in projects:
        if project.get("id") == previous_active_id:
            if _normalize_path(project.get("path")) == injected_path:
                return "current"
            return previous_active_id
    return "current"
