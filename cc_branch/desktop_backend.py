"""Desktop backend entry point for the bundled Tauri sidecar.

This module intentionally starts only the local Web UI API server. It avoids
the full CLI command parser so a PyInstaller-built sidecar can be a small,
predictable backend process for the desktop application.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .webui.server import start_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the CC Branch desktop backend")
    parser.add_argument("--host", default="127.0.0.1", help="host to bind to")
    parser.add_argument("--port", type=int, required=True, help="port to listen on")
    parser.add_argument("--config", required=True, help="path to .cc-branch.yaml")
    parser.add_argument("--state", required=True, help="path to .cc-branch.state.yaml")
    parser.add_argument(
        "--token",
        default=os.environ.get("CC_BRANCH_WEB_TOKEN"),
        help="optional bearer token for API access",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    start_server(
        Path(args.config),
        Path(args.state),
        host=args.host,
        port=args.port,
        token=args.token,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
