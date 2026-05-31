#!/usr/bin/env python3
"""Verify published desktop release assets and updater metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import re
import tarfile
from pathlib import Path
from urllib.parse import quote
from urllib.parse import unquote, urlparse

REQUIRED_PLATFORMS = (
    "darwin-aarch64",
    "darwin-x86_64",
    "windows-x86_64",
    "linux-x86_64",
)

REQUIRED_DOWNLOAD_ASSETS = (
    ("macOS Apple Silicon DMG", r"aarch64.*\.dmg$"),
    ("macOS Intel DMG", r"x64.*\.dmg$"),
    ("Windows MSI", r"x64_en-US\.msi$"),
    ("Windows NSIS setup", r"x64-setup\.exe$"),
    ("Ubuntu/Debian package", r"amd64\.deb$"),
    ("Fedora/RHEL package", r"x86_64\.rpm$"),
    ("Linux AppImage", r"amd64\.AppImage$"),
)

CHECKSUMS_ASSET_NAME = "SHA256SUMS"

AUXILIARY_ASSET_SUFFIXES = (
    ".sig",
    ".blockmap",
    ".sha256",
    ".sha512",
)


def is_auxiliary_release_asset(name: str) -> bool:
    return name == CHECKSUMS_ASSET_NAME or name.endswith(AUXILIARY_ASSET_SUFFIXES)


def recommended_download_asset_names(available_assets: set[str]) -> list[str]:
    return sorted(name for name in available_assets if not is_auxiliary_release_asset(name))


def asset_name_has_version(name: str, expected_version: str) -> bool:
    return re.search(rf"(?<!\d){re.escape(expected_version)}(?!\d)", name) is not None


def asset_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(unquote(parsed.path)).name
    if not name:
        raise ValueError(f"Asset URL has no file name: {url}")
    return name


def expected_release_asset_url(repo: str, tag: str, asset_name: str) -> str:
    return f"https://github.com/{repo}/releases/download/{tag}/{quote(asset_name)}"


def validate_latest_json(
    data: dict,
    *,
    available_assets: set[str] | None = None,
    asset_sizes: dict[str, int] | None = None,
    expected_repo: str | None = None,
    expected_tag: str | None = None,
) -> dict[str, str]:
    if not isinstance(data.get("version"), str) or not data["version"]:
        raise ValueError("latest.json is missing a non-empty version")
    platforms = data.get("platforms")
    if not isinstance(platforms, dict):
        raise ValueError("latest.json is missing platforms")

    platform_assets: dict[str, str] = {}
    missing = [platform for platform in REQUIRED_PLATFORMS if platform not in platforms]
    if missing:
        raise ValueError(f"latest.json is missing platform entries: {', '.join(missing)}")

    for platform, item in platforms.items():
        if not isinstance(item, dict):
            raise ValueError(f"Platform {platform} is not an object")
        url = item.get("url")
        signature = item.get("signature")
        if not isinstance(url, str) or not url:
            raise ValueError(f"Platform {platform} is missing url")
        if not isinstance(signature, str) or not signature.strip():
            raise ValueError(f"Platform {platform} is missing signature")
        asset_name = asset_name_from_url(url)
        platform_assets[platform] = asset_name
        if available_assets is not None and asset_name not in available_assets:
            raise ValueError(f"Platform {platform} references missing release asset: {asset_name}")
        if asset_sizes is not None and asset_sizes.get(asset_name, 0) <= 0:
            raise ValueError(f"Platform {platform} references empty release asset: {asset_name}")
        if expected_repo is not None and expected_tag is not None:
            expected_url = expected_release_asset_url(expected_repo, expected_tag, asset_name)
            if url != expected_url:
                raise ValueError(
                    f"Platform {platform} URL does not match expected release URL: "
                    f"{url} != {expected_url}"
                )
    return platform_assets


def validate_download_assets(
    available_assets: set[str],
    *,
    expected_version: str | None = None,
    asset_sizes: dict[str, int] | None = None,
) -> dict[str, str]:
    """Verify the user-facing recommended installer assets are present."""
    matches: dict[str, str] = {}
    candidate_assets = recommended_download_asset_names(available_assets)
    for label, pattern in REQUIRED_DOWNLOAD_ASSETS:
        matching_assets = [name for name in candidate_assets if re.search(pattern, name)]
        if not matching_assets:
            raise ValueError(f"Release is missing recommended download asset: {label} ({pattern})")
        if expected_version is not None:
            wrong_version_assets = [
                asset for asset in matching_assets if not asset_name_has_version(asset, expected_version)
            ]
            if wrong_version_assets:
                raise ValueError(
                    f"Release recommended download asset does not match expected version "
                    f"{expected_version}: {label} ({', '.join(wrong_version_assets)})"
                )
        if len(matching_assets) > 1:
            raise ValueError(
                f"Release has multiple recommended download assets for {label}: "
                f"{', '.join(matching_assets)}"
            )
        asset = next(
            (
                name
                for name in matching_assets
                if expected_version is None or asset_name_has_version(name, expected_version)
            ),
            matching_assets[0],
        )
        if asset_sizes is not None:
            empty_assets = [
                name for name in matching_assets if asset_sizes.get(name, 0) <= 0
            ]
            if empty_assets:
                raise ValueError(
                    f"Release recommended download asset is empty: {label} ({', '.join(empty_assets)})"
                )
        matches[label] = asset
    return matches


def parse_assets_json(path: Path) -> tuple[set[str], dict[str, int]]:
    """Read gh release asset metadata from `gh release view --json assets`."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    assets = raw.get("assets") if isinstance(raw, dict) else raw
    if not isinstance(assets, list):
        raise ValueError(f"Release asset metadata is not a list: {path}")

    names: set[str] = set()
    sizes: dict[str, int] = {}
    for item in assets:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name:
            continue
        names.add(name)
        try:
            sizes[name] = int(item.get("size") or 0)
        except (TypeError, ValueError):
            sizes[name] = 0
    return names, sizes


