"""Custom build steps for cc-branch.

Integrates frontend build into the Python packaging pipeline so that
`pip install` or `python -m build` automatically produces an up-to-date
static bundle.

Environment variables:
    CC_BRANCH_SKIP_WEBUI_BUILD=1
        Skip the frontend build even if npm is available. Useful when
        static files are already up-to-date or when you want to install
        quickly without npm.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.sdist import sdist as _sdist


def _build_webui() -> None:
    """Build the bundled Web UI before packaging files are collected."""
    root = Path(__file__).parent.resolve()
    web_dir = root / "apps" / "web"
    static_dir = root / "cc_branch" / "webui" / "static"

    if os.environ.get("CC_BRANCH_SKIP_WEBUI_BUILD") == "1":
        # User explicitly asked to skip — respect that, but warn if
        # static files look stale or missing.
        if not (static_dir / "index.html").exists() and (
            web_dir / "package.json"
        ).exists():
            raise RuntimeError(
                "Static web UI assets are missing. "
                "Run 'python scripts/build-webui.py' first, "
                "or unset CC_BRANCH_SKIP_WEBUI_BUILD."
            )
        return

    # Only attempt frontend build when we are in a source checkout
    # (package.json exists) and npm is on PATH.
    if not (web_dir / "package.json").exists():
        return

    try:
        subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        # npm not available — this is fine for end-users installing
        # from PyPI (static files are already baked into the wheel).
        # For source installs, warn if assets look missing.
        if not (static_dir / "index.html").exists():
            raise RuntimeError(
                "npm is not installed and static web UI assets are missing.\n"
                "Either install Node.js/npm and re-run, or set "
                "CC_BRANCH_SKIP_WEBUI_BUILD=1 to skip the web UI."
            ) from None
        return

    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "build-webui.py")],
        cwd=root,
        stdout=sys.stderr,
        stderr=sys.stderr,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Frontend build failed. "
            "Run 'python scripts/build-webui.py' manually to diagnose, "
            "or set CC_BRANCH_SKIP_WEBUI_BUILD=1 to skip."
        )


class build_py(_build_py):
    """Extend build_py to auto-build the web UI before packaging."""

    def run(self) -> None:
        _build_webui()
        # Distutils build directories are incremental. Remove the copied
        # static tree first so old hashed assets cannot leak into wheels.
        stale_static = Path(self.build_lib) / "cc_branch" / "webui" / "static"
        if stale_static.exists():
            shutil.rmtree(stale_static)
        super().run()


class sdist(_sdist):
    """Ensure source distributions include current Web UI assets."""

    def run(self) -> None:
        _build_webui()
        super().run()


setup(cmdclass={"build_py": build_py, "sdist": sdist})
