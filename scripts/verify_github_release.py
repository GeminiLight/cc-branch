#!/usr/bin/env python3
"""Download and verify a GitHub desktop release canary."""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    from scripts.verify_release_canary import (
        REQUIRED_DOWNLOAD_ASSETS,
        asset_name_from_url,
        parse_assets_json,
        validate_checksum_manifest,
        verify_release_dir,
    )
except ModuleNotFoundError:
    from verify_release_canary import (
        REQUIRED_DOWNLOAD_ASSETS,
        asset_name_from_url,
        parse_assets_json,
        validate_checksum_manifest,
        verify_release_dir,
    )


def gh_command(args: list[str], *, repo: str | None = None) -> list[str]:
    command = ["gh", *args]
    if repo:
        command.extend(["--repo", repo])
    return command


def run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def verify_github_release_is_latest(
    expected_tag: str,
    repo: str | None,
    *,
    timeout: float = 120.0,
    poll_interval: float = 5.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    latest: dict[str, Any] = {}
    while True:
        latest = run_json(release_view_command(None, repo))
        if latest.get("tagName") == expected_tag:
            return latest
        if time.monotonic() >= deadline:
            break
        time.sleep(poll_interval)

    latest_tag = latest.get("tagName")
    latest_url = latest.get("url") or "<unknown>"
    raise ValueError(
        f"GitHub latest release is {latest_tag}, expected {expected_tag}. "
        f"Latest URL: {latest_url}"
    )


def selected_platform_asset(latest_json: dict[str, Any], platform: str) -> str:
    platforms = latest_json.get("platforms")
    if not isinstance(platforms, dict):
        raise ValueError("latest.json is missing platforms")
    item = platforms.get(platform)
    if not isinstance(item, dict):
        raise ValueError(f"latest.json is missing platform entry: {platform}")
    url = item.get("url")
    if not isinstance(url, str) or not url:
        raise ValueError(f"Platform {platform} is missing url")
    return asset_name_from_url(url)


def selected_latest_platform_assets(latest_json: dict[str, Any]) -> list[str]:
    platforms = latest_json.get("platforms")
    if not isinstance(platforms, dict):
        raise ValueError("latest.json is missing platforms")
    assets: list[str] = []
    for platform, item in sorted(platforms.items()):
        if not isinstance(item, dict):
            raise ValueError(f"Platform {platform} is not an object")
        url = item.get("url")
        if not isinstance(url, str) or not url:
            raise ValueError(f"Platform {platform} is missing url")
        assets.append(asset_name_from_url(url))
    return list(dict.fromkeys(assets))


def selected_macos_updater_assets(latest_json: dict[str, Any]) -> list[str]:
    platforms = latest_json.get("platforms")
    if not isinstance(platforms, dict):
        raise ValueError("latest.json is missing platforms")
    assets: list[str] = []
    for platform, item in sorted(platforms.items()):
        if not str(platform).startswith("darwin-"):
            continue
        if not isinstance(item, dict):
            raise ValueError(f"Platform {platform} is not an object")
        url = item.get("url")
        if not isinstance(url, str) or not url:
            raise ValueError(f"Platform {platform} is missing url")
        asset = asset_name_from_url(url)
        if asset.endswith(".app.tar.gz"):
            assets.append(asset)
    if not assets:
        raise ValueError("latest.json does not reference any macOS updater app tarballs")
    return assets


def selected_download_asset(available_assets: set[str], label: str) -> str:
    for asset_label, pattern in REQUIRED_DOWNLOAD_ASSETS:
        if asset_label != label:
            continue
        matches = [name for name in sorted(available_assets) if re.search(pattern, name)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(
                f"Release has multiple recommended download assets for {label}: "
                + ", ".join(matches)
            )
        raise ValueError(f"Release is missing recommended download asset: {label} ({pattern})")
    raise ValueError(f"Unknown recommended download asset label: {label}")


def macos_dmg_assets(available_assets: set[str]) -> dict[str, str]:
    return {
        "apple_silicon": selected_download_asset(
            available_assets,
            "macOS Apple Silicon DMG",
        ),
        "intel": selected_download_asset(available_assets, "macOS Intel DMG"),
    }


def verify_macos_dmg_asset(
    dmg_path: Path,
    *,
    launch_app: bool,
    verify_installed_copy: bool = False,
    verify_stale_backend_rejection: bool | None = None,
    verify_gatekeeper_check: bool = False,
    expected_version: str | None = None,
    launch_timeout: float = 30.0,
) -> dict[str, Any]:
    script_path = Path(__file__).with_name("verify-macos-dmg.py")
    spec = importlib.util.spec_from_file_location("verify_macos_dmg", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify_dmg(
        dmg_path,
        expected_app_name="CC Branch.app",
        launch_app=launch_app,
        verify_installed_copy=verify_installed_copy,
        verify_stale_backend_rejection=(
            launch_app
            if verify_stale_backend_rejection is None
            else verify_stale_backend_rejection
        ),
        verify_gatekeeper_check=verify_gatekeeper_check,
        expected_version=expected_version,
        launch_timeout=launch_timeout,
    )


def verify_platform_installers(
    release_dir: Path,
    target_platform: str,
    *,
    expected_version: str | None = None,
    launch_appimage: bool = False,
    launch_linux_packages: bool = False,
    launch_windows_msi: bool = False,
    launch_windows_nsis: bool = False,
    launch_timeout: float = 30.0,
) -> dict[str, Any]:
    script_path = Path(__file__).with_name("verify-desktop-installers.py")
    spec = importlib.util.spec_from_file_location("verify_desktop_installers", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify_installers(
        release_dir,
        target_platform,
        expected_version=expected_version,
        launch_appimage=launch_appimage,
        launch_linux_packages=launch_linux_packages,
        launch_windows_msi=launch_windows_msi,
        launch_windows_nsis=launch_windows_nsis,
        launch_timeout=launch_timeout,
    )


def collect_launch_backend_sources(result: dict[str, Any]) -> dict[str, str]:
    sources: dict[str, str] = {}

    def record(label: str, verification: Any) -> None:
        if not isinstance(verification, dict):
            return
        launch = verification.get("launch")
        if launch is not None:
            if not isinstance(launch, dict):
                raise ValueError(f"{label} launch verification is not an object")
            if launch.get("ok") is not True:
                raise ValueError(f"{label} launch verification did not pass")
            source = launch.get("backend_source")
            if not isinstance(source, str) or not source:
                raise ValueError(f"{label} launch verification is missing backend_source")
            if source != "bundled-sidecar":
                raise ValueError(
                    f"{label} launched with backend_source={source!r}, expected 'bundled-sidecar'"
                )
            sources[label] = source

        installed_copy = verification.get("installed_copy")
        if installed_copy is not None:
            if not isinstance(installed_copy, dict):
                raise ValueError(f"{label} installed copy verification is not an object")
            installed_launch = installed_copy.get("launch")
            if not isinstance(installed_launch, dict):
                raise ValueError(f"{label} installed copy launch verification is not an object")
            if installed_launch.get("ok") is not True:
                raise ValueError(f"{label} installed copy launch verification did not pass")
            source = installed_launch.get("backend_source")
            if not isinstance(source, str) or not source:
                raise ValueError(
                    f"{label} installed copy launch verification is missing backend_source"
                )
            if source != "bundled-sidecar":
                raise ValueError(
                    f"{label} installed copy launched with backend_source={source!r}, "
                    "expected 'bundled-sidecar'"
                )
            sources[f"{label}.installed_copy"] = source

    macos_dmgs = result.get("macos_dmgs")
    if isinstance(macos_dmgs, dict):
        for label, verification in sorted(macos_dmgs.items()):
            record(f"macos.{label}", verification)
    else:
        record("macos.dmg", result.get("dmg"))

    linux = result.get("linux")
    if isinstance(linux, dict):
        record("linux.deb", linux.get("deb"))
        record("linux.rpm", linux.get("rpm"))
        record("linux.appimage", linux.get("appimage"))

    windows = result.get("windows")
    if isinstance(windows, dict):
        record("windows.msi", windows.get("msi"))
        record("windows.nsis", windows.get("nsis"))

    return sources


def collect_launch_desktop_metadata(result: dict[str, Any]) -> dict[str, dict[str, str]]:
    metadata_by_label: dict[str, dict[str, str]] = {}

    def metadata_from_launch(label: str, launch: dict[str, Any]) -> dict[str, str]:
        if launch.get("ok") is not True:
            raise ValueError(f"{label} launch verification did not pass")
        metadata: dict[str, str] = {}
        for key in ("desktop_version", "desktop_platform", "desktop_arch"):
            value = launch.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} launch verification is missing {key}")
            metadata[key] = value
        return metadata

    def record(label: str, verification: Any) -> None:
        if not isinstance(verification, dict):
            return
        launch = verification.get("launch")
        if launch is not None:
            if not isinstance(launch, dict):
                raise ValueError(f"{label} launch verification is not an object")
            metadata_by_label[label] = metadata_from_launch(label, launch)

        installed_copy = verification.get("installed_copy")
        if installed_copy is not None:
            if not isinstance(installed_copy, dict):
                raise ValueError(f"{label} installed copy verification is not an object")
            installed_launch = installed_copy.get("launch")
            if not isinstance(installed_launch, dict):
                raise ValueError(f"{label} installed copy launch verification is not an object")
            metadata_by_label[f"{label}.installed_copy"] = metadata_from_launch(
                f"{label} installed copy",
                installed_launch,
            )

    macos_dmgs = result.get("macos_dmgs")
    if isinstance(macos_dmgs, dict):
        for label, verification in sorted(macos_dmgs.items()):
            record(f"macos.{label}", verification)
    else:
        record("macos.dmg", result.get("dmg"))

    linux = result.get("linux")
    if isinstance(linux, dict):
        record("linux.deb", linux.get("deb"))
        record("linux.rpm", linux.get("rpm"))
        record("linux.appimage", linux.get("appimage"))

    windows = result.get("windows")
    if isinstance(windows, dict):
        record("windows.msi", windows.get("msi"))
        record("windows.nsis", windows.get("nsis"))

    return metadata_by_label


def collect_launch_port_modes(result: dict[str, Any]) -> dict[str, str]:
    port_modes: dict[str, str] = {}

    def port_mode_from_launch(label: str, launch: dict[str, Any]) -> str:
        if launch.get("ok") is not True:
            raise ValueError(f"{label} launch verification did not pass")
        port_mode = launch.get("port_mode")
        if not isinstance(port_mode, str) or not port_mode.strip():
            raise ValueError(f"{label} launch verification is missing port_mode")
        return port_mode

    def record(label: str, verification: Any) -> None:
        if not isinstance(verification, dict):
            return
        launch = verification.get("launch")
        if launch is not None:
            if not isinstance(launch, dict):
                raise ValueError(f"{label} launch verification is not an object")
            port_modes[label] = port_mode_from_launch(label, launch)

        installed_copy = verification.get("installed_copy")
        if installed_copy is not None:
            if not isinstance(installed_copy, dict):
                raise ValueError(f"{label} installed copy verification is not an object")
            installed_launch = installed_copy.get("launch")
            if not isinstance(installed_launch, dict):
                raise ValueError(f"{label} installed copy launch verification is not an object")
            port_modes[f"{label}.installed_copy"] = port_mode_from_launch(
                f"{label} installed copy",
                installed_launch,
            )

    macos_dmgs = result.get("macos_dmgs")
    if isinstance(macos_dmgs, dict):
        for label, verification in sorted(macos_dmgs.items()):
            record(f"macos.{label}", verification)
    else:
        record("macos.dmg", result.get("dmg"))

    linux = result.get("linux")
    if isinstance(linux, dict):
        record("linux.deb", linux.get("deb"))
        record("linux.rpm", linux.get("rpm"))
        record("linux.appimage", linux.get("appimage"))

    windows = result.get("windows")
    if isinstance(windows, dict):
        record("windows.msi", windows.get("msi"))
        record("windows.nsis", windows.get("nsis"))

    return port_modes


def collect_stale_backend_rejections(result: dict[str, Any]) -> dict[str, str]:
    rejections: dict[str, str] = {}

    def record(label: str, verification: Any) -> None:
        if not isinstance(verification, dict):
            return
        stale = verification.get("stale_backend_rejection")
        if stale is None:
            return
        if not isinstance(stale, dict):
            raise ValueError(f"{label} stale backend rejection verification is not an object")
        if stale.get("ok") is not True:
            raise ValueError(f"{label} stale backend rejection verification did not pass")
        expected_error = stale.get("expected_error")
        if not isinstance(expected_error, str) or not expected_error:
            raise ValueError(
                f"{label} stale backend rejection verification is missing expected_error"
            )
        rejections[label] = expected_error

    macos_dmgs = result.get("macos_dmgs")
    if isinstance(macos_dmgs, dict):
        for label, verification in sorted(macos_dmgs.items()):
            record(f"macos.{label}", verification)
    else:
        record("macos.dmg", result.get("dmg"))

    linux = result.get("linux")
    if isinstance(linux, dict):
        record("linux.deb", linux.get("deb"))
        record("linux.rpm", linux.get("rpm"))
        record("linux.appimage", linux.get("appimage"))

    windows = result.get("windows")
    if isinstance(windows, dict):
        record("windows.msi", windows.get("msi"))
        record("windows.nsis", windows.get("nsis"))

    return rejections


def require_launch_backend_sources(
    sources: dict[str, str],
    required_labels: list[str],
) -> None:
    missing = [label for label in required_labels if label not in sources]
    if missing:
        raise ValueError(
            "Missing required launch verification: " + ", ".join(missing)
        )


def require_launch_desktop_metadata(
    metadata_by_label: dict[str, dict[str, str]],
    required_labels: list[str],
    *,
    expected_version: str | None = None,
) -> None:
    missing = [label for label in required_labels if label not in metadata_by_label]
    if missing:
        raise ValueError(
            "Missing required launch desktop metadata: " + ", ".join(missing)
        )
    for label in required_labels:
        metadata = metadata_by_label[label]
        if expected_version is not None and metadata.get("desktop_version") != expected_version:
            raise ValueError(
                f"{label} launch desktop metadata desktop_version={metadata.get('desktop_version')!r}, "
                f"expected {expected_version!r}"
            )
        expected_platform_arch = expected_desktop_platform_arch(label)
        if expected_platform_arch is None:
            continue
        expected_platform, expected_arch = expected_platform_arch
        if metadata.get("desktop_platform") != expected_platform:
            raise ValueError(
                f"{label} launch desktop metadata desktop_platform={metadata.get('desktop_platform')!r}, "
                f"expected {expected_platform!r}"
            )
        if metadata.get("desktop_arch") != expected_arch:
            raise ValueError(
                f"{label} launch desktop metadata desktop_arch={metadata.get('desktop_arch')!r}, "
                f"expected {expected_arch!r}"
            )


def require_launch_port_modes(
    port_modes: dict[str, str],
    required_labels: list[str],
) -> None:
    missing = [label for label in required_labels if label not in port_modes]
    if missing:
        raise ValueError(
            "Missing required launch port mode verification: " + ", ".join(missing)
        )
    for label in required_labels:
        port_mode = port_modes[label]
        if port_mode != "auto":
            raise ValueError(
                f"{label} launch verification reported port_mode={port_mode!r}, expected 'auto'"
            )


def expected_desktop_platform_arch(label: str) -> tuple[str, str] | None:
    if label.startswith("macos.apple_silicon"):
        return ("darwin", "aarch64")
    if label.startswith("macos.intel"):
        return ("darwin", "x86_64")
    if label.startswith("linux."):
        return ("linux", "x86_64")
    if label.startswith("windows."):
        return ("windows", "x86_64")
    return None


def require_stale_backend_rejections(
    rejections: dict[str, str],
    required_labels: list[str],
) -> None:
    missing = [label for label in required_labels if label not in rejections]
    if missing:
        raise ValueError(
            "Missing required stale backend rejection verification: " + ", ".join(missing)
        )


def build_verification_summary(
    *,
    repo: str | None,
    release_tag: str,
    release_url: str | None,
    is_draft: bool | None,
    is_prerelease: bool | None,
    latest_release: dict[str, Any] | None,
    require_latest: bool,
    require_public: bool,
    required_launch_labels: list[str],
    required_stale_labels: list[str],
    launch_backend_sources: dict[str, str],
    launch_desktop_metadata: dict[str, dict[str, str]],
    launch_port_modes: dict[str, str],
    stale_backend_rejections: dict[str, str],
    required_checksum_assets: list[str] | None = None,
    checksum_verified_assets: list[str] | None = None,
    release_notes_checked: bool = False,
    latest_json_notes_checked: bool = False,
) -> dict[str, Any]:
    sorted_required_launch_labels = sorted(required_launch_labels)
    sorted_required_stale_labels = sorted(required_stale_labels)
    sorted_required_checksum_assets = sorted(required_checksum_assets or [])
    sorted_checksum_verified_assets = sorted(checksum_verified_assets or [])
    latest_tag = latest_release.get("tagName") if isinstance(latest_release, dict) else None
    latest_url = latest_release.get("url") if isinstance(latest_release, dict) else None
    release_is_public = is_draft is False and is_prerelease is False
    latest_matches_tag = latest_tag == release_tag if latest_release is not None else None
    checks = {
        "public_release_requirement_met": (
            release_is_public if require_public else True
        ),
        "latest_release_requirement_met": (
            latest_matches_tag is True if require_latest else True
        ),
        "all_required_launches_verified": all(
            label in launch_backend_sources
            and label in launch_desktop_metadata
            and label in launch_port_modes
            for label in sorted_required_launch_labels
        ),
        "all_required_stale_backend_rejections_verified": all(
            label in stale_backend_rejections
            for label in sorted_required_stale_labels
        ),
        "all_required_checksum_assets_verified": all(
            asset in sorted_checksum_verified_assets
            for asset in sorted_required_checksum_assets
        ),
        "release_notes_verified": release_notes_checked,
        "latest_json_notes_verified": latest_json_notes_checked,
        "all_launch_backend_sources_bundled_sidecar": all(
            source == "bundled-sidecar"
            for source in launch_backend_sources.values()
        ),
        "all_launch_port_modes_auto": all(
            port_mode == "auto"
            for port_mode in launch_port_modes.values()
        ),
        "all_launch_desktop_metadata_present": all(
            all(metadata.get(key) for key in ("desktop_version", "desktop_platform", "desktop_arch"))
            for metadata in launch_desktop_metadata.values()
        ),
    }
    return {
        "required_launch_labels": sorted_required_launch_labels,
        "required_stale_backend_rejection_labels": sorted_required_stale_labels,
        "release_state": {
            "repo": repo,
            "tag": release_tag,
            "url": release_url,
            "is_public": release_is_public,
            "is_draft": is_draft,
            "is_prerelease": is_prerelease,
            "public_required": require_public,
            "latest_checked": latest_release is not None,
            "latest_required": require_latest,
            "latest_matches_tag": latest_matches_tag,
            "latest_tag": latest_tag,
            "latest_url": latest_url,
        },
        "checks": checks,
        "ready_for_public_download": all(value is True for value in checks.values()),
        "launch_backend_sources": {
            label: launch_backend_sources[label]
            for label in sorted(launch_backend_sources)
        },
        "launch_port_modes": {
            label: launch_port_modes[label]
            for label in sorted(launch_port_modes)
        },
        "launch_desktop_metadata": {
            label: launch_desktop_metadata[label]
            for label in sorted(launch_desktop_metadata)
        },
        "stale_backend_rejections": {
            label: stale_backend_rejections[label]
            for label in sorted(stale_backend_rejections)
        },
        "checksum_manifest": {
            "required_assets": sorted_required_checksum_assets,
            "verified_assets": sorted_checksum_verified_assets,
        },
    }


def require_checksum_verified_assets(
    checksum_manifest: dict[str, Any] | None,
    required_assets: list[str],
) -> None:
    required = sorted(set(required_assets))
    if not required:
        return
    if not isinstance(checksum_manifest, dict):
        raise ValueError("Missing checksum manifest verification for downloaded installer assets")
    verified_assets = checksum_manifest.get("verified_assets")
    if not isinstance(verified_assets, list):
        raise ValueError("Checksum manifest verification did not report verified_assets")
    verified = {asset for asset in verified_assets if isinstance(asset, str)}
    missing = [asset for asset in required if asset not in verified]
    if missing:
        raise ValueError(
            "Missing checksum verification for downloaded installer asset(s): "
            + ", ".join(missing)
        )


def release_view_command(tag: str | None, repo: str | None) -> list[str]:
    args = ["release", "view"]
    if tag:
        args.append(tag)
    args.extend(["--json", "assets,body,isDraft,isPrerelease,name,tagName,url"])
    return gh_command(args, repo=repo)


def require_public_release(release: dict[str, Any]) -> None:
    tag = release.get("tagName") or "<unknown>"
    if release.get("isDraft") is True:
        raise ValueError(f"GitHub release {tag} is still a draft")
    if release.get("isPrerelease") is True:
        raise ValueError(f"GitHub release {tag} is still marked as a prerelease")


def release_download_command(
    tag: str,
    destination: Path,
    patterns: list[str],
    repo: str | None,
) -> list[str]:
    args = ["release", "download", tag, "--dir", str(destination), "--clobber"]
    for pattern in patterns:
        args.extend(["--pattern", pattern])
    return gh_command(args, repo=repo)


def verify_github_release(
    *,
    tag: str | None = None,
    repo: str | None = None,
    expected_version: str | None = None,
    sample_platform: str = "darwin-aarch64",
    verify_dmg_download: bool | None = None,
    launch_dmg_app: bool = False,
    verify_dmg_installed_copy: bool = False,
    verify_macos_gatekeeper: bool = False,
    require_latest: bool = False,
    require_public: bool = False,
    verify_linux_installers: bool = False,
    launch_linux_appimage: bool = False,
    launch_linux_packages: bool = False,
    verify_windows_installer: bool = False,
    launch_windows_msi: bool = False,
    launch_windows_nsis: bool = False,
    launch_timeout: float = 30.0,
) -> dict[str, Any]:
    release = run_json(release_view_command(tag, repo))
    release_tag = release.get("tagName")
    if not isinstance(release_tag, str) or not release_tag:
        raise ValueError("GitHub release metadata is missing tagName")
    if require_public:
        require_public_release(release)
    latest_release = (
        verify_github_release_is_latest(release_tag, repo) if require_latest else None
    )
    should_verify_dmg = platform.system() == "Darwin" if verify_dmg_download is None else verify_dmg_download

    with tempfile.TemporaryDirectory(prefix="cc-branch-release-canary-") as tmp:
        release_dir = Path(tmp)
        required_checksum_assets: list[str] = []
        assets_json = release_dir / "assets.json"
        assets_json.write_text(json.dumps(release), encoding="utf-8")
        available_assets, asset_sizes = parse_assets_json(assets_json)

        run(release_download_command(release_tag, release_dir, ["latest.json", "SHA256SUMS"], repo))
        latest_path = release_dir / "latest.json"
        latest_json = json.loads(latest_path.read_text(encoding="utf-8"))
        sample_asset = selected_platform_asset(latest_json, sample_platform)
        platform_assets = selected_latest_platform_assets(latest_json)
        macos_updater_assets = selected_macos_updater_assets(latest_json)
        canary_downloads = list(
            dict.fromkeys(
                [
                    *macos_updater_assets,
                    *[f"{asset}.sig" for asset in platform_assets],
                ]
            )
        )
        run(
            release_download_command(
                release_tag,
                release_dir,
                canary_downloads,
                repo,
            )
        )

        canary = verify_release_dir(
            release_dir,
            sample_asset=sample_asset,
            expected_version=expected_version,
            available_assets=available_assets,
            asset_sizes=asset_sizes,
            release_notes_body=str(release.get("body") or ""),
            repo=repo,
            tag=release_tag,
        )
        dmg_verification = None
        macos_dmg_verifications = None
        if should_verify_dmg:
            dmgs = macos_dmg_assets(available_assets)
            dmg_assets = list(dmgs.values())
            run(release_download_command(release_tag, release_dir, dmg_assets, repo))
            required_checksum_assets.extend(dmg_assets)
            launch_label = (
                "intel" if sample_platform == "darwin-x86_64" else "apple_silicon"
            )
            macos_dmg_verifications = {
                label: verify_macos_dmg_asset(
                    release_dir / asset,
                    launch_app=launch_dmg_app and label == launch_label,
                    verify_installed_copy=verify_dmg_installed_copy and label == launch_label,
                    verify_stale_backend_rejection=launch_dmg_app and label == launch_label,
                    verify_gatekeeper_check=verify_macos_gatekeeper,
                    expected_version=expected_version,
                    launch_timeout=launch_timeout,
                )
                for label, asset in dmgs.items()
            }
            dmg_verification = macos_dmg_verifications["apple_silicon"]
        linux_verification = None
        if verify_linux_installers:
            linux_assets = [
                selected_download_asset(available_assets, "Ubuntu/Debian package"),
                selected_download_asset(available_assets, "Fedora/RHEL package"),
                selected_download_asset(available_assets, "Linux AppImage"),
            ]
            run(release_download_command(release_tag, release_dir, linux_assets, repo))
            required_checksum_assets.extend(linux_assets)
            linux_verification = verify_platform_installers(
                release_dir,
                "linux",
                expected_version=expected_version,
                launch_appimage=launch_linux_appimage,
                launch_linux_packages=launch_linux_packages,
                launch_timeout=launch_timeout,
            )

        windows_verification = None
        if verify_windows_installer:
            windows_assets = [
                selected_download_asset(available_assets, "Windows MSI"),
                selected_download_asset(available_assets, "Windows NSIS setup"),
            ]
            run(release_download_command(release_tag, release_dir, windows_assets, repo))
            required_checksum_assets.extend(windows_assets)
            windows_verification = verify_platform_installers(
                release_dir,
                "windows",
                expected_version=expected_version,
                launch_windows_msi=launch_windows_msi,
                launch_windows_nsis=launch_windows_nsis,
                launch_timeout=launch_timeout,
            )
        checksum_manifest = None
        download_assets = canary.get("download_assets") if isinstance(canary, dict) else None
        summary_required_checksum_assets: list[str] = []
        if isinstance(download_assets, dict):
            checksum_manifest = validate_checksum_manifest(
                release_dir,
                download_assets=download_assets,
            )
            require_checksum_verified_assets(checksum_manifest, required_checksum_assets)
            summary_required_checksum_assets = required_checksum_assets

    result = {
        "ok": True,
        "repo": repo,
        "tag": release_tag,
        "name": release.get("name"),
        "url": release.get("url"),
        "isDraft": release.get("isDraft"),
        "isPrerelease": release.get("isPrerelease"),
        "latest": latest_release,
        "sample_platform": sample_platform,
        "canary": canary,
        "dmg": dmg_verification,
        "macos_dmgs": macos_dmg_verifications,
        "linux": linux_verification,
        "windows": windows_verification,
        "checksum_manifest": checksum_manifest,
        "required_checksum_assets": sorted(set(summary_required_checksum_assets)),
    }
    launch_backend_sources = collect_launch_backend_sources(result)
    required_launch_labels: list[str] = []
    required_stale_labels: list[str] = []
    if launch_dmg_app:
        label = "macos.intel" if sample_platform == "darwin-x86_64" else "macos.apple_silicon"
        required_launch_labels.append(label)
        required_stale_labels.append(label)
    if verify_dmg_installed_copy:
        label = "macos.intel" if sample_platform == "darwin-x86_64" else "macos.apple_silicon"
        required_launch_labels.append(f"{label}.installed_copy")
    if launch_linux_appimage:
        required_launch_labels.append("linux.appimage")
        required_stale_labels.append("linux.appimage")
    if launch_linux_packages:
        required_launch_labels.extend(["linux.deb", "linux.rpm"])
        required_stale_labels.extend(["linux.deb", "linux.rpm"])
    if launch_windows_msi:
        required_launch_labels.append("windows.msi")
        required_stale_labels.append("windows.msi")
    if launch_windows_nsis:
        required_launch_labels.append("windows.nsis")
        required_stale_labels.append("windows.nsis")
    require_launch_backend_sources(launch_backend_sources, required_launch_labels)
    result["launch_backend_sources"] = launch_backend_sources
    launch_desktop_metadata = collect_launch_desktop_metadata(result)
    require_launch_desktop_metadata(
        launch_desktop_metadata,
        required_launch_labels,
        expected_version=expected_version,
    )
    result["launch_desktop_metadata"] = launch_desktop_metadata
    launch_port_modes = collect_launch_port_modes(result)
    require_launch_port_modes(launch_port_modes, required_launch_labels)
    result["launch_port_modes"] = launch_port_modes
    stale_backend_rejections = collect_stale_backend_rejections(result)
    require_stale_backend_rejections(stale_backend_rejections, required_stale_labels)
    result["stale_backend_rejections"] = stale_backend_rejections
    result["verification_summary"] = build_verification_summary(
        repo=repo,
        release_tag=release_tag,
        release_url=release.get("url") if isinstance(release.get("url"), str) else None,
        is_draft=release.get("isDraft") if isinstance(release.get("isDraft"), bool) else None,
        is_prerelease=release.get("isPrerelease") if isinstance(release.get("isPrerelease"), bool) else None,
        latest_release=latest_release,
        require_latest=require_latest,
        require_public=require_public,
        required_launch_labels=required_launch_labels,
        required_stale_labels=required_stale_labels,
        launch_backend_sources=launch_backend_sources,
        launch_desktop_metadata=launch_desktop_metadata,
        launch_port_modes=launch_port_modes,
        stale_backend_rejections=stale_backend_rejections,
        required_checksum_assets=result["required_checksum_assets"],
        checksum_verified_assets=(
            checksum_manifest.get("verified_assets")
            if isinstance(checksum_manifest, dict)
            and isinstance(checksum_manifest.get("verified_assets"), list)
            else []
        ),
        release_notes_checked=(
            isinstance(canary.get("release_notes"), dict)
            and canary["release_notes"].get("checked") is True
        ),
        latest_json_notes_checked=(
            isinstance(canary.get("latest_notes"), dict)
            and canary["latest_notes"].get("checked") is True
        ),
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", nargs="?", help="release tag; omit to verify GitHub latest")
    parser.add_argument("--repo", default=None, help="GitHub repository, for example owner/name")
    parser.add_argument("--expected-version", default=None)
    parser.add_argument("--sample-platform", default="darwin-aarch64")
    parser.add_argument(
        "--launch-dmg-app",
        action="store_true",
        help="after downloading the macOS DMG, launch its app and verify the backend starts",
    )
    parser.add_argument(
        "--verify-dmg-installed-copy",
        action="store_true",
        help="copy the macOS app out of the downloaded DMG and launch that installed copy",
    )
    parser.add_argument(
        "--verify-macos-gatekeeper",
        action="store_true",
        help="validate the downloaded macOS DMG notarization ticket and Gatekeeper acceptance",
    )
    parser.add_argument(
        "--require-latest",
        action="store_true",
        help="fail unless GitHub latest points to the release tag being verified",
    )
    parser.add_argument(
        "--require-public",
        action="store_true",
        help="fail if the release is still draft or marked as a prerelease",
    )
    parser.add_argument(
        "--verify-linux-installers",
        action="store_true",
        help="download and inspect the recommended Linux .deb, .rpm, and .AppImage assets",
    )
    parser.add_argument(
        "--launch-linux-appimage",
        action="store_true",
        help="after downloading the Linux AppImage, extract and launch it to verify the backend starts",
    )
    parser.add_argument(
        "--launch-linux-packages",
        action="store_true",
        help="extract the Linux DEB/RPM packages and launch their packaged app binaries",
    )
    parser.add_argument(
        "--verify-windows-installer",
        action="store_true",
        help="download and inspect the recommended Windows MSI and NSIS setup assets",
    )
    parser.add_argument(
        "--launch-windows-msi",
        action="store_true",
        help="after downloading the Windows MSI, extract and launch it to verify the backend starts",
    )
    parser.add_argument(
        "--launch-windows-nsis",
        action="store_true",
        help="after downloading the Windows NSIS setup EXE, extract and launch it to verify the backend starts",
    )
    parser.add_argument(
        "--launch-timeout",
        type=float,
        default=30.0,
        help="seconds to wait for launched desktop installers to report bundled backend startup",
    )
    dmg_group = parser.add_mutually_exclusive_group()
    dmg_group.add_argument(
        "--verify-dmg",
        dest="verify_dmg_download",
        action="store_true",
        default=None,
        help="download and mount the recommended macOS Apple Silicon DMG",
    )
    dmg_group.add_argument(
        "--skip-dmg",
        dest="verify_dmg_download",
        action="store_false",
        help="skip macOS DMG content verification",
    )
    args = parser.parse_args(argv)

    result = verify_github_release(
        tag=args.tag,
        repo=args.repo,
        expected_version=args.expected_version,
        sample_platform=args.sample_platform,
        verify_dmg_download=args.verify_dmg_download,
        launch_dmg_app=args.launch_dmg_app,
        verify_dmg_installed_copy=args.verify_dmg_installed_copy,
        verify_macos_gatekeeper=args.verify_macos_gatekeeper,
        require_latest=args.require_latest,
        require_public=args.require_public,
        verify_linux_installers=args.verify_linux_installers,
        launch_linux_appimage=args.launch_linux_appimage,
        launch_linux_packages=args.launch_linux_packages,
        verify_windows_installer=args.verify_windows_installer,
        launch_windows_msi=args.launch_windows_msi,
        launch_windows_nsis=args.launch_windows_nsis,
        launch_timeout=args.launch_timeout,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
