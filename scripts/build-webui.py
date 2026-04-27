#!/usr/bin/env python3
"""Build script: copies apps/web build output into the Python package.

Usage:
    python scripts/build-webui.py

Copies apps/web/dist/* → cc_branch/webui/static/*
so that `importlib.resources` can serve the files at runtime.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def build_frontend(root: Path) -> None:
    """Run npm build in apps/web."""
    web_dir = root / "apps" / "web"
    if not (web_dir / "package.json").exists():
        raise FileNotFoundError(f"{web_dir / 'package.json'} not found")

    # Check npm is available
    try:
        subprocess.run(["npm", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        raise RuntimeError("npm is not installed or not on PATH") from e

    # Install dependencies if node_modules is missing
    if not (web_dir / "node_modules").exists():
        print("Installing npm dependencies...")
        subprocess.run(["npm", "install"], cwd=web_dir, check=True)

    print("Building frontend...")
    subprocess.run(["npm", "run", "build"], cwd=web_dir, check=True)


def sync_static_files(root: Path) -> None:
    """Copy apps/web/dist/* → cc_branch/webui/static/*."""
    dist_dir = root / "apps" / "web" / "dist"
    static_dir = root / "cc_branch" / "webui" / "static"

    if not dist_dir.exists():
        raise FileNotFoundError(
            f"{dist_dir} does not exist. Run 'npm run build' first."
        )

    # Remove old static files (keep __init__.py)
    for item in static_dir.iterdir():
        if item.name == "__init__.py":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    # Copy new files
    for item in dist_dir.iterdir():
        dest = static_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
        print(f"  copied {item.name}")

    print(f"\n✓ Static files updated in {static_dir}")


def build_webui(root: Path | None = None) -> int:
    """Build frontend and sync static files.

    Args:
        root: Project root directory. Defaults to the directory containing
            the parent of this script.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    if root is None:
        root = Path(__file__).parent.parent.resolve()

    try:
        build_frontend(root)
        sync_static_files(root)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    return build_webui()


if __name__ == "__main__":
    raise SystemExit(main())
