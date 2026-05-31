#!/usr/bin/env python3
"""Verify platform desktop installers contain the backend sidecar."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def find_one(root: Path, pattern: str) -> Path:
    matches = sorted(path for path in root.rglob(pattern) if path.is_file())
    if not matches:
        raise FileNotFoundError(f"Could not find installer matching {pattern} under {root}")
    if len(matches) > 1:
        names = ", ".join(str(path.relative_to(root)) for path in matches)
        raise ValueError(f"Found multiple installers matching {pattern} under {root}: {names}")
    return matches[0]


def path_mentions_backend(path: str, *, windows: bool = False) -> bool:
    normalized = path.replace("\\", "/").lower()
    expected = "cc-branch-backend.exe" if windows else "cc-branch-backend"
    return normalized.endswith(expected)


def path_mentions_app_binary(path: str, *, windows: bool = False) -> bool:
    normalized = path.replace("\\", "/").lower()
    expected = "cc-branch.exe" if windows else "cc-branch"
    return normalized.endswith(expected) and not path_mentions_backend(path, windows=windows)


def listing_line_has_executable_mode(line: str) -> bool:
    mode = line.strip().split(maxsplit=1)[0] if line.strip() else ""
    if len(mode) < 10 or mode[0] not in "-l":
        return True
    return any(mode[index] == "x" for index in (3, 6, 9))


def listing_line_size(line: str) -> int | None:
    tokens = line.strip().split()
    if len(tokens) >= 3 and "/" in tokens[1] and tokens[2].isdigit():
        return int(tokens[2])
    if len(tokens) >= 5 and tokens[1].isdigit() and tokens[4].isdigit():
        return int(tokens[4])
    return None


def listing_line_path(line: str) -> Path:
    tokens = line.strip().split()
    if not tokens:
        raise ValueError("listing entry path could not be verified: empty line")
    for token in reversed(tokens):
        normalized = token.replace("\\", "/")
        if "/" in normalized:
            return Path(normalized)
    raise ValueError(f"listing entry path could not be verified: {line.strip()}")


def require_nonempty_listing_entry(line: str, *, label: str, entry_label: str) -> None:
    size = listing_line_size(line)
    if size is None:
        raise ValueError(f"{label} {entry_label} size could not be verified: {line.strip()}")
    if size <= 0:
        raise ValueError(f"{label} {entry_label} is empty: {line.strip()}")


def require_listing_entries_colocated(app_entry: str, backend_entry: str, *, label: str) -> None:
    app_path = listing_line_path(app_entry)
    backend_path = listing_line_path(backend_entry)
    if app_path.parent != backend_path.parent:
        raise ValueError(
            f"{label} app executable and backend sidecar must be in the same directory: "
            f"{app_path} vs {backend_path}"
        )


def require_listing_entry(
    listing: str,
    *,
    label: str,
    file_name: str,
    entry_label: str,
    matcher,
) -> str:
    matches = [line.strip() for line in listing.splitlines() if matcher(line)]
    if not matches:
        raise ValueError(f"{label} does not contain {file_name}")
    if len(matches) > 1:
        raise ValueError(f"{label} contains multiple {file_name}: {', '.join(matches)}")
    entry = matches[0]
    if not listing_line_has_executable_mode(entry):
        raise PermissionError(f"{label} {entry_label} is not executable: {entry}")
    require_nonempty_listing_entry(entry, label=label, entry_label=entry_label)
    return entry


def require_backend_in_listing(listing: str, *, label: str, windows: bool = False) -> str:
    suffix = "cc-branch-backend.exe" if windows else "cc-branch-backend"
    return require_listing_entry(
        listing,
        label=label,
        file_name=suffix,
        entry_label="backend sidecar",
        matcher=lambda line: path_mentions_backend(line, windows=windows),
    )


def require_app_binary_in_listing(listing: str, *, label: str, windows: bool = False) -> str:
    suffix = "cc-branch.exe" if windows else "cc-branch"
    return require_listing_entry(
        listing,
        label=label,
        file_name=suffix,
        entry_label="app executable",
        matcher=lambda line: path_mentions_app_binary(line, windows=windows),
    )


def run_text(command: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        command,
        check=True,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return f"{result.stdout}\n{result.stderr}"


def temporary_directory(prefix: str):
    try:
        return tempfile.TemporaryDirectory(
            prefix=prefix,
            ignore_cleanup_errors=True,
        )
    except TypeError:
        return tempfile.TemporaryDirectory(prefix=prefix)


def current_windows_identity() -> str:
    user = os.environ.get("USERNAME")
    if user:
        return user
    try:
        identity = run_text(["whoami"]).strip().splitlines()[0]
    except Exception:
        identity = ""
    return identity or "Users"


def grant_windows_path_access(path: Path, *, recursive: bool = False) -> None:
    if platform.system() != "Windows":
        return
    if shutil.which("icacls") is None:
        return
    identity = current_windows_identity()
    grants = [f"{identity}:F"]
    if recursive:
        grants = [f"{identity}:(OI)(CI)F", "*S-1-5-32-545:(OI)(CI)RX"]
        if shutil.which("takeown") is not None:
            try:
                subprocess.run(
                    ["takeown", "/F", str(path), "/R", "/D", "Y"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
            except OSError:
                pass
        try:
            subprocess.run(
                ["icacls", str(path), "/inheritance:e"],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            return
    for grant in grants:
        command = ["icacls", str(path), "/grant", grant, "/C"]
        if recursive:
            command.extend(["/T"])
        try:
            subprocess.run(command, check=False, capture_output=True, text=True)
        except OSError:
            return


def grant_windows_tree_access(root: Path) -> None:
    grant_windows_path_access(root, recursive=True)


def stat_file(path: Path, *, label: str) -> os.stat_result:
    last_error: PermissionError | None = None
    for attempt in range(6):
        try:
            return path.stat()
        except PermissionError as error:
            if platform.system() != "Windows" or getattr(error, "winerror", None) != 5:
                raise
            last_error = error
            grant_windows_path_access(path)
            time.sleep(0.2 * (attempt + 1))
    raise PermissionError(f"{label} could not be read after Windows ACL repair: {path}") from last_error


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise FileNotFoundError(f"Required installer verification tool is missing: {name}")


def find_7z() -> str:
    for candidate in ("7z", "7z.exe"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    default = Path("C:/Program Files/7-Zip/7z.exe")
    if default.exists():
        return str(default)
    raise FileNotFoundError("Required installer verification tool is missing: 7z")


def require_package_version(
    package_version: str,
    expected_version: str | None,
    *,
    label: str,
) -> str:
    version = package_version.strip()
    if not version:
        raise ValueError(f"{label} package version is empty")
    if expected_version is not None and version != expected_version:
        raise ValueError(
            f"{label} package version {version!r} does not match expected {expected_version!r}"
        )
    return version


def require_asset_name_version(asset: Path, expected_version: str | None, *, label: str) -> None:
    if expected_version is not None and re.search(rf"(?<!\d){re.escape(expected_version)}(?!\d)", asset.name) is None:
        raise ValueError(
            f"{label} asset {asset.name!r} does not match expected {expected_version!r}"
        )


def read_windows_executable_version(executable: Path) -> str:
    version = run_text([
        "powershell",
        "-NoProfile",
        "-Command",
        f"(Get-Item -LiteralPath {json.dumps(str(executable))}).VersionInfo.ProductVersion",
    ]).strip()
    if not version:
        raise ValueError(f"Windows executable version is empty: {executable}")
    return version


def verify_deb(
    bundle_dir: Path,
    *,
    expected_version: str | None = None,
    launch_app: bool = False,
) -> dict:
    require_tool("dpkg-deb")
    deb = find_one(bundle_dir, "*.deb")
    listing = run_text(["dpkg-deb", "--contents", str(deb)])
    app = require_app_binary_in_listing(listing, label=deb.name)
    backend = require_backend_in_listing(listing, label=deb.name)
    require_listing_entries_colocated(app, backend, label=deb.name)
    package_version = None
    if expected_version is not None:
        package_version = require_package_version(
            run_text(["dpkg-deb", "--field", str(deb), "Version"]),
            expected_version,
            label=deb.name,
        )
    launch_result = {}
    if launch_app:
        with tempfile.TemporaryDirectory(prefix="cc-branch-deb-") as tmp:
            target = Path(tmp) / "extract"
            target.mkdir()
            run_text(["dpkg-deb", "--extract", str(deb), str(target)])
            launch_result = verify_extracted_linux_package_launch(
                target,
                label=deb.name,
                expected_version=expected_version,
            )
    return {
        "asset": str(deb),
        "app": app,
        "backend": backend,
        "package_version": package_version,
        **launch_result,
    }


def verify_rpm(
    bundle_dir: Path,
    *,
    expected_version: str | None = None,
    launch_app: bool = False,
) -> dict:
    require_tool("rpm")
    require_tool("rpm2cpio")
    require_tool("cpio")
    rpm = find_one(bundle_dir, "*.rpm")
    listing = subprocess.run(
        f"rpm2cpio {shlex_quote(str(rpm))} | cpio -tv",
        shell=True,
        check=True,
        capture_output=True,
        text=True,
    )
    backend = require_backend_in_listing(
        f"{listing.stdout}\n{listing.stderr}",
        label=rpm.name,
    )
    app = require_app_binary_in_listing(
        f"{listing.stdout}\n{listing.stderr}",
        label=rpm.name,
    )
    require_listing_entries_colocated(app, backend, label=rpm.name)
    package_version = None
    if expected_version is not None:
        package_version = require_package_version(
            run_text(["rpm", "-qp", "--queryformat", "%{VERSION}", str(rpm)]),
            expected_version,
            label=rpm.name,
        )
    launch_result = {}
    if launch_app:
        with tempfile.TemporaryDirectory(prefix="cc-branch-rpm-") as tmp:
            target = Path(tmp) / "extract"
            target.mkdir()
            subprocess.run(
                f"rpm2cpio {shlex_quote(str(rpm))} | cpio -idmv",
                shell=True,
                check=True,
                cwd=target,
                capture_output=True,
                text=True,
            )
            launch_result = verify_extracted_linux_package_launch(
                target,
                label=rpm.name,
                expected_version=expected_version,
            )
    return {
        "asset": str(rpm),
        "app": app,
        "backend": backend,
        "package_version": package_version,
        **launch_result,
    }


def shlex_quote(value: str) -> str:
    import shlex

    return shlex.quote(value)


def verify_desktop_app_launch(
    executable: Path,
    *,
    expected_version: str | None = None,
    expected_platform: str | None = None,
    expected_arch: str | None = None,
) -> dict:
    script_path = Path(__file__).with_name("smoke-test-desktop-app.py")
    spec = importlib.util.spec_from_file_location("smoke_test_desktop_app", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify_desktop_app(
        executable,
        timeout=30.0,
        expected_version=expected_version,
        expected_platform=expected_platform,
        expected_arch=expected_arch,
        use_auto_port=True,
    )


def verify_desktop_app_stale_backend_rejection(
    executable: Path,
    *,
    sidecar_executable: Path,
) -> dict:
    script_path = Path(__file__).with_name("smoke-test-desktop-app.py")
    spec = importlib.util.spec_from_file_location("smoke_test_desktop_app", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify_desktop_rejects_stale_backend(
        executable,
        sidecar_executable=sidecar_executable,
        timeout=30.0,
    )


def require_bundled_backend_launch(launch: dict) -> dict:
    if launch.get("ok") is not True:
        raise ValueError("Installer launch verification did not pass")
    source = launch.get("backend_source")
    if source != "bundled-sidecar":
        raise ValueError(
            f"Installer launch used backend_source={source!r}, expected 'bundled-sidecar'"
        )
    return launch


def require_stale_backend_rejection(result: dict) -> dict:
    if result.get("ok") is not True:
        raise ValueError("Installer stale backend rejection verification did not pass")
    expected_error = result.get("expected_error")
    if not isinstance(expected_error, str) or not expected_error:
        raise ValueError("Installer stale backend rejection is missing expected_error")
    return result


def require_nonempty_file(path: Path, *, label: str) -> None:
    if stat_file(path, label=label).st_size <= 0:
        raise ValueError(f"{label} is empty: {path}")


def require_same_directory(app: Path, backend: Path, *, label: str) -> None:
    if app.parent != backend.parent:
        raise ValueError(
            f"{label} app executable and backend sidecar must be in the same directory: "
            f"{app} vs {backend}"
        )


def require_one_match(matches: list[Path], *, label: str, file_name: str) -> Path:
    if not matches:
        raise ValueError(f"{label} does not contain {file_name}")
    if len(matches) > 1:
        names = ", ".join(str(path) for path in matches)
        raise ValueError(f"{label} contains multiple {file_name}: {names}")
    return matches[0]


def find_extracted_linux_executables(root: Path, *, label: str) -> tuple[Path, Path]:
    app_matches = sorted(
        path
        for path in root.rglob("cc-branch")
        if path.is_file() and not path_mentions_backend(str(path))
    )
    backend_matches = sorted(
        path for path in root.rglob("cc-branch-backend") if path.is_file()
    )
    app = require_one_match(app_matches, label=label, file_name="cc-branch")
    backend = require_one_match(
        backend_matches,
        label=label,
        file_name="cc-branch-backend",
    )
    require_nonempty_file(app, label=f"{label} app executable")
    require_nonempty_file(backend, label=f"{label} backend sidecar")
    if not os.access(app, os.X_OK):
        raise PermissionError(f"{label} app executable is not executable: {app}")
    if not os.access(backend, os.X_OK):
        raise PermissionError(f"{label} backend sidecar is not executable: {backend}")
    require_same_directory(app, backend, label=label)
    return app, backend


def verify_extracted_linux_package_launch(
    root: Path,
    *,
    label: str,
    expected_version: str | None = None,
) -> dict:
    app, backend = find_extracted_linux_executables(root, label=label)
    launch = require_bundled_backend_launch(
        verify_desktop_app_launch(
            app,
            expected_version=expected_version,
            expected_platform="linux" if expected_version else None,
            expected_arch="x86_64" if expected_version else None,
        )
    )
    stale_backend_rejection = require_stale_backend_rejection(
        verify_desktop_app_stale_backend_rejection(
            app,
            sidecar_executable=backend,
        )
    )
    return {
        "extracted_app": str(app.relative_to(root)),
        "extracted_backend": str(backend.relative_to(root)),
        "launch": launch,
        "stale_backend_rejection": stale_backend_rejection,
    }


def verify_appimage(
    bundle_dir: Path,
    *,
    expected_version: str | None = None,
    launch_app: bool = False,
) -> dict:
    appimage = find_one(bundle_dir, "*.AppImage")
    require_asset_name_version(appimage, expected_version, label="AppImage")
    appimage.chmod(appimage.stat().st_mode | 0o111)
    with tempfile.TemporaryDirectory(prefix="cc-branch-appimage-") as tmp:
        workdir = Path(tmp)
        run_text([str(appimage), "--appimage-extract"], cwd=workdir)
        extracted = workdir / "squashfs-root"
        if not extracted.exists():
            raise FileNotFoundError(f"AppImage extraction did not create {extracted}")
        matches = sorted(
            path for path in extracted.rglob("cc-branch-backend") if path.is_file()
        )
        backend = require_one_match(
            matches,
            label=appimage.name,
            file_name="cc-branch-backend",
        )
        require_nonempty_file(backend, label="AppImage backend sidecar")
        if not os.access(backend, os.X_OK):
            raise PermissionError(f"AppImage backend sidecar is not executable: {backend}")
        app_run = extracted / "AppRun"
        if not app_run.exists() or not os.access(app_run, os.X_OK):
            raise FileNotFoundError(f"AppImage extraction did not create executable AppRun: {app_run}")
        require_nonempty_file(app_run, label="AppImage AppRun")
        if launch_app:
            launch = require_bundled_backend_launch(
                verify_desktop_app_launch(
                    appimage,
                    expected_version=expected_version,
                    expected_platform="linux" if expected_version else None,
                    expected_arch="x86_64" if expected_version else None,
                )
            )
            stale_backend_rejection = require_stale_backend_rejection(
                verify_desktop_app_stale_backend_rejection(
                    appimage,
                    sidecar_executable=backend,
                )
            )
        else:
            launch = None
            stale_backend_rejection = None
        return {
            "asset": str(appimage),
            "asset_version": expected_version,
            "app": str(app_run.relative_to(extracted)),
            "app_size": app_run.stat().st_size,
            "backend": str(backend.relative_to(extracted)),
            "backend_size": backend.stat().st_size,
            "launch": launch,
            "stale_backend_rejection": stale_backend_rejection,
        }


def verify_msi(
    bundle_dir: Path,
    *,
    expected_version: str | None = None,
    launch_app: bool = False,
) -> dict:
    msi = find_one(bundle_dir, "*.msi")
    require_asset_name_version(msi, expected_version, label="MSI")
    if platform.system() != "Windows":
        if launch_app:
            raise RuntimeError("MSI launch verification requires Windows")
        return {
            "asset": str(msi),
            "checked": False,
            "reason": "MSI extraction requires Windows",
            "launch": None,
        }
    with temporary_directory(prefix="cc-branch-msi-") as tmp:
        target = Path(tmp) / "extract"
        target.mkdir()
        subprocess.run(
            ["msiexec", "/a", str(msi), "/qn", f"TARGETDIR={target}"],
            check=True,
        )
        grant_windows_tree_access(target)
        matches = sorted(
            path for path in target.rglob("cc-branch-backend.exe") if path.is_file()
        )
        backend = require_one_match(matches, label=msi.name, file_name="cc-branch-backend.exe")
        require_nonempty_file(backend, label="MSI backend sidecar")
        app_matches = sorted(
            path
            for path in target.rglob("cc-branch.exe")
            if path.is_file() and path.name.lower() != "cc-branch-backend.exe"
        )
        app = require_one_match(app_matches, label=msi.name, file_name="cc-branch.exe")
        for app in app_matches:
            require_nonempty_file(app, label="MSI app executable")
        require_same_directory(app, backend, label=msi.name)
        app_version = None
        if expected_version is not None:
            app_version = require_package_version(
                read_windows_executable_version(app),
                expected_version,
                label=f"{msi.name} app executable",
            )
        if launch_app:
            launch = require_bundled_backend_launch(
                verify_desktop_app_launch(
                    app,
                    expected_version=expected_version,
                    expected_platform="windows" if expected_version else None,
                    expected_arch="x86_64" if expected_version else None,
                )
            )
            stale_backend_rejection = require_stale_backend_rejection(
                verify_desktop_app_stale_backend_rejection(
                    app,
                    sidecar_executable=backend,
                )
            )
        else:
            launch = None
            stale_backend_rejection = None
        return {
            "asset": str(msi),
            "checked": True,
            "app": str(app.relative_to(target)),
            "app_size": app.stat().st_size,
            "app_version": app_version,
            "backend": str(backend.relative_to(target)),
            "backend_size": backend.stat().st_size,
            "launch": launch,
            "stale_backend_rejection": stale_backend_rejection,
        }


def verify_nsis(
    bundle_dir: Path,
    *,
    expected_version: str | None = None,
    launch_app: bool = False,
) -> dict:
    nsis = find_one(bundle_dir, "*setup*.exe")
    require_asset_name_version(nsis, expected_version, label="NSIS")
    if platform.system() != "Windows":
        if launch_app:
            raise RuntimeError("NSIS launch verification requires Windows")
        return {
            "asset": str(nsis),
            "checked": False,
            "reason": "NSIS extraction requires Windows",
            "launch": None,
        }
    with temporary_directory(prefix="cc-branch-nsis-") as tmp:
        target = Path(tmp) / "extract"
        target.mkdir()
        run_text([find_7z(), "x", str(nsis), f"-o{target}", "-y"])
        grant_windows_tree_access(target)
        matches = sorted(
            path for path in target.rglob("cc-branch-backend.exe") if path.is_file()
        )
        backend = require_one_match(matches, label=nsis.name, file_name="cc-branch-backend.exe")
        require_nonempty_file(backend, label="NSIS backend sidecar")
        app_matches = sorted(
            path
            for path in target.rglob("cc-branch.exe")
            if path.is_file() and path.name.lower() != "cc-branch-backend.exe"
        )
        app = require_one_match(app_matches, label=nsis.name, file_name="cc-branch.exe")
        for app in app_matches:
            require_nonempty_file(app, label="NSIS app executable")
        require_same_directory(app, backend, label=nsis.name)
        app_version = None
        if expected_version is not None:
            app_version = require_package_version(
                read_windows_executable_version(app),
                expected_version,
                label=f"{nsis.name} app executable",
            )
        if launch_app:
            launch = require_bundled_backend_launch(
                verify_desktop_app_launch(
                    app,
                    expected_version=expected_version,
                    expected_platform="windows" if expected_version else None,
                    expected_arch="x86_64" if expected_version else None,
                )
            )
            stale_backend_rejection = require_stale_backend_rejection(
                verify_desktop_app_stale_backend_rejection(
                    app,
                    sidecar_executable=backend,
                )
            )
        else:
            launch = None
            stale_backend_rejection = None
        return {
            "asset": str(nsis),
            "checked": True,
            "app": str(app.relative_to(target)),
            "app_size": app.stat().st_size,
            "app_version": app_version,
            "backend": str(backend.relative_to(target)),
            "backend_size": backend.stat().st_size,
            "launch": launch,
            "stale_backend_rejection": stale_backend_rejection,
        }


def verify_installers(
    bundle_dir: Path,
    target_platform: str,
    *,
    expected_version: str | None = None,
    launch_appimage: bool = False,
    launch_linux_packages: bool = False,
    launch_windows_msi: bool = False,
    launch_windows_nsis: bool = False,
) -> dict:
    if target_platform == "linux":
        return {
            "ok": True,
            "platform": target_platform,
            "deb": verify_deb(
                bundle_dir,
                expected_version=expected_version,
                launch_app=launch_linux_packages,
            ),
            "rpm": verify_rpm(
                bundle_dir,
                expected_version=expected_version,
                launch_app=launch_linux_packages,
            ),
            "appimage": verify_appimage(
                bundle_dir,
                expected_version=expected_version,
                launch_app=launch_appimage,
            ),
        }
    if target_platform == "windows":
        return {
            "ok": True,
            "platform": target_platform,
            "msi": verify_msi(
                bundle_dir,
                expected_version=expected_version,
                launch_app=launch_windows_msi,
            ),
            "nsis": verify_nsis(
                bundle_dir,
                expected_version=expected_version,
                launch_app=launch_windows_nsis,
            ),
        }
    raise ValueError(f"Unsupported installer verification platform: {target_platform}")


def default_platform() -> str:
    system = platform.system()
    if system == "Linux":
        return "linux"
    if system == "Windows":
        return "windows"
    raise ValueError(f"Installer verification is not implemented for {system}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--platform", choices=["linux", "windows"], default=None)
    parser.add_argument("--expected-version", default=None)
    parser.add_argument(
        "--launch-appimage",
        action="store_true",
        help="launch the downloaded AppImage and verify the backend starts",
    )
    parser.add_argument(
        "--launch-linux-packages",
        action="store_true",
        help="extract the Linux DEB/RPM packages and launch their packaged app binaries",
    )
    parser.add_argument(
        "--launch-windows-msi",
        action="store_true",
        help="extract the Windows MSI and launch cc-branch.exe to verify the backend starts",
    )
    parser.add_argument(
        "--launch-windows-nsis",
        action="store_true",
        help="extract the Windows NSIS setup EXE and launch cc-branch.exe to verify the backend starts",
    )
    args = parser.parse_args(argv)

    result = verify_installers(
        args.bundle_dir.resolve(),
        args.platform or default_platform(),
        expected_version=args.expected_version,
        launch_appimage=args.launch_appimage,
        launch_linux_packages=args.launch_linux_packages,
        launch_windows_msi=args.launch_windows_msi,
        launch_windows_nsis=args.launch_windows_nsis,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