def validate_release_notes(
    body: str,
    *,
    download_assets: dict[str, str],
    repo: str | None = None,
    tag: str | None = None,
) -> dict:
    """Verify the GitHub release body gives users direct installer links."""
    if not body.strip():
        raise ValueError("Release notes body is empty")

    required_phrases = (
        "Download the right installer",
        "bundled backend starts automatically",
        "No separate Python install is required for the desktop app.",
        "Source code zip or tar.gz",
        "drag CC Branch to Applications",
        "run the MSI or setup EXE",
        "run the AppImage directly",
        "Copy report",
        "attach the report when filing an issue",
        "Local backend ready",
        "Add project",
        "local directory or SSH workspace",
    )
    for phrase in required_phrases:
        if phrase not in body:
            raise ValueError(f"Release notes are missing required copy: {phrase}")

    if "download the installer for your platform from the table above" not in body:
        raise ValueError(
            "Release notes must direct reinstall attempts to the current release download table"
        )
    forbidden_reinstall_copy = (
        "download the latest installer",
        "download latest installer",
    )
    lowered_body = body.lower()
    for phrase in forbidden_reinstall_copy:
        if phrase in lowered_body:
            raise ValueError(
                "Release notes must not send failed reinstall attempts to the latest release instead of the current release"
            )

    for label, asset in sorted(download_assets.items()):
        if asset not in body:
            raise ValueError(f"Release notes are missing recommended download asset: {label} ({asset})")
        if repo is not None and tag is not None:
            url = f"https://github.com/{repo}/releases/download/{tag}/{quote(asset)}"
            if url not in body:
                raise ValueError(f"Release notes are missing direct download link: {label} ({url})")

    if repo is not None and tag is not None:
        checksum_url = expected_release_asset_url(repo, tag, CHECKSUMS_ASSET_NAME)
        if CHECKSUMS_ASSET_NAME not in body or checksum_url not in body:
            raise ValueError(
                f"Release notes are missing checksum manifest link: {CHECKSUMS_ASSET_NAME} ({checksum_url})"
            )

        latest_download_links = sorted(
            unquote(asset)
            for asset in re.findall(
                rf"https://github\.com/{re.escape(repo)}/releases/latest/download/([^\)\s]+)",
                body,
            )
        )
        if latest_download_links:
            raise ValueError(
                "Release notes link download asset(s) outside the current release: "
                + ", ".join(f"latest/{asset}" for asset in latest_download_links)
            )

        linked_release_downloads = re.findall(
            rf"https://github\.com/{re.escape(repo)}/releases/download/([^/\)\s]+)/([^\)\s]+)",
            body,
        )
        non_current_release_links = sorted(
            f"{linked_tag}/{unquote(asset)}"
            for linked_tag, asset in linked_release_downloads
            if linked_tag != tag
        )
        if non_current_release_links:
            raise ValueError(
                "Release notes link download asset(s) outside the current release: "
                + ", ".join(non_current_release_links)
            )

        direct_download_prefix = f"https://github.com/{repo}/releases/download/{tag}/"
        linked_assets = {
            unquote(match)
            for match in re.findall(
                re.escape(direct_download_prefix) + r"([^\)\s]+)",
                body,
            )
        }
        auxiliary_assets = sorted(
            asset
            for asset in linked_assets
            if is_auxiliary_release_asset(asset) and asset != CHECKSUMS_ASSET_NAME
        )
        if auxiliary_assets:
            raise ValueError(
                "Release notes link auxiliary release asset(s) as user downloads: "
                + ", ".join(auxiliary_assets)
            )
        recommended_assets = set(download_assets.values())
        support_assets = {CHECKSUMS_ASSET_NAME}
        non_recommended_assets = sorted(linked_assets - recommended_assets - support_assets)
        if non_recommended_assets:
            raise ValueError(
                "Release notes link non-recommended release asset(s) as user downloads: "
                + ", ".join(non_recommended_assets)
            )

    table_rows = [
        line
        for line in body.splitlines()
        if line.lstrip().startswith("|") and line.rstrip().endswith("|")
    ]
    for label, asset in sorted(download_assets.items()):
        expected_url = (
            f"https://github.com/{repo}/releases/download/{tag}/{quote(asset)}"
            if repo is not None and tag is not None
            else None
        )
        if not any(
            label in row
            and asset in row
            and (expected_url is None or expected_url in row)
            for row in table_rows
        ):
            raise ValueError(
                f"Release notes download table is missing recommended asset: {label} ({asset})"
            )

    return {"checked": True, "assets": sorted(download_assets)}


