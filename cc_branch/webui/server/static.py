"""Static asset helpers for the Web UI server."""

from __future__ import annotations

import os
from importlib.resources import files
from urllib.parse import urlparse

REQUIRED_STATIC_FILES = ("index.html",)


def static_assets_available() -> bool:
    """Return True when the packaged Web UI entry files are available."""
    static_dir = files("cc_branch.webui.static")
    return all((static_dir / filename).is_file() for filename in REQUIRED_STATIC_FILES)


def missing_static_assets_message() -> str:
    """Return an actionable message for installations without bundled assets."""
    return (
        "Web UI assets are missing from this installation. "
        "Official PyPI wheels include the packaged Web UI. Reinstall with "
        "`pip install --upgrade --force-reinstall cc-branch`, install the "
        "desktop app from GitHub Releases, or for source development build the "
        "Web UI in the checkout with `python scripts/build-webui.py` before "
        "running `cc-branch serve` from that checkout."
    )


def read_static_file(filename: str) -> str:
    """Read a text static file bundled with the package."""
    static_dir = files("cc_branch.webui.static")
    return (static_dir / filename).read_text(encoding="utf-8")


def read_index_html() -> str:
    """Read the Web UI entrypoint with optional app-scope bootstrap metadata."""
    html = read_static_file("index.html")
    if os.environ.get("CC_BRANCH_BACKEND_SCOPE") == "app":
        return html.replace("</head>", "<script>window.__CC_BRANCH_APP_SCOPE__=true;</script></head>", 1)
    return html


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
