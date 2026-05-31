from __future__ import annotations

import shlex

from ..models.config import RemoteConfig


def effective_remote(
    slot_remote: RemoteConfig | None,
    window_remote: RemoteConfig | None,
) -> RemoteConfig | None:
    """Return the inherited remote target for a window."""
    if slot_remote is None and window_remote is None:
        return None
    if window_remote is not None and not window_remote.enabled:
        return None
    if slot_remote is not None and not slot_remote.enabled:
        slot_remote = None
    if slot_remote is None:
        return window_remote if window_remote and window_remote.host else None
    if window_remote is None:
        return slot_remote if slot_remote.host else None
    merged = RemoteConfig(
        host=window_remote.host or slot_remote.host,
        user=window_remote.user if window_remote.user is not None else slot_remote.user,
        port=window_remote.port if window_remote.port is not None else slot_remote.port,
        cwd=window_remote.cwd if window_remote.cwd is not None else slot_remote.cwd,
        args=window_remote.args or slot_remote.args,
        options={**slot_remote.options, **window_remote.options},
    )
    return merged if merged.host else None


def render_ssh_command(remote: RemoteConfig, command: str) -> str:
    """Wrap a resolved launch command so it executes on the configured remote."""
    if not command:
        return command

    ssh_args = ["ssh"]
    if remote.port is not None:
        ssh_args.extend(["-p", str(remote.port)])
    for key, value in sorted(remote.options.items()):
        option = str(key) if value is None else f"{key}={value}"
        ssh_args.extend(["-o", option])
    ssh_args.extend(remote.args)
    ssh_args.append(remote.target())

    remote_command = command
    if remote.cwd:
        remote_command = f"cd {shlex.quote(remote.cwd)} && {command}"

    return " ".join(shlex.quote(part) for part in [*ssh_args, remote_command])