def validate_checksum_manifest(
    release_dir: Path,
    *,
    download_assets: dict[str, str],
) -> dict:
    manifest_path = release_dir / CHECKSUMS_ASSET_NAME
    if not manifest_path.exists() or manifest_path.stat().st_size == 0:
        raise ValueError(f"Release checksum manifest is missing or empty: {CHECKSUMS_ASSET_NAME}")

    entries: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line:
            continue
        match = re.fullmatch(r"([a-fA-F0-9]{64})\s+\*?(.+)", line)
        if match is None:
            raise ValueError(
                f"Release checksum manifest has invalid line {line_number}: {raw_line}"
            )
        digest, asset = match.groups()
        if "/" in asset or "\\" in asset:
            raise ValueError(
                f"Release checksum manifest entry must be an asset name, not a path: {asset}"
            )
        entries[asset] = digest.lower()

    missing = []
    verified_assets = []
    for label, asset in sorted(download_assets.items()):
        if asset not in entries:
            missing.append(f"{label} ({asset})")
            continue
        asset_path = release_dir / asset
        if asset_path.exists():
            actual_digest = hashlib.sha256(asset_path.read_bytes()).hexdigest()
            expected_digest = entries[asset]
            if actual_digest != expected_digest:
                raise ValueError(
                    f"Release checksum manifest SHA256 mismatch for {label} ({asset}): "
                    f"{actual_digest} != {expected_digest}"
                )
            verified_assets.append(asset)
    if missing:
        raise ValueError(
            "Release checksum manifest is missing recommended download asset(s): "
            + ", ".join(missing)
        )

    return {
        "checked": True,
        "asset": CHECKSUMS_ASSET_NAME,
        "covered_assets": sorted(download_assets.values()),
        "verified_assets": sorted(verified_assets),
    }


