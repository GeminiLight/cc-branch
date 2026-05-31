"""Server runtime startup for the Web UI."""

from __future__ import annotations

from functools import partial
from http.server import HTTPServer
from pathlib import Path

from .handler import WebUIHandler


def start_server(
    config_path: Path,
    state_path: Path,
    host: str = "127.0.0.1",
    port: int = 8080,
    token: str | None = None,
) -> None:
    """Start the web UI server."""
    handler = partial(WebUIHandler, config_path, state_path, token=token)
    server = HTTPServer((host, port), handler)
    print(f"Starting cc-branch Web UI at http://{host}:{port}")
    if token:
        print("Authentication enabled (token required for Web UI and API access)")
        print(f"Open once with: http://{host}:{port}/?token={token}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.shutdown()
