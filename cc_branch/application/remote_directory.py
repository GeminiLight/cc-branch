"""Remote directory browsing helpers for SSH-backed projects."""

from __future__ import annotations

import posixpath
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RemoteTarget:
    host: str
    user: str | None = None
    port: int | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RemoteTarget":
        host = str(value.get("host") or "").strip()
        if not host:
            raise ValueError("remote host is required")
        user = str(value.get("user") or "").strip() or None
        raw_port = value.get("port")
        port: int | None = None
        if raw_port not in (None, ""):
            try:
                port = int(str(raw_port))
            except (TypeError, ValueError) as error:
                raise ValueError("remote port must be an integer") from error
            if port < 1 or port > 65535:
                raise ValueError("remote port must be between 1 and 65535")
        return cls(host=host, user=user, port=port)

    def ssh_command(self, remote_command: str) -> list[str]:
        target = f"{self.user}@{self.host}" if self.user else self.host
        command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8"]
        if self.port is not None:
            command.extend(["-p", str(self.port)])
        command.extend([target, remote_command])
        return command


def list_remote_directories(
    remote: dict[str, Any],
    path: str | None = None,
    *,
    timeout: int = 12,
    max_entries: int = 300,
) -> dict[str, object]:
    target = RemoteTarget.from_dict(remote)
    requested_path = str(path or ".").strip() or "."
    if max_entries < 1:
        raise ValueError("max_entries must be positive")
    remote_entry_limit = max_entries + 1
    remote_command = (
        f"cd {shlex.quote(requested_path)} && "
        "pwd -P && "
        f"find . -maxdepth 1 -mindepth 1 -type d -print | sed -n '1,{remote_entry_limit}p'"
    )
    result = subprocess.run(
        target.ssh_command(remote_command),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "Cannot list remote directory"
        raise RuntimeError(detail)

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    current_path = _normalize_remote_path(lines[0] if lines else requested_path)
    raw_entries = lines[1:]
    truncated = len(raw_entries) > max_entries
    entries: list[dict[str, object]] = []
    for line in raw_entries[:max_entries]:
        entry = _entry_from_find_line(current_path, line)
        if entry is not None:
            entries.append(entry)
    entries.sort(key=lambda entry: (bool(entry["hidden"]), str(entry["name"]).casefold()))
    return {
        "path": current_path,
        "parent": _parent_path(current_path),
        "entries": entries,
        "truncated": truncated,
    }


def _normalize_remote_path(value: str) -> str:
    normalized = posixpath.normpath(value.strip() or ".")
    if value.startswith("/") and not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized


def _entry_from_find_line(base_path: str, value: str) -> dict[str, object] | None:
    name = value[2:] if value.startswith("./") else value
    name = name.strip().rstrip("/")
    if not name or name == ".":
        return None
    path = posixpath.normpath(posixpath.join(base_path, name))
    return {
        "name": name,
        "path": path,
        "hidden": name.startswith("."),
    }


def _parent_path(path: str) -> str | None:
    if path in {"", "/", "."}:
        return None
    parent = posixpath.dirname(path.rstrip("/")) or "/"
    return parent if parent != path else None