def normalize_release_notes(body: str) -> str:
    return "\n".join(line.rstrip() for line in body.strip().splitlines())


def verify_app_tarball_contains_backend(
    path: Path,
    *,
    expected_version: str | None = None,
) -> dict:
    """Verify a macOS updater tarball contains the bundled backend sidecar."""
    if not path.name.endswith(".app.tar.gz"):
        return {"checked": False, "reason": "sample asset is not a macOS app tarball"}

    try:
        with tarfile.open(path, "r:gz") as archive:
            members = archive.getmembers()
            app_roots = sorted(
                {
                    member.name.split("/", 1)[0]
                    for member in members
                    if ".app/" in member.name
                    and member.name.split("/", 1)[0].endswith(".app")
                }
            )
            if app_roots != ["CC Branch.app"]:
                raise ValueError(
                    "Canary macOS app tarball must contain exactly CC Branch.app; "
                    f"found: {', '.join(app_roots) or '<none>'}"
                )
            info_members = [
                member
                for member in members
                if member.isfile() and member.name.endswith(".app/Contents/Info.plist")
            ]
            if len(info_members) > 1:
                raise ValueError("Canary macOS app tarball contains multiple Contents/Info.plist files")
            bundle_version = None
            if info_members:
                info_file = archive.extractfile(info_members[0])
                if info_file is not None:
                    info = plistlib.load(info_file)
                    if isinstance(info, dict):
                        version_value = info.get("CFBundleShortVersionString")
                        if isinstance(version_value, str):
                            bundle_version = version_value
    except tarfile.TarError as error:
        raise ValueError(f"Canary app tarball is not readable: {path.name}") from error

    if expected_version is not None:
        if bundle_version is None:
            raise ValueError("Canary macOS app tarball is missing bundle version in Info.plist")
        if bundle_version != expected_version:
            raise ValueError(
                f"Canary macOS app tarball version {bundle_version!r} "
                f"does not match expected {expected_version!r}"
            )

    backend_members = [
        member
        for member in members
        if member.isfile()
        and member.name.endswith(".app/Contents/MacOS/cc-branch-backend")
        and member.size > 0
    ]
    if not backend_members:
        raise ValueError(
            "Canary macOS app tarball is missing Contents/MacOS/cc-branch-backend"
        )
    if len(backend_members) > 1:
        raise ValueError(
            "Canary macOS app tarball contains multiple Contents/MacOS/cc-branch-backend files"
        )

    backend = backend_members[0]
    if backend.mode & 0o111 == 0:
        raise ValueError("Canary backend sidecar is present but is not executable")

    main_binary_members = [
        member
        for member in members
        if member.isfile()
        and member.name.endswith(".app/Contents/MacOS/cc-branch")
        and member.size > 0
    ]
    if not main_binary_members:
        raise ValueError("Canary macOS app tarball is missing Contents/MacOS/cc-branch")
    if len(main_binary_members) > 1:
        raise ValueError("Canary macOS app tarball contains multiple Contents/MacOS/cc-branch files")

    main_binary = main_binary_members[0]
    if main_binary.mode & 0o111 == 0:
        raise ValueError("Canary app binary is present but is not executable")

    return {
        "checked": True,
        "app_bundle": "CC Branch.app",
        "app_binary_path": main_binary.name,
        "app_binary_size": main_binary.size,
        "backend_path": backend.name,
        "backend_size": backend.size,
        "bundle_version": bundle_version,
    }


