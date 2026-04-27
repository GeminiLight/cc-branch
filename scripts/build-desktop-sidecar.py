#!/usr/bin/env python3
"""Build the bundled desktop backend sidecar.

The Tauri bundler expects sidecar binaries to be named with the Rust target
triple suffix, for example:

    apps/desktop/src-tauri/binaries/cc-branch-backend-x86_64-unknown-linux-gnu
    apps/desktop/src-tauri/binaries/cc-branch-backend-x86_64-pc-windows-msvc.exe

This script builds a PyInstaller one-file executable for the current platform
and copies it to the expected Tauri sidecar path.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIDECAR_NAME = "cc-branch-backend"
BINARIES_DIR = ROOT / "apps" / "desktop" / "src-tauri" / "binaries"
ENTRYPOINT = ROOT / "packaging" / "desktop" / "cc_branch_backend.py"
BUILD_DIR = ROOT / "build" / "desktop-sidecar"
DIST_DIR = BUILD_DIR / "dist"
WORK_DIR = BUILD_DIR / "work"
SPEC_DIR = BUILD_DIR / "spec"


def rust_host_triple() -> str:
    output = subprocess.check_output(["rustc", "-vV"], text=True)
    for line in output.splitlines():
        if line.startswith("host: "):
            return line.split("host: ", 1)[1].strip()
    raise RuntimeError("Could not determine Rust host target triple")


def executable_suffix(target: str) -> str:
    return ".exe" if "windows" in target else ""


def pyinstaller_executable() -> Path:
    return DIST_DIR / f"{SIDECAR_NAME}{'.exe' if os.name == 'nt' else ''}"


def run_pyinstaller(target: str) -> None:
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--name",
        SIDECAR_NAME,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(WORK_DIR / target),
        "--specpath",
        str(SPEC_DIR),
        "--collect-data",
        "cc_branch",
        str(ENTRYPOINT),
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)


def copy_sidecar(target: str) -> Path:
    source = pyinstaller_executable()
    if not source.exists():
        raise FileNotFoundError(f"PyInstaller output not found: {source}")

    BINARIES_DIR.mkdir(parents=True, exist_ok=True)
    destination = BINARIES_DIR / f"{SIDECAR_NAME}-{target}{executable_suffix(target)}"
    shutil.copy2(source, destination)
    destination.chmod(destination.stat().st_mode | 0o755)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the desktop backend sidecar")
    parser.add_argument(
        "--target",
        default=None,
        help="Rust target triple. Defaults to the current rustc host triple.",
    )
    args = parser.parse_args(argv)

    target = args.target or rust_host_triple()
    run_pyinstaller(target)
    destination = copy_sidecar(target)
    print(f"Built desktop sidecar: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
