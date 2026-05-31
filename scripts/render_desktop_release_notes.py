#!/usr/bin/env python3
"""Render desktop release notes with direct installer download links."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

try:
    from scripts.verify_release_canary import (
        REQUIRED_DOWNLOAD_ASSETS,
        CHECKSUMS_ASSET_NAME,
        asset_name_has_version,
        is_auxiliary_release_asset,
    )
except ModuleNotFoundError:
    from verify_release_canary import (
        REQUIRED_DOWNLOAD_ASSETS,
        CHECKSUMS_ASSET_NAME,
        asset_name_has_version,
        is_auxiliary_release_asset,
    )


DOWNLOAD_NOTES = {
    "macOS Apple Silicon DMG": "M1/M2/M3/M4 Macs. Signed and notarized DMG.",
    "macOS Intel DMG": "Older Intel Macs. Signed and notarized DMG.",
    "Windows MSI": "Recommended Windows installer.",
    "Windows NSIS setup": "Alternative Windows installer if you prefer an EXE setup.",
    "Ubuntu/Debian package": "Debian-based Linux distributions.",
    "Fedora/RHEL package": "RPM-based Linux distributions.",
    "Linux AppImage": "Portable Linux build.",
}

DOWNLOAD_ROWS = tuple(
    (label, pattern, DOWNLOAD_NOTES[label])
    for label, pattern in REQUIRED_DOWNLOAD_ASSETS
)


def load_assets(source: Path | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(source, list):
        return source
    raw = json.loads(source.read_text(encoding="utf-8"))
    assets = raw.get("assets") if isinstance(raw, dict) else raw
    if not isinstance(assets, list):
        raise ValueError(f"Release asset metadata is not a list: {source}")
    return [asset for asset in assets if isinstance(asset, dict)]


def expected_version_from_tag(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def select_asset(
    assets: list[dict[str, Any]],
    label: str,
    pattern: str,
    *,
    expected_version: str | None = None,
) -> dict[str, Any]:
    matches = [
        asset
        for asset in assets
        if isinstance(asset.get("name"), str) and re.search(pattern, asset["name"])
        and not is_auxiliary_release_asset(asset["name"])
    ]
    if not matches:
        raise ValueError(f"Release is missing recommended download asset: {label} ({pattern})")
    if expected_version is not None:
        wrong_version_assets = [
            asset["name"]
            for asset in matches
            if not asset_name_has_version(asset["name"], expected_version)
        ]
        if wrong_version_assets:
            raise ValueError(
                f"Release recommended download asset does not match expected version "
                f"{expected_version}: {label} ({', '.join(sorted(wrong_version_assets))})"
            )
    if len(matches) > 1:
        raise ValueError(
            f"Release has multiple recommended download assets for {label}: "
            f"{', '.join(sorted(asset['name'] for asset in matches))}"
        )

    asset = sorted(matches, key=lambda item: item["name"])[0]
    try:
        size = int(asset.get("size") or 0)
    except (TypeError, ValueError):
        size = 0
    if size <= 0:
        raise ValueError(f"Release recommended download asset is empty: {label} ({asset['name']})")
    return asset


def asset_url(repo: str, tag: str, name: str) -> str:
    return f"https://github.com/{repo}/releases/download/{tag}/{quote(name)}"


def format_size(size: Any) -> str:
    try:
        value = int(size)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        return ""
    return f"{value / 1_000_000:.1f} MB"


def render_release_notes(
    *,
    repo: str,
    tag: str,
    assets: Path | list[dict[str, Any]],
) -> str:
    loaded_assets = load_assets(assets)
    expected_version = expected_version_from_tag(tag)
    lines = [
        f"# CC Branch Desktop {tag}",
        "",
        "This desktop build bundles CC Branch and starts its local backend automatically. No separate Python install is required for the desktop app.",
        "",
        "## Download the right installer",
        "",
        "| Your computer | Download | Size | Notes |",
        "| --- | --- | ---: | --- |",
    ]

    for platform, pattern, note in DOWNLOAD_ROWS:
        asset = select_asset(
            loaded_assets,
            platform,
            pattern,
            expected_version=expected_version,
        )
        name = asset["name"]
        lines.append(
            f"| {platform} | [{name}]({asset_url(repo, tag, name)}) | {format_size(asset.get('size'))} | {note} |"
        )

    lines.extend(
        [
            "",
            "## Install and open",
            "",
            "- Do not use GitHub's Source code zip or tar.gz downloads for the desktop app.",
            "- macOS: open the DMG, drag CC Branch to Applications, then launch it from Applications.",
            "- Windows: run the MSI or setup EXE; no terminal or Python install is required.",
            "- Linux: install the DEB/RPM or run the AppImage directly.",
            "",
            "## Verify your download",
            "",
            f"- Optional: compare your installer against [{CHECKSUMS_ASSET_NAME}]({asset_url(repo, tag, CHECKSUMS_ASSET_NAME)}) before opening it.",
            "",
            "## What should work after install",
            "",
            "- Opening CC Branch should show the desktop shell without requiring a terminal.",
            "- On first launch, the app should show Local backend ready. Click Add project to connect a local directory or SSH workspace.",
            "- The bundled backend starts automatically and is verified by the release workflow before this release is published.",
            "- Settings can check for future signed updates using the included `latest.json` metadata.",
            "",
            "## If the app cannot start",
            "",
            "Use the Retry button in the app first. If it still fails, download the installer for your platform from the table above and reinstall. Click Copy report in the startup error panel and attach the report when filing an issue.",
            "",
            "## CLI package",
            "",
            "The Python CLI package is released separately. Until that channel is published, use the source install documented in the repository README.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--assets-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    notes = render_release_notes(
        repo=args.repo,
        tag=args.tag,
        assets=args.assets_json,
    )
    args.output.write_text(notes, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