def verify_macos_updater_tarballs(
    release_dir: Path,
    platform_assets: dict[str, str],
    *,
    platform_signatures: dict[str, str] | None = None,
    expected_version: str | None = None,
) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for platform, asset in sorted(platform_assets.items()):
        if not asset.endswith(".app.tar.gz"):
            continue
        asset_path = release_dir / asset
        sig_path = release_dir / f"{asset}.sig"
        if not asset_path.exists() or asset_path.stat().st_size == 0:
            raise ValueError(f"Canary macOS updater asset is missing or empty: {asset}")
        if not sig_path.exists() or not sig_path.read_text(encoding="utf-8").strip():
            raise ValueError(f"Canary macOS updater signature is missing or empty: {sig_path.name}")
        expected_signature = (
            platform_signatures.get(platform) if platform_signatures is not None else None
        )
        actual_signature = sig_path.read_text(encoding="utf-8").strip()
        if expected_signature is not None and actual_signature != expected_signature:
            raise ValueError(
                f"Canary macOS updater signature for {asset} does not match latest.json"
            )
        results[asset] = {
            "platform": platform,
            **verify_app_tarball_contains_backend(
                asset_path,
                expected_version=expected_version,
            ),
        }
    return results


def verify_platform_signature_files(
    release_dir: Path,
    platform_assets: dict[str, str],
    platform_signatures: dict[str, str],
) -> dict[str, dict]:
    """Verify every latest.json platform signature matches its release .sig asset."""
    results: dict[str, dict] = {}
    for platform, asset in sorted(platform_assets.items()):
        sig_path = release_dir / f"{asset}.sig"
        if not sig_path.exists() or sig_path.stat().st_size == 0:
            raise ValueError(f"Canary updater signature is missing or empty: {sig_path.name}")
        actual_signature = sig_path.read_text(encoding="utf-8").strip()
        expected_signature = platform_signatures.get(platform, "").strip()
        if not actual_signature:
            raise ValueError(f"Canary updater signature is missing or empty: {sig_path.name}")
        if expected_signature and actual_signature != expected_signature:
            raise ValueError(
                f"Canary updater signature for {asset} ({platform}) does not match latest.json"
            )
        results[platform] = {
            "asset": asset,
            "signature_file": sig_path.name,
            "checked": True,
        }
    return results


