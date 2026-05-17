"""Discover reusable conversation sessions from local agent stores."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import quote, unquote, urlparse

from ..config import project_dir_for_config
from .results import ActionResult

_DEFAULT_AGENTS = ["codex", "claude", "gemini", "cursor", "kimi"]


@dataclass(frozen=True)
class AgentSessionOption:
    agent: str
    id: str
    label: str
    updated_at: str | None = None
    source: str | None = None
    project_path: str | None = None

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "id": self.id,
            "label": self.label,
            "updated_at": self.updated_at,
            "source": self.source,
            "project_path": self.project_path,
        }


def agent_session_options(
    config_path: Path,
    agent: str | None = None,
    *,
    home: Path | None = None,
    limit: int = 40,
) -> ActionResult:
    """Return known local sessions for *agent* or all supported agents."""
    project_dir = project_dir_for_config(config_path)
    sessions = agent_session_options_for_project(project_dir, agent, home=home, limit=limit)
    return ActionResult(
        ok=True,
        code="agent_sessions_loaded",
        message="Agent sessions loaded",
        payload={"sessions": [session.to_dict() for session in sessions[:limit]]},
    )


def agent_session_options_for_project(
    project_dir: Path,
    agent: str | None = None,
    *,
    home: Path | None = None,
    limit: int = 40,
) -> list[AgentSessionOption]:
    """Return known local sessions scoped to an already resolved project directory."""
    project_dir = _normalize_display_path(project_dir)
    home_dir = home or Path.home()
    requested = [_agent_key(agent)] if agent else _DEFAULT_AGENTS

    sessions: list[AgentSessionOption] = []
    for name in requested:
        if name == "codex":
            sessions.extend(_codex_sessions(home_dir, project_dir, limit=limit))
        elif name == "claude":
            sessions.extend(_claude_sessions(home_dir, project_dir, limit=limit))
        elif name == "gemini":
            sessions.extend(_gemini_sessions(home_dir, project_dir, limit=limit))
        elif name == "cursor":
            sessions.extend(_cursor_sessions(home_dir, project_dir, limit=limit))
        elif name == "kimi":
            sessions.extend(_kimi_sessions(home_dir, project_dir, limit=limit))

    sessions = _dedupe(sessions)
    sessions.sort(key=lambda item: item.updated_at or "", reverse=True)
    return sessions[:limit]


def _codex_sessions(home: Path, project_dir: Path, *, limit: int) -> list[AgentSessionOption]:
    index_by_session = _codex_session_index_lookup(home)
    projects_by_session = _codex_session_project_lookup(home)
    sessions: list[AgentSessionOption] = []
    for session_id, (session_project, transcript_path, transcript_updated_at) in projects_by_session.items():
        if not _same_path(session_project, project_dir):
            continue
        indexed = index_by_session.get(session_id, {})
        label = _clean_label(_string(indexed.get("thread_name"))) or session_id
        updated_at = _latest_iso_string(
            _string(indexed.get("updated_at")),
            transcript_updated_at,
        ) or _mtime_iso(transcript_path)
        sessions.append(
            AgentSessionOption(
                agent="codex",
                id=session_id,
                label=label,
                updated_at=updated_at,
                source=str(transcript_path),
                project_path=str(session_project),
            )
        )
    sessions.sort(key=lambda item: item.updated_at or "", reverse=True)
    return sessions[:limit]


def _codex_session_index_lookup(home: Path) -> dict[str, dict]:
    path = home / ".codex" / "session_index.jsonl"
    if not path.exists():
        return {}
    indexed: dict[str, dict] = {}
    for item in _read_jsonl(path):
        session_id = _string(item.get("id"))
        if session_id:
            indexed[session_id] = item
    return indexed


def _codex_session_project_lookup(home: Path) -> dict[str, tuple[Path, Path, str | None]]:
    sessions_dir = home / ".codex" / "sessions"
    if not sessions_dir.exists():
        return {}

    projects: dict[str, tuple[Path, Path, str | None]] = {}
    for transcript_path in sorted(sessions_dir.rglob("*.jsonl")):
        meta_id = ""
        cwd: Path | None = None
        updated_at = ""
        for item in _read_jsonl(transcript_path):
            timestamp = _string(item.get("timestamp"))
            if timestamp and timestamp > updated_at:
                updated_at = timestamp
            if item.get("type") == "session_meta":
                payload = item.get("payload")
                if not isinstance(payload, dict):
                    continue
                meta_id = _string(payload.get("id")) or meta_id
                cwd = _path_from_uri(_string(payload.get("cwd"))) or cwd
        if meta_id and cwd and meta_id not in projects:
            projects[meta_id] = (cwd, transcript_path, updated_at or None)
    return projects


def _claude_sessions(home: Path, project_dir: Path, *, limit: int) -> list[AgentSessionOption]:
    projects_dir = home / ".claude" / "projects"
    project_dirs = [
        projects_dir / _claude_project_slug(project_dir),
        projects_dir / _claude_project_slug(project_dir.resolve()),
    ]
    seen_paths: set[Path] = set()
    sessions: list[AgentSessionOption] = []
    for project_path in project_dirs:
        index_path = project_path / "sessions-index.json"
        sessions.extend(_claude_index_sessions(index_path, seen_paths, project_dir))
        if project_path.exists():
            for transcript_path in sorted(project_path.glob("*.jsonl")):
                if transcript_path in seen_paths:
                    continue
                seen_paths.add(transcript_path)
                session = _claude_transcript_session(transcript_path, project_dir)
                if session:
                    sessions.append(session)
    return sessions[-limit:]


def _claude_index_sessions(path: Path, seen_paths: set[Path], project_dir: Path) -> list[AgentSessionOption]:
    if path in seen_paths or not path.exists():
        return []
    seen_paths.add(path)
    data = _read_json(path)
    if not isinstance(data, dict):
        return []
    entries = data.get("entries")
    if not isinstance(entries, list):
        return []

    sessions: list[AgentSessionOption] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        session_id = _string(entry.get("sessionId"))
        if not session_id:
            continue
        label = (
            _clean_label(_string(entry.get("summary")))
            or _clean_label(_string(entry.get("firstPrompt")))
            or session_id
        )
        sessions.append(
            AgentSessionOption(
                agent="claude",
                id=session_id,
                label=label,
                updated_at=_string(entry.get("modified")) or _string(entry.get("created")) or None,
                source=str(path),
                project_path=str(_scoped_project_path(_string(entry.get("projectPath")), project_dir)),
            )
        )
    return sessions


def _claude_transcript_session(path: Path, project_dir: Path) -> AgentSessionOption | None:
    session_id = path.stem
    label = ""
    updated_at = ""
    project_path = ""

    for item in _read_jsonl(path):
        session_id = _string(item.get("sessionId")) or session_id
        timestamp = _string(item.get("timestamp"))
        if timestamp and timestamp > updated_at:
            updated_at = timestamp
        cwd = _string(item.get("cwd"))
        if cwd and not project_path:
            project_path = str(_scoped_project_path(cwd, project_dir))
        if item.get("type") == "summary" and not label:
            label = _clean_label(_string(item.get("summary")))

    if not session_id:
        return None
    return AgentSessionOption(
        agent="claude",
        id=session_id,
        label=label or session_id,
        updated_at=updated_at or _mtime_iso(path),
        source=str(path),
        project_path=project_path or str(project_dir),
    )


def _gemini_sessions(home: Path, project_dir: Path, *, limit: int) -> list[AgentSessionOption]:
    brain_dir = home / ".gemini" / "antigravity" / "brain"
    if not brain_dir.exists():
        return []

    by_session: dict[str, AgentSessionOption] = {}
    for metadata_path in sorted(brain_dir.glob("*/*.metadata.json")):
        data = _read_json(metadata_path)
        if not isinstance(data, dict):
            continue
        project_path = _metadata_project_path(data, project_dir)
        if not project_path or not _same_path(project_path, project_dir):
            continue
        session_id = metadata_path.parent.name
        summary = _clean_label(_string(data.get("summary"))) or session_id
        updated_at = _string(data.get("updatedAt")) or _string(data.get("updated_at")) or _mtime_iso(metadata_path)
        existing = by_session.get(session_id)
        if existing and (existing.updated_at or "") >= (updated_at or ""):
            continue
        by_session[session_id] = AgentSessionOption(
            agent="gemini",
            id=session_id,
            label=f"Antigravity: {summary}",
            updated_at=updated_at,
            source=str(metadata_path),
            project_path=str(project_path),
        )
    return list(by_session.values())[-limit:]


def _cursor_sessions(home: Path, project_dir: Path, *, limit: int) -> list[AgentSessionOption]:
    sessions: list[AgentSessionOption] = []
    for db_path in _cursor_global_state_paths(home):
        raw = _read_sqlite_item(db_path, "composer.composerHeaders")
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        entries = data.get("allComposers") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("isDraft"):
                continue
            if entry.get("unifiedMode") not in {None, "agent"}:
                continue
            session_id = _string(entry.get("composerId"))
            if not session_id:
                continue
            workspace_path = _cursor_workspace_path(entry)
            if not workspace_path or not _same_path(workspace_path, project_dir):
                continue
            label = (
                _clean_label(_string(entry.get("name")))
                or _clean_label(_string(entry.get("title")))
                or f"Cursor Agent {session_id[:8]}"
            )
            sessions.append(
                AgentSessionOption(
                    agent="cursor",
                    id=session_id,
                    label=label,
                    updated_at=_epoch_millis_iso(entry.get("lastUpdatedAt"))
                    or _epoch_millis_iso(entry.get("createdAt")),
                    source=str(db_path),
                    project_path=str(workspace_path) if workspace_path else None,
                )
            )
    return sessions[-limit:]


def _kimi_sessions(home: Path, project_dir: Path, *, limit: int) -> list[AgentSessionOption]:
    project_bucket = home / ".kimi" / "sessions" / hashlib.md5(str(project_dir).encode("utf-8")).hexdigest()
    if not project_bucket.exists():
        return []

    sessions: list[AgentSessionOption] = []
    for session_dir in sorted(path for path in project_bucket.iterdir() if path.is_dir()):
        state_path = session_dir / "state.json"
        state = _read_json(state_path)
        if isinstance(state, dict) and state.get("archived") is True:
            continue
        label = ""
        if isinstance(state, dict):
            label = (
                _clean_label(_string(state.get("custom_title")))
                or _clean_label(_string(state.get("plan_slug")))
            )
        sessions.append(
            AgentSessionOption(
                agent="kimi",
                id=session_dir.name,
                label=label or session_dir.name,
                updated_at=_latest_mtime_iso([
                    state_path,
                    session_dir / "wire.jsonl",
                    session_dir / "context.jsonl",
                ]),
                source=str(state_path) if state_path.exists() else str(session_dir),
                project_path=str(project_dir),
            )
        )
    return sessions[-limit:]


def _cursor_global_state_paths(home: Path) -> list[Path]:
    return [
        home / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb",
        home / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb",
        home / "AppData" / "Roaming" / "Cursor" / "User" / "globalStorage" / "state.vscdb",
    ]


def _cursor_workspace_path(entry: dict) -> Path | None:
    workspace = entry.get("workspaceIdentifier")
    if not isinstance(workspace, dict):
        return None
    uri = workspace.get("uri")
    if isinstance(uri, dict):
        path = _string(uri.get("fsPath")) or _string(uri.get("path")) or _string(uri.get("external"))
    else:
        path = _string(uri)
    return _path_from_uri(path)


def _metadata_project_path(data: dict, project_dir: Path) -> Path | None:
    for key in ("projectPath", "project_path", "workspacePath", "workspace_path", "cwd", "root"):
        value = _string(data.get(key))
        if value:
            return _scoped_project_path(value, project_dir)

    for key in ("project", "workspace"):
        nested = data.get(key)
        if not isinstance(nested, dict):
            continue
        for nested_key in ("path", "fsPath", "uri", "cwd", "root"):
            value = _string(nested.get(nested_key))
            if value:
                return _scoped_project_path(value, project_dir)
    return None


def _scoped_project_path(value: str, project_dir: Path) -> Path:
    path = _path_from_uri(value)
    if not path:
        return _normalize_display_path(project_dir)
    if path.is_absolute():
        return _normalize_display_path(path)
    return _normalize_display_path(project_dir / path)


def _normalize_display_path(path: Path) -> Path:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    return Path(os.path.normpath(str(expanded)))


def _path_from_uri(value: str) -> Path | None:
    if not value:
        return None
    if value.startswith("file://"):
        parsed = urlparse(value)
        return Path(unquote(parsed.path))
    return Path(value)


def _read_sqlite_item(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    try:
        db_uri = f"file:{quote(str(path), safe='/')}?mode=ro"
        with sqlite3.connect(db_uri, uri=True) as connection:
            row = connection.execute("select value from ItemTable where key = ?", (key,)).fetchone()
    except sqlite3.Error:
        return ""
    if not row:
        return ""
    return _string(row[0])


def _read_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _agent_key(value: str | None) -> str:
    normalized = re.sub(r"[\s_-]+", "", (value or "").lower())
    if "codex" in normalized:
        return "codex"
    if "claude" in normalized or "cloudcode" in normalized or "anthropic" in normalized:
        return "claude"
    if "gemini" in normalized or "antigravity" in normalized:
        return "gemini"
    if "cursor" in normalized:
        return "cursor"
    if "kimi" in normalized:
        return "kimi"
    return (value or "").lower()


def _same_path(left: Path, right: Path) -> bool:
    return _path_identity(left) == _path_identity(right)


def _path_identity(path: Path) -> str:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    return os.path.normcase(os.path.normpath(str(expanded)))


def _mtime_iso(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except OSError:
        return None


def _latest_mtime_iso(paths: Iterable[Path]) -> str | None:
    newest = 0.0
    for path in paths:
        if not path.exists():
            continue
        try:
            newest = max(newest, path.stat().st_mtime)
        except OSError:
            continue
    if not newest:
        return None
    return datetime.fromtimestamp(newest, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _latest_iso_string(*values: str | None) -> str | None:
    return max((value for value in values if value), default=None)


def _epoch_millis_iso(value: object) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    timestamp = value / 1000 if value > 10_000_000_000 else value
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _claude_project_slug(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "-", str(path))


def _read_jsonl(path: Path) -> Iterable[dict]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict):
                    yield item
    except OSError:
        return


def _string(value: object) -> str:
    return value if isinstance(value, str) else ""


def _clean_label(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:96]


def _dedupe(sessions: list[AgentSessionOption]) -> list[AgentSessionOption]:
    seen: set[tuple[str, str]] = set()
    result: list[AgentSessionOption] = []
    for session in sessions:
        key = (session.agent, session.id)
        if key in seen:
            continue
        seen.add(key)
        result.append(session)
    return result
