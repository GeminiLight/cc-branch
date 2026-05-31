"""Shared platform helpers for opener implementations."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .types import OpenerError


def _find_macos_app(app_name: str) -> Path | None:
    candidates = [
        Path("/Applications") / f"{app_name}.app",
        Path.home() / "Applications" / f"{app_name}.app",
        Path("/System/Applications") / f"{app_name}.app",
        Path("/System/Applications/Utilities") / f"{app_name}.app",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _open_uri(uri: str) -> None:
    if sys.platform == "darwin":
        _popen(["open", uri])
        return
    if os.name == "nt":
        _popen(["cmd", "/c", "start", "", uri])
        return
    executable = shutil.which("xdg-open")
    if not executable:
        raise OpenerError("Cannot open URI: xdg-open is not available")
    _popen([executable, uri])


def _open_path(path: Path) -> None:
    resolved = path.expanduser().resolve()
    if sys.platform == "darwin":
        executable = shutil.which("open")
        if not executable:
            raise OpenerError("Cannot open folder: open is not available")
        _popen([executable, str(resolved)])
        return
    if os.name == "nt":
        _popen(["explorer", str(resolved)])
        return
    executable = shutil.which("xdg-open")
    if not executable:
        raise OpenerError("Cannot open folder: xdg-open is not available")
    _popen([executable, str(resolved)])


def _cache_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "cc-branch"
    if os.name == "nt":
        windows_root = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(windows_root) / "cc-branch"
    linux_root = os.environ.get("XDG_CACHE_HOME")
    if linux_root:
        return Path(linux_root) / "cc-branch"
    return Path.home() / ".cache" / "cc-branch"


def _warp_launch_config_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / ".warp" / "launch_configurations"
    if os.name == "nt":
        windows_root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(windows_root) / "warp" / "Warp" / "data" / "launch_configurations"
    linux_root = os.environ.get("XDG_DATA_HOME")
    if linux_root:
        return Path(linux_root) / "warp-terminal" / "launch_configurations"
    return Path.home() / ".local" / "share" / "warp-terminal" / "launch_configurations"


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-").lower()
    return slug or "workspace"


def _yaml_string(value: str) -> str:
    return json.dumps(value)


def _popen(args: list[str]) -> None:
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
