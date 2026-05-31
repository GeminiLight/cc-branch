"""Open local support paths in the platform file manager."""

from __future__ import annotations

import platform
import subprocess
from collections.abc import Callable
from pathlib import Path


def reveal_path(
    path: Path,
    *,
    exists: Callable[[Path], bool] | None = None,
    is_dir: Callable[[Path], bool] | None = None,
) -> None:
    """Reveal *path* in the user's file manager."""
    resolved = path.expanduser()
    exists_fn = exists or Path.exists
    is_dir_fn = is_dir or Path.is_dir
    if not exists_fn(resolved):
        raise FileNotFoundError(f"Path does not exist: {resolved}")

    system = platform.system()
    if system == "Darwin":
        if is_dir_fn(resolved):
            subprocess.Popen(["open", str(resolved)])
        else:
            subprocess.Popen(["open", "-R", str(resolved)])
        return
    if system == "Windows":
        if is_dir_fn(resolved):
            subprocess.Popen(["explorer", str(resolved)])
        else:
            subprocess.Popen(["explorer", "/select,", str(resolved)])
        return
    target = resolved if is_dir_fn(resolved) else resolved.parent
    subprocess.Popen(["xdg-open", str(target)])
