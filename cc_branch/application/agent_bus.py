"""Local Agent Bus event storage."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..app_state.paths import app_data_dir

Clock = Callable[[], str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class AgentBusStore:
    """Append-only local event log for agent messages and inbox state."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_data_dir() / "agent-bus.jsonl"

    def record_message_sent(
        self,
        *,
        target: str,
        message: str,
        sender: str = "user",
        delivery: str,
        status: str = "sent",
        now: Clock = _utc_now,
    ) -> dict[str, object]:
        event = {
            "id": uuid.uuid4().hex,
            "timestamp": now(),
            "type": "message.sent",
            "sender": sender,
            "target": target,
            "message": message,
            "delivery": delivery,
            "status": status,
            "read": False,
        }
        self.append(event)
        return event

    def mark_read(
        self,
        *,
        target: str | None = None,
        event_id: str | None = None,
        reader: str = "user",
        now: Clock = _utc_now,
    ) -> dict[str, object]:
        unread = self.inbox(target=target, unread_only=True)
        if event_id is not None:
            unread = [event for event in unread if event.get("id") == event_id]
        read_ids = [str(event.get("id")) for event in unread if event.get("id")]
        event = {
            "id": uuid.uuid4().hex,
            "timestamp": now(),
            "type": "message.read",
            "reader": reader,
            "target": target,
            "event_ids": read_ids,
            "count": len(read_ids),
        }
        self.append(event)
        return event

    def append(self, event: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")

    def events(self, *, target: str | None = None, limit: int | None = None) -> list[dict[str, object]]:
        events = [event for event in self._read_events() if target is None or event.get("target") == target]
        if limit is not None:
            return events[-limit:]
        return events

    def inbox(self, *, target: str | None = None, unread_only: bool = False, limit: int | None = None) -> list[dict[str, object]]:
        read_ids = self._read_message_ids(target=target)
        events = [
            event
            for event in self.events(target=target)
            if event.get("type") == "message.sent"
            and (not unread_only or str(event.get("id") or "") not in read_ids)
        ]
        if limit is not None:
            return events[-limit:]
        return events

    def _read_message_ids(self, *, target: str | None = None) -> set[str]:
        read_ids: set[str] = set()
        for event in self.events(target=target):
            if event.get("type") != "message.read":
                continue
            for event_id in event.get("event_ids") or []:
                if event_id:
                    read_ids.add(str(event_id))
        return read_ids

    def _read_events(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        events: list[dict[str, object]] = []
        for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                events.append(parsed)
        return events
