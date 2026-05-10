"""Discover reusable conversation sessions from local agent stores."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .results import ActionResult
from ..config import project_dir_for_config


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
    home_dir = home or Path.home()
    requested = [agent.lower()] if agent else ["codex", "claude", "gemini"]

    sessions: list[AgentSessionOption] = []
    for name in requested:
        if name == "codex":
            sessions.extend(_codex_sessions(home_dir, limit=limit))
        elif name == "claude":
            sessions.extend(_claude_sessions(home_dir, project_dir, limit=limit))
        elif name == "gemini":
            sessions.extend([])

    sessions = _dedupe(sessions)
    sessions.sort(key=lambda item: item.updated_at or "", reverse=True)
    return ActionResult(
        ok=True,
        code="agent_sessions_loaded",
        message="Agent sessions loaded",
        payload={"sessions": [session.to_dict() for session in sessions[:limit]]},
    )


def _codex_sessions(home: Path, *, limit: int) -> list[AgentSessionOption]:
    path = home / ".codex" / "session_index.jsonl"
    if not path.exists():
        return []

    sessions: list[AgentSessionOption] = []
    for item in _read_jsonl(path):
        session_id = _string(item.get("id"))
        if not session_id:
            continue
        label = _clean_label(_string(item.get("thread_name"))) or session_id
        sessions.append(
            AgentSessionOption(
                agent="codex",
                id=session_id,
                label=label,
                updated_at=_string(item.get("updated_at")) or None,
                source="~/.codex/session_index.jsonl",
            )
        )
    return sessions[-limit:]


def _claude_sessions(home: Path, project_dir: Path, *, limit: int) -> list[AgentSessionOption]:
    projects_dir = home / ".claude" / "projects"
    candidates = [
        projects_dir / _claude_project_slug(project_dir) / "sessions-index.json",
        projects_dir / _claude_project_slug(project_dir.resolve()) / "sessions-index.json",
    ]
    seen_paths: set[Path] = set()
    sessions: list[AgentSessionOption] = []
    for path in candidates:
        if path in seen_paths or not path.exists():
            continue
        seen_paths.add(path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        entries = data.get("entries")
        if not isinstance(entries, list):
            continue
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
                    project_path=_string(entry.get("projectPath")) or None,
                )
            )
    return sessions[-limit:]


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
    value = re.sub(r"<[^>]+>", "", value).strip()
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
