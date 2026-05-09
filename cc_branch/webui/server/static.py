"""Static asset helpers for the Web UI server."""

from __future__ import annotations

import os
from importlib.resources import files
from urllib.parse import urlparse


def read_static_file(filename: str) -> str:
    """Read a text static file bundled with the package."""
    static_dir = files("cc_branch.webui.static")
    return (static_dir / filename).read_text(encoding="utf-8")


def read_static_bytes(filename: str) -> bytes:
    """Read a static file bundled with the package as bytes."""
    static_dir = files("cc_branch.webui.static")
    return (static_dir / filename).read_bytes()


def canonical_static_path(request_path: str) -> str | None:
    """Return a safe canonical path for a static file request."""
    path = urlparse(request_path).path
    if path.startswith("/static/"):
        filename = path[8:]
    elif path.startswith("/assets/"):
        filename = "assets/" + path[8:]
    elif path in {"/favicon.png", "/favicon.svg", "/apple-touch-icon.png", "/icon-512.png", "/icons.svg"}:
        filename = path[1:]
    else:
        return None

    normalized = os.path.normpath(filename)
    if normalized.startswith("..") or normalized.startswith("/") or ".." in normalized.split(os.sep):
        return None
    return normalized
