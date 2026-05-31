#!/usr/bin/env python3
"""Verify a macOS DMG contains the packaged app and backend sidecar."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import plistlib
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def find_app_bundle(mountpoint: Path, expected_app_name: str) -> Path:
    expected = mountpoint / expected_app_name
    apps = sorted(mountpoint.glob("*.app"))
    if not expected.exists():
        found = ", ".join(app.name for app in apps) or "<none>"
        raise FileNotFoundError(
            f"Could not find {expected_app_name} in mounted DMG; found: {found}"
        )
    unexpected_apps = [app for app in apps if app.name != expected_app_name]
    if unexpected_apps:
        names = ", ".join(app.name for app in unexpected_apps)
        raise ValueError(f"Mounted DMG contains unexpected app bundle(s): {names}")
    return expected


def verify_applications_shortcut(mountpoint: Path) -> dict:
    shortcut = mountpoint / "Applications"
    if not shortcut.exists() and not shortcut.is_symlink():
        raise FileNotFoundError(
            "Mounted DMG is missing the Applications drag-install shortcut"
        )
    if not shortcut.is_symlink():
        raise ValueError("Mounted DMG Applications shortcut is not a symlink")
    target = os.readlink(shortcut)
    if target != "/Applications":
        raise ValueError(
            f"Mounted DMG Applications shortcut points to {target!r}, expected '/Applications'"
        )
    return {"applications_shortcut": target}


def read_bundle_version(app_path: Path) -> str | None:
    info_plist = app_path / "Contents" / "Info.plist"
    if not info_plist.exists() or info_plist.stat().st_size <= 0:
        return None
    with info_plist.open("rb") as file:
        info = plistlib.load(file)
    if not isinstance(info, dict):
        return None
    version = info.get("CFBundleShortVersionString")
    return version if isinstance(version, str) and version else None


def require_asset_name_version(asset: Path, expected_version: str | None, *, label: str) -> None:
    if expected_version is not None and re.search(rf"(?<!\d){re.escape(expected_version)}(?!\d)", asset.name) is None:
        raise ValueError(
            f"{label} asset {asset.name!r} does not match expected {expected_version!r}"
        )


def verify_app_bundle_contains_backend(
    app_path: Path,
    *,
    expected_version: str | None = None,
) -> dict:
    macos_dir = app_path / "Contents" / "MacOS"
    main_binary = macos_dir / "cc-branch"
    backend = macos_dir / "cc-branch-backend"
    if not main_binary.exists() or main_binary.stat().st_size <= 0:
        raise FileNotFoundError(f"Missing packaged app executable: {main_binary}")
    if not os.access(main_binary, os.X_OK):
        raise PermissionError(f"Packaged app executable is not executable: {main_binary}")
    if not backend.exists() or backend.stat().st_size <= 0:
        raise FileNotFoundError(f"Missing bundled backend sidecar: {backend}")
    if not os.access(backend, os.X_OK):
        raise PermissionError(f"Bundled backend sidecar is not executable: {backend}")
    bundle_version = read_bundle_version(app_path)
    if expected_version is not None:
        if bundle_version is None:
            raise ValueError("Packaged app is missing bundle version in Info.plist")
        if bundle_version != expected_version:
            raise ValueError(
                f"Packaged app bundle version {bundle_version!r} "
                f"does not match expected {expected_version!r}"
            )
    return {
        "app_path": str(app_path),
        "app_binary_path": str(main_binary),
        "main_binary_size": main_binary.stat().st_size,
        "backend_path": str(backend),
        "backend_size": backend.stat().st_size,
        "bundle_version": bundle_version,
    }


def dmg_expected_arch(dmg_path: Path) -> str | None:
    name = dmg_path.name.lower()
    if "aarch64" in name or "arm64" in name:
        return "aarch64"
    if "x64" in name or "x86_64" in name:
        return "x86_64"
    return None


def verify_app_launches_backend(
    app_path: Path,
    *,
    timeout: float,
    expected_version: str | None = None,
    expected_platform: str | None = None,
    expected_arch: str | None = None,
    use_auto_port: bool = True,
) -> dict:
    script_path = Path(__file__).with_name("smoke-test-desktop-app.py")
    spec = importlib.util.spec_from_file_location("smoke_test_desktop_app", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    executable = module.app_executable_from_bundle(app_path)
    return module.verify_desktop_app(
        executable,
        timeout=timeout,
        expected_version=expected_version,
        expected_platform=expected_platform,
        expected_arch=expected_arch,
        use_auto_port=use_auto_port,
    )


def copy_app_bundle_for_install_verification(app_path: Path, install_root: Path) -> Path:
    applications_dir = install_root / "Applications"
    applications_dir.mkdir(parents=True, exist_ok=False)
    installed_app = applications_dir / app_path.name
    shutil.copytree(app_path, installed_app, symlinks=True)
    return installed_app


def verify_installed_copy_launches_backend(
    app_path: Path,
    *,
    install_root: Path,
    expected_version: str | None = None,
    expected_platform: str | None = None,
    expected_arch: str | None = None,
    timeout: float,
) -> dict:
    installed_app = copy_app_bundle_for_install_verification(app_path, install_root)
    content = verify_app_bundle_contains_backend(
        installed_app,
        expected_version=expected_version,
    )
    launch = require_bundled_backend_launch(
        verify_app_launches_backend(
            installed_app,
            timeout=timeout,
            expected_version=expected_version,
            expected_platform=expected_platform,
            expected_arch=expected_arch,
            use_auto_port=True,
        )
    )
    return {
        "app_path": str(installed_app),
        "content": content,
        "launch": launch,
    }


def verify_app_rejects_stale_backend(app_path: Path, *, timeout: float) -> dict:
    script_path = Path(__file__).with_name("smoke-test-desktop-app.py")
    spec = importlib.util.spec_from_file_location("smoke_test_desktop_app", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    executable = module.app_executable_from_bundle(app_path)
    sidecar = module.sidecar_executable_from_app_executable(executable)
    return module.verify_desktop_rejects_stale_backend(
        executable,
        sidecar_executable=sidecar,
        timeout=timeout,
    )


def require_bundled_backend_launch(launch: dict) -> dict:
    if launch.get("ok") is not True:
        raise ValueError("DMG launch verification did not pass")
    source = launch.get("backend_source")
    if source != "bundled-sidecar":
        raise ValueError(
            f"DMG launch used backend_source={source!r}, expected 'bundled-sidecar'"
        )
    return launch


def require_stale_backend_rejection(result: dict) -> dict:
    if result.get("ok") is not True:
        raise ValueError("DMG stale backend rejection verification did not pass")
    expected_error = result.get("expected_error")
    if not isinstance(expected_error, str) or not expected_error:
        raise ValueError("DMG stale backend rejection is missing expected_error")
    return result


def run_checked(command: list[str]) -> str:
    result = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.stdout.strip()


def verify_gatekeeper(dmg_path: Path) -> dict:
    stapler = run_checked(["xcrun", "stapler", "validate", str(dmg_path)])
    spctl = run_checked(
        [
            "spctl",
            "-a",
            "-vv",
            "-t",
            "open",
            "--context",
            "context:primary-signature",
            str(dmg_path),
        ]
    )
    return {
        "checked": True,
        "stapler": stapler,
        "spctl": spctl,
    }


def attach_dmg(dmg_path: Path, mountpoint: Path) -> None:
    subprocess.run(
        [
            "hdiutil",
            "attach",
            str(dmg_path),
            "-nobrowse",
            "-noautoopen",
            "-readonly",
            "-mountpoint",
            str(mountpoint),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def detach_dmg(mountpoint: Path) -> None:
    result = subprocess.run(
        ["hdiutil", "detach", str(mountpoint)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        subprocess.run(
            ["hdiutil", "detach", str(mountpoint), "-force"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )


def verify_dmg(
    dmg_path: Path,
    *,
    expected_app_name: str,
    launch_app: bool = False,
    launch_timeout: float = 30.0,
    verify_installed_copy: bool = False,
    verify_stale_backend_rejection: bool = False,
    verify_gatekeeper_check: bool = False,
    expected_version: str | None = None,
) -> dict:
    if platform.system() != "Darwin":
        if launch_app or verify_installed_copy or verify_stale_backend_rejection:
            raise RuntimeError("DMG launch verification requires macOS")
        if verify_gatekeeper_check:
            raise RuntimeError("DMG Gatekeeper verification requires macOS")
        return {
            "ok": True,
            "checked": False,
            "reason": "DMG mount verification requires macOS",
        }
    require_asset_name_version(dmg_path, expected_version, label="DMG")
    expected_arch = dmg_expected_arch(dmg_path)
    if not dmg_path.exists() or dmg_path.stat().st_size <= 0:
        raise FileNotFoundError(f"Missing or empty DMG: {dmg_path}")

    gatekeeper = verify_gatekeeper(dmg_path) if verify_gatekeeper_check else None

    temp_parent = Path("/private/tmp") if Path("/private/tmp").exists() else None
    with tempfile.TemporaryDirectory(
        prefix="cc-branch-dmg-",
        dir=str(temp_parent) if temp_parent else None,
    ) as tmp:
        mountpoint = Path(tmp).resolve() / "mount"
        mountpoint.mkdir()
        attached = False
        try:
            attach_dmg(dmg_path, mountpoint)
            attached = True
            app_path = find_app_bundle(mountpoint, expected_app_name)
            shortcut = verify_applications_shortcut(mountpoint)
            content = verify_app_bundle_contains_backend(
                app_path,
                expected_version=expected_version,
            )
            launch = (
                require_bundled_backend_launch(
                    verify_app_launches_backend(
                        app_path,
                        timeout=launch_timeout,
                        expected_version=expected_version,
                        expected_platform="darwin" if expected_version else None,
                        expected_arch=expected_arch if expected_version else None,
                        use_auto_port=True,
                    )
                )
                if launch_app
                else None
            )
            installed_copy = (
                verify_installed_copy_launches_backend(
                    app_path,
                    install_root=Path(tmp).resolve() / "installed-copy",
                    expected_version=expected_version,
                    expected_platform="darwin" if expected_version else None,
                    expected_arch=expected_arch if expected_version else None,
                    timeout=launch_timeout,
                )
                if verify_installed_copy
                else None
            )
            stale_backend_rejection = (
                require_stale_backend_rejection(
                    verify_app_rejects_stale_backend(app_path, timeout=launch_timeout)
                )
                if verify_stale_backend_rejection
                else None
            )
            return {
                "ok": True,
                "checked": True,
                "dmg": str(dmg_path),
                "gatekeeper": gatekeeper,
                "launch": launch,
                "installed_copy": installed_copy,
                "stale_backend_rejection": stale_backend_rejection,
                **shortcut,
                **content,
            }
        finally:
            if attached:
                detach_dmg(mountpoint)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dmg", type=Path)
    parser.add_argument("--expected-app-name", default="CC Branch.app")
    parser.add_argument(
        "--launch-app",
        action="store_true",
        help="launch the app from the mounted DMG and verify its backend starts",
    )
    parser.add_argument(
        "--verify-stale-backend-rejection",
        action="store_true",
        help="launch the app with a stale backend on the same port and verify it rejects it",
    )
    parser.add_argument(
        "--verify-installed-copy",
        action="store_true",
        help="copy the app bundle out of the DMG and launch that installed copy",
    )
    parser.add_argument("--launch-timeout", type=float, default=30.0)
    parser.add_argument("--expected-version", default=None)
    parser.add_argument(
        "--verify-gatekeeper",
        action="store_true",
        help="validate the DMG notarization ticket and Gatekeeper acceptance",
    )
    args = parser.parse_args(argv)

    result = verify_dmg(
        args.dmg.resolve(),
        expected_app_name=args.expected_app_name,
        launch_app=args.launch_app,
        launch_timeout=args.launch_timeout,
        verify_installed_copy=args.verify_installed_copy,
        verify_stale_backend_rejection=args.verify_stale_backend_rejection,
        verify_gatekeeper_check=args.verify_gatekeeper,
        expected_version=args.expected_version,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
