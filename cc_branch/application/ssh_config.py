"""SSH config discovery for UI target pickers."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SSHHost:
    alias: str
    hostname: str | None = None
    user: str | None = None
    port: int | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"alias": self.alias}
        if self.hostname:
            payload["hostname"] = self.hostname
        if self.user:
            payload["user"] = self.user
        if self.port is not None:
            payload["port"] = self.port
        return payload


def discover_ssh_hosts(config_path: Path | None = None, *, home: Path | None = None) -> list[dict[str, object]]:
    """Return user-facing SSH host aliases from OpenSSH config files.

    The UI needs friendly choices, not a full OpenSSH evaluator. We read
    explicit ``Host`` entries, follow simple ``Include`` directives, and skip
    wildcard/negated patterns that are not concrete connection targets.
    """

    root = config_path or ((home or Path.home()) / ".ssh" / "config")
    hosts = _parse_ssh_config(root, seen=set(), depth=0)
    return [host.to_dict() for host in hosts]


def _parse_ssh_config(path: Path, *, seen: set[Path], depth: int) -> list[SSHHost]:
    if depth > 4:
        return []
    try:
        resolved = path.expanduser().resolve(strict=False)
    except OSError:
        resolved = path.expanduser()
    if resolved in seen or not resolved.exists() or not resolved.is_file():
        return []
    seen.add(resolved)

    hosts: list[SSHHost] = []
    by_alias: dict[str, int] = {}
    current_aliases: list[str] = []
    current_values: dict[str, str] = {}

    def flush_current() -> None:
        nonlocal current_aliases, current_values
        for alias in current_aliases:
            if alias in by_alias:
                index = by_alias[alias]
                existing = hosts[index]
                hosts[index] = SSHHost(
                    alias=existing.alias,
                    hostname=existing.hostname or current_values.get("hostname"),
                    user=existing.user or current_values.get("user"),
                    port=existing.port if existing.port is not None else _parse_port(current_values.get("port")),
                )
                continue
            by_alias[alias] = len(hosts)
            hosts.append(
                SSHHost(
                    alias=alias,
                    hostname=current_values.get("hostname"),
                    user=current_values.get("user"),
                    port=_parse_port(current_values.get("port")),
                )
            )
        current_aliases = []
        current_values = {}

    try:
        lines = resolved.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    except UnicodeDecodeError:
        try:
            lines = resolved.read_text().splitlines()
        except OSError:
            return []

    for raw_line in lines:
        parts = _split_config_line(raw_line)
        if not parts:
            continue
        key = parts[0].lower()
        values = parts[1:]
        if key == "host":
            flush_current()
            current_aliases = [value for value in values if _is_concrete_alias(value)]
            current_values = {}
            continue
        if key == "include":
            include_hosts: list[SSHHost] = []
            for value in values:
                include_hosts.extend(_parse_include(value, base_dir=resolved.parent, seen=seen, depth=depth + 1))
            for host in include_hosts:
                if host.alias in by_alias:
                    continue
                by_alias[host.alias] = len(hosts)
                hosts.append(host)
            continue
        if current_aliases and key in {"hostname", "user", "port"} and values:
            current_values.setdefault(key, values[0])

    flush_current()
    return hosts


def _split_config_line(line: str) -> list[str]:
    try:
        return shlex.split(line, comments=True, posix=True)
    except ValueError:
        return []


def _is_concrete_alias(value: str) -> bool:
    return bool(value) and not value.startswith("!") and not any(char in value for char in "*?")


def _parse_port(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        port = int(value)
    except ValueError:
        return None
    return port if 1 <= port <= 65535 else None


def _parse_include(value: str, *, base_dir: Path, seen: set[Path], depth: int) -> list[SSHHost]:
    include_path = Path(value).expanduser()
    if not include_path.is_absolute():
        include_path = base_dir / include_path

    matches = sorted(include_path.parent.glob(include_path.name)) if any(char in str(include_path) for char in "*?[]") else [include_path]
    hosts: list[SSHHost] = []
    for match in matches:
        hosts.extend(_parse_ssh_config(match, seen=seen, depth=depth))
    return hosts