def verify_release_dir(
    release_dir: Path,
    *,
    sample_asset: str | None = None,
    expected_version: str | None = None,
    available_assets: set[str] | None = None,
    asset_sizes: dict[str, int] | None = None,
    release_notes_body: str | None = None,
    repo: str | None = None,
    tag: str | None = None,
) -> dict:
    latest_path = release_dir / "latest.json"
    if not latest_path.exists():
        raise ValueError(f"Missing latest.json in {release_dir}")
    data = json.loads(latest_path.read_text(encoding="utf-8"))
    platform_signatures = {
        platform: item.get("signature", "")
        for platform, item in data.get("platforms", {}).items()
        if isinstance(item, dict) and isinstance(item.get("signature"), str)
    }
    platform_assets = validate_latest_json(
        data,
        available_assets=available_assets,
        asset_sizes=asset_sizes,
        expected_repo=repo,
        expected_tag=tag,
    )
    download_assets = (
        validate_download_assets(
            available_assets,
            expected_version=expected_version,
            asset_sizes=asset_sizes,
        )
        if available_assets is not None
        else None
    )
    release_notes = (
        validate_release_notes(
            release_notes_body,
            download_assets=download_assets,
            repo=repo,
            tag=tag,
        )
        if release_notes_body is not None and download_assets is not None
        else None
    )
    latest_notes = None
    checksum_manifest = None
    if download_assets is not None and repo is not None and tag is not None:
        try:
            latest_notes = validate_release_notes(
                data.get("notes", ""),
                download_assets=download_assets,
                repo=repo,
                tag=tag,
            )
        except ValueError as error:
            raise ValueError(f"latest.json notes failed validation: {error}") from error
        if release_notes_body is not None and normalize_release_notes(data.get("notes", "")) != normalize_release_notes(release_notes_body):
            raise ValueError("latest.json notes do not match release body")
    if (
        download_assets is not None
        and available_assets is not None
        and CHECKSUMS_ASSET_NAME in available_assets
    ):
        checksum_manifest = validate_checksum_manifest(
            release_dir,
            download_assets=download_assets,
        )
    if expected_version is not None and data["version"] != expected_version:
        raise ValueError(
            f"latest.json version {data['version']!r} does not match expected {expected_version!r}"
        )

    macos_updater_assets = verify_macos_updater_tarballs(
        release_dir,
        platform_assets,
        platform_signatures=platform_signatures,
        expected_version=expected_version,
    )
    platform_signature_files = verify_platform_signature_files(
        release_dir,
        platform_assets,
        platform_signatures,
    )

    sample = sample_asset or platform_assets["darwin-aarch64"]
    if sample not in platform_assets.values():
        raise ValueError(f"Canary sample asset is not referenced by latest.json: {sample}")
    if sample in macos_updater_assets:
        sample_path = release_dir / sample
        sample_content = macos_updater_assets[sample]
    else:
        sample_path = release_dir / sample
        sig_path = release_dir / f"{sample}.sig"
        if not sample_path.exists() or sample_path.stat().st_size == 0:
            raise ValueError(f"Canary asset is missing or empty: {sample}")
        if not sig_path.exists() or not sig_path.read_text(encoding="utf-8").strip():
            raise ValueError(f"Canary signature is missing or empty: {sig_path.name}")
        sample_content = verify_app_tarball_contains_backend(
            sample_path,
            expected_version=expected_version,
        )

    return {
        "ok": True,
        "repo": repo,
        "tag": tag,
        "version": data["version"],
        "platforms": sorted(platform_assets),
        "sample_asset": sample,
        "sample_size": sample_path.stat().st_size,
        "sample_content": sample_content,
        "macos_updater_assets": macos_updater_assets,
        "platform_signature_files": platform_signature_files,
        "download_assets": download_assets,
        "checksum_manifest": checksum_manifest,
        "release_notes": release_notes,
        "latest_notes": latest_notes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--sample-asset", default=None)
    parser.add_argument("--expected-version", default=None)
    parser.add_argument(
        "--assets-file",
        type=Path,
        default=None,
        help="optional newline-delimited release asset manifest",
    )
    parser.add_argument(
        "--assets-json",
        type=Path,
        default=None,
        help="optional gh release view --json assets output with names and sizes",
    )
    parser.add_argument(
        "--release-body-file",
        type=Path,
        default=None,
        help="optional GitHub release body markdown file to verify",
    )
    parser.add_argument("--repo", default=None, help="repository for direct download links")
    parser.add_argument("--tag", default=None, help="release tag for direct download links")
    args = parser.parse_args(argv)

    available_assets = None
    asset_sizes = None
    if args.assets_file is not None:
        available_assets = {
            line.strip()
            for line in args.assets_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    if args.assets_json is not None:
        available_assets, asset_sizes = parse_assets_json(args.assets_json)
    release_notes_body = (
        args.release_body_file.read_text(encoding="utf-8")
        if args.release_body_file is not None
        else None
    )

    result = verify_release_dir(
        args.release_dir,
        sample_asset=args.sample_asset,
        expected_version=args.expected_version,
        available_assets=available_assets,
        asset_sizes=asset_sizes,
        release_notes_body=release_notes_body,
        repo=args.repo,
        tag=args.tag,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
