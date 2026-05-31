"""Native directory picker helpers for the local Web UI server."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def pick_directory(starting_dir: str | None = None) -> str | None:
    """Open a native directory picker on the server machine and return a path."""
    start = _existing_directory(starting_dir)
    if sys.platform == "darwin":
        return _pick_directory_macos(start)
    if os.name == "nt":
        return _pick_directory_windows(start)
    return _pick_directory_linux(start)


def _existing_directory(value: str | None) -> Path:
    if value:
        path = Path(value).expanduser()
        if path.is_dir():
            return path.resolve()
    return Path.cwd().resolve()


def _pick_directory_macos(starting_dir: Path) -> str | None:
    script = (
        "set startFolder to POSIX file {start}\n"
        'set pickedFolder to choose folder default location startFolder with prompt "Select project directory"\n'
        "POSIX path of pickedFolder"
    ).format(start=json.dumps(str(starting_dir)))
    try:
        result = subprocess.run(
            ["osascript", *[arg for line in script.splitlines() for arg in ("-e", line)]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("Directory picker timed out") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        if "User canceled" in detail or "(-128)" in detail:
            return None
        raise RuntimeError(detail or "Cannot open directory picker")
    picked = result.stdout.strip()
    return picked.rstrip("/") if picked else None


def _pick_directory_windows(starting_dir: Path) -> str | None:
    start = _powershell_single_quote(str(starting_dir))
    script = (
        "$shell = New-Object -ComObject Shell.Application; "
        f"$folder = $shell.BrowseForFolder(0, 'Select project directory', 0, {start}); "
        "if ($folder) { $folder.Self.Path }"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Cannot open directory picker")
    picked = result.stdout.strip()
    return picked or None


def _powershell_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _pick_directory_linux(starting_dir: Path) -> str | None:
    if executable := shutil.which("zenity"):
        return _run_linux_picker([executable, "--file-selection", "--directory", "--filename", str(starting_dir) + "/"])
    if executable := shutil.which("kdialog"):
        return _run_linux_picker([executable, "--getexistingdirectory", str(starting_dir)])
    return _pick_directory_tk(starting_dir)


def _run_linux_picker(args: list[str]) -> str | None:
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, timeout=120)
    if result.returncode != 0:
        return None
    picked = result.stdout.strip()
    return picked or None


def _pick_directory_tk(starting_dir: Path) -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as error:
        raise RuntimeError("No supported directory picker is available") from error

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        picked = filedialog.askdirectory(initialdir=str(starting_dir), title="Select project directory")
    finally:
        root.destroy()
    return picked or None
