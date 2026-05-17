"""Web UI server package facade."""

from __future__ import annotations

from pathlib import Path

from .handler import WebUIHandler
from .runtime import start_server
from .static import canonical_static_path as _canonical_static_path
from .static import read_static_bytes as _read_static_bytes
from .static import read_static_file as _read_static_file
from .terminal import _cli_command, _open_terminal, _slot_exists

__all__ = [
    "Path",
    "WebUIHandler",
    "start_server",
    "_canonical_static_path",
    "_read_static_bytes",
    "_read_static_file",
    "_cli_command",
    "_open_terminal",
    "_slot_exists",
]
