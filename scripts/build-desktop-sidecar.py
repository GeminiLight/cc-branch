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


def expected_binary_architecture(target: str) -> str | None:
    if target == "aarch64-apple-darwin":
        return "arm64"
    if target == "x86_64-apple-darwin":
        return "x86_64"
    if target == "x86_64-unknown-linux-gnu":
        return "x86_64"
    if target == "x86_64-pc-windows-msvc":
        return "x86_64"
    return None


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


def _mismatch_error(path: Path, target: str, expected: str, found: str) -> RuntimeError:
    return RuntimeError(
        f"Built sidecar architecture mismatch for {target}: expected {expected}, found {found}. "
        "Use a Python/PyInstaller environment that matches the release runner architecture."
    )


def elf_architecture(path: Path) -> str:
    header = path.read_bytes()[:20]
    if len(header) < 20 or header[:4] != b"\x7fELF":
        raise RuntimeError(f"Could not inspect ELF sidecar architecture for {path}")
    if header[4] != 2:
        return "non-64-bit-elf"
    byteorder = "little" if header[5] == 1 else "big"
    machine = int.from_bytes(header[18:20], byteorder)
    return {
        62: "x86_64",
        183: "arm64",
    }.get(machine, f"elf-machine-{machine}")


def pe_architecture(path: Path) -> str:
    content = path.read_bytes()
    if len(content) < 0x40 or content[:2] != b"MZ":
        raise RuntimeError(f"Could not inspect PE sidecar architecture for {path}")
    pe_offset = int.from_bytes(content[0x3C:0x40], "little")
    if pe_offset < 0 or len(content) < pe_offset + 6 or content[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise RuntimeError(f"Could not inspect PE sidecar architecture for {path}")
    machine = int.from_bytes(content[pe_offset + 4:pe_offset + 6], "little")
    return {
        0x8664: "x86_64",
        0xAA64: "arm64",
        0x14C: "x86",
    }.get(machine, f"pe-machine-0x{machine:04x}")


def validate_sidecar_architecture(path: Path, target: str) -> None:
    expected = expected_binary_architecture(target)
    if expected is None:
        return
    if "linux" in target:
        found = elf_architecture(path)
        if found != expected:
            raise _mismatch_error(path, target, expected, found)
        return
    if "windows" in target:
        found = pe_architecture(path)
        if found != expected:
            raise _mismatch_error(path, target, expected, found)
        return

    try:
        output = subprocess.check_output(["lipo", "-archs", str(path)], text=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise RuntimeError(f"Could not inspect sidecar architecture for {path}") from error

    architectures = output.split()
    if expected not in architectures:
        found = ", ".join(architectures) if architectures else "<none>"
        raise _mismatch_error(path, target, expected, found)


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
    validate_sidecar_architecture(pyinstaller_executable(), target)
    destination = copy_sidecar(target)
    validate_sidecar_architecture(destination, target)
    print(f"Built desktop sidecar: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
