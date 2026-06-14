"""Global project index persistence."""

from __future__ import annotations

import hashlib
import re
import secrets
import shutil
import time
from pathlib import Path
from typing import Any, Callable, cast

from ..models.config import RemoteConfig
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

    def add_project(
        self,
        path: str,
        *,
        name: str | None = None,
        display_path: str | None = None,
        remote: dict[str, object] | None = None,
        remote_preflight: dict[str, object] | None = None,
    ) -> dict[str, object]:
        normalized_path = _normalize_path(path)
        if not normalized_path:
            raise ValueError("path is required")
        normalized_remote = _normalize_remote(remote)
        normalized_display_path = str(display_path or "").strip()
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
            if normalized_display_path:
                project["display_path"] = normalized_display_path
            if normalized_remote:
                project["remote"] = normalized_remote
            if remote_preflight:
                project["remote_preflight"] = remote_preflight
            projects[existing_path_idx] = project
            data["active_project_id"] = project["id"]
        else:
            project_id = _generate_project_id(projects)
            project = {
                "id": project_id,
                "name": name or _project_name(normalized_path),
                "path": normalized_path,
            }
            if normalized_display_path:
                project["display_path"] = normalized_display_path
            if normalized_remote:
                project["remote"] = normalized_remote
            if remote_preflight:
                project["remote_preflight"] = remote_preflight
            projects.append(project)
            data["active_project_id"] = project_id

        data["projects"] = projects
        self._save(data)
        return self.payload()

    def add_remote_project(
        self,
        remote: dict[str, object],
        *,
        name: str | None = None,
        agent: str = "codex",
        remote_probe: Callable[[tuple[RemoteConfig, tuple[str, ...]]], dict] | None = None,
    ) -> dict[str, object]:
        preview = self.preview_remote_project(remote, name=name, agent=agent, remote_probe=remote_probe)
        normalized_remote = cast(dict[str, object], preview["remote"])
        preflight = cast(dict[str, object], preview["remote_preflight"])
        display_path = str(preview["display_path"])
        project_name = str(preview["name"])
        storage_path = Path(str(preview["path"]))
        selected_agent = str(preview["agent"])
        _ensure_remote_workspace(storage_path, project_name, normalized_remote, agent=selected_agent)
        selected_config_path = storage_path / ".cc-branch" / "config.yaml"
        self.add_project(
            str(storage_path),
            name=project_name,
            display_path=display_path,
            remote=normalized_remote,
            remote_preflight=preflight,
        )
        return self.set_project_config(str(storage_path), str(selected_config_path))

    def preview_remote_project(
        self,
        remote: dict[str, object],
        *,
        name: str | None = None,
        agent: str = "codex",
        remote_probe: Callable[[tuple[RemoteConfig, tuple[str, ...]]], dict] | None = None,
    ) -> dict[str, object]:
        """Preflight an SSH project without writing the local project index."""
        normalized_remote = _normalize_remote(remote)
        if not normalized_remote:
            raise ValueError("remote target is required")
        if not str(normalized_remote.get("cwd") or "").strip():
            raise ValueError("remote cwd is required")
        selected_agent = _normalize_agent(agent)
        preflight = _preflight_remote_project(normalized_remote, agent=selected_agent, remote_probe=remote_probe)
        display_path = _remote_display_path(normalized_remote)
        project_name = name or _remote_project_name(normalized_remote)
        storage_path = _remote_project_storage_path(self._path.parent, normalized_remote, project_name)
        selected_config_path = storage_path / ".cc-branch" / "config.yaml"
        return {
            "name": project_name,
            "path": str(storage_path),
            "display_path": display_path,
            "remote": normalized_remote,
            "agent": selected_agent,
            "remote_preflight": preflight,
            "selected_config_path": str(selected_config_path.resolve(strict=False)),
        }

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

    def set_project_pinned(self, project_id: str, pinned: bool) -> dict[str, object]:
        if not project_id:
            raise ValueError("id is required")
        data = self._load()
        projects = _project_list(data)
        for idx, item in enumerate(projects):
            if item.get("id") != project_id:
                continue
            next_item = dict(item)
            next_item["pinned"] = bool(pinned)
            projects[idx] = next_item
            data["projects"] = projects
            self._save(data)
            return self.payload()
        raise ValueError(f"unknown project id: {project_id}")

    def reorder_project(self, project_id: str, *, before_id: str | None = None) -> dict[str, object]:
        if not project_id:
            raise ValueError("id is required")
        data = self._load()
        projects = _project_list(data)
        source_index = next((idx for idx, item in enumerate(projects) if item.get("id") == project_id), -1)
        if source_index < 0:
            raise ValueError(f"unknown project id: {project_id}")

        moving = projects.pop(source_index)
        if before_id:
            target_index = next((idx for idx, item in enumerate(projects) if item.get("id") == before_id), -1)
            if target_index < 0:
                raise ValueError(f"unknown target project id: {before_id}")
            projects.insert(target_index, moving)
        else:
            projects.append(moving)

        data["projects"] = projects
        self._save(data)
        return self.payload()

    def inject_current_project(
        self,
        project_path: str,
        *,
        selected_config_path: str | None = None,
        activate_current: bool = False,
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
        data["active_project_id"] = (
            "current"
            if activate_current
            else _active_after_current_injection(
                projects,
                previous_active_id=previous_active_id,
                injected_path=normalized_path,
                replaced_project_id=same_path_id,
            )
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
        raw = self._load_yaml_file(self._path)
        if raw is None and self._path.exists():
            raw = self._load_yaml_file(self._backup_path())
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
        temp_path.write_text(content, encoding="utf-8")
        if self._path.exists() and self._load_yaml_file(self._path) is not None:
            shutil.copy2(self._path, self._backup_path())
        temp_path.replace(self._path)

    def _load_yaml_file(self, path: Path) -> dict[str, object] | None:
        if yaml is None:  # pragma: no cover
            raise RuntimeError("YAML support requires PyYAML to be installed")
        if not path.exists():
            return None
        try:
            raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            return None
        return raw if isinstance(raw, dict) else None

    def _backup_path(self) -> Path:
        return self._path.with_suffix(self._path.suffix + ".bak")


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
            record["pinned"] = bool(item.get("pinned"))
            display_path = str(item.get("display_path") or "").strip()
            if display_path:
                record["display_path"] = display_path
            remote = _normalize_remote(item.get("remote") if isinstance(item, dict) else None)
            if remote:
                record["remote"] = remote
            remote_preflight = item.get("remote_preflight")
            if isinstance(remote_preflight, dict):
                record["remote_preflight"] = remote_preflight
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


def _remote_project_name(remote: dict[str, object]) -> str:
    cwd_name = Path(str(remote.get("cwd") or "").rstrip("/")).name
    host = str(remote.get("host") or "").strip()
    return cwd_name or host or "remote-project"


def _normalize_path(value: object | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return str(Path(raw).expanduser().resolve(strict=False))


def _normalize_remote(value: object | None) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    host = str(value.get("host") or "").strip()
    if not host:
        return None
    remote: dict[str, object] = {"host": host}
    user = str(value.get("user") or "").strip()
    if user:
        remote["user"] = user
    raw_port = value.get("port")
    if raw_port is not None and raw_port != "":
        try:
            port = int(raw_port)
        except (TypeError, ValueError) as error:
            raise ValueError("remote port must be an integer") from error
        if port < 1 or port > 65535:
            raise ValueError("remote port must be between 1 and 65535")
        remote["port"] = port
    cwd = str(value.get("cwd") or "").strip()
    if cwd:
        remote["cwd"] = cwd
    args = value.get("args")
    if isinstance(args, list):
        cleaned_args = [str(arg) for arg in args if str(arg)]
        if cleaned_args:
            remote["args"] = cleaned_args
    options = value.get("options")
    if isinstance(options, dict):
        cleaned_options = {str(key): option for key, option in options.items() if str(key)}
        if cleaned_options:
            remote["options"] = cleaned_options
    return remote


def _remote_display_path(remote: dict[str, object]) -> str:
    user = str(remote.get("user") or "").strip()
    host = str(remote.get("host") or "").strip()
    cwd = str(remote.get("cwd") or "").strip() or "~"
    target = f"{user}@{host}" if user else host
    return f"ssh://{target}{cwd if cwd.startswith('/') else f'/{cwd}'}"


def _remote_project_storage_path(base_dir: Path, remote: dict[str, object], name: str) -> Path:
    key = "\0".join([
        str(remote.get("host") or ""),
        str(remote.get("user") or ""),
        str(remote.get("port") or ""),
        str(remote.get("cwd") or ""),
    ])
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    slug = _safe_slug(name or str(remote.get("host") or "remote"))
    return base_dir / "remote-projects" / f"{slug}-{digest}"


def _preflight_remote_project(
    remote: dict[str, object],
    *,
    agent: str = "codex",
    remote_probe: Callable[[tuple[RemoteConfig, tuple[str, ...]]], dict] | None,
) -> dict[str, object]:
    probe: Callable[[tuple[RemoteConfig, tuple[str, ...]]], dict]
    if remote_probe is None:
        from ..doctor.checks import _probe_remote

        probe = _probe_remote
    else:
        probe = remote_probe

    remote_config = RemoteConfig.from_dict(remote)
    if remote_config is None:
        raise ValueError("remote target is required")
    selected_agent = _normalize_agent(agent)
    result = probe((remote_config, (selected_agent,)))
    if result.get("error"):
        raise ValueError(f"Cannot inspect SSH target {remote_config.target()}: {result['error']}")
    if result.get("cwd") is False:
        raise ValueError(f"Remote working directory does not exist: {remote.get('cwd')}")
    if result.get("tmux") is False:
        raise ValueError(f"tmux is missing on SSH target {remote_config.target()}")
    raw_commands = result.get("commands")
    commands = cast(dict[str, object], raw_commands) if isinstance(raw_commands, dict) else {}
    missing_commands = [name for name, ok in sorted(commands.items()) if ok is False]
    if missing_commands:
        raise ValueError(f"Remote command not found on {remote_config.target()}: {', '.join(missing_commands)}")
    return {
        "cwd": result.get("cwd") is True,
        "tmux": result.get("tmux") is True,
        "agent": selected_agent,
        "commands": dict(commands),
    }


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return slug[:48] or "remote-project"


def _normalize_agent(value: str | None) -> str:
    agent = str(value or "").strip()
    return agent or "codex"


def _ensure_remote_workspace(storage_path: Path, name: str, remote: dict[str, object], *, agent: str = "codex") -> None:
    if yaml is None:  # pragma: no cover
        raise RuntimeError("YAML support requires PyYAML to be installed")
    config_path = storage_path / ".cc-branch" / "config.yaml"
    state_path = storage_path / ".cc-branch" / "state.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        remote_config = {
            key: value
            for key, value in {
                "host": remote.get("host"),
                "user": remote.get("user"),
                "port": remote.get("port"),
                "cwd": remote.get("cwd"),
                "args": remote.get("args"),
                "options": remote.get("options"),
            }.items()
            if value not in (None, "", [], {})
        }
        config = {
            "version": 2,
            "project": name,
            "root": ".",
            "tabs": [
                {
                    "name": "remote",
                    "layoutBackend": "tmux",
                    "remote": remote_config,
                    "panes": [
                        {
                            "name": "agent",
                            "agent": _normalize_agent(agent),
                        }
                    ],
                }
            ],
        }
        config_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=False), encoding="utf-8")
    if not state_path.exists():
        state_path.write_text("version: 1\nwindows: {}\n", encoding="utf-8")


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
