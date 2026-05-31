"""Executable lookup helpers shared by CLI, Web UI, and desktop sidecars."""

from __future__ import annotations

import os
import shutil


_PLATFORM_EXECUTABLE_DIRS = (
    "/opt/homebrew/bin",
    "/opt/homebrew/sbin",
    "/usr/local/bin",
    "/usr/local/sbin",
    "/opt/local/bin",
    "/opt/local/sbin",
    "/usr/bin",
    "/bin",
    "/usr/sbin",
    "/sbin",
)


def _executable_search_path() -> str | None:
    """Return PATH plus common GUI-app-missing install directories."""
    values: list[str] = []
    seen: set[str] = set()
    for value in os.environ.get("PATH", "").split(os.pathsep):
        if value and value not in seen:
            values.append(value)
            seen.add(value)
    for value in _PLATFORM_EXECUTABLE_DIRS:
        if value and value not in seen:
            values.append(value)
            seen.add(value)
    return os.pathsep.join(values) if values else None


def which(name: str) -> str | None:
    """Return the path to executable *name* or None."""
    return shutil.which(name, path=_executable_search_path())
