#!/usr/bin/env python3
"""Verify all release-facing package versions match the release tag."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

VERSION_FILES = {
    "pyproject": ROOT / "pyproject.toml",
    "python_package": ROOT / "cc_branch" / "__init__.py",
    "apps_workspace": ROOT / "apps" / "package.json",
    "web_package": ROOT / "apps" / "web" / "package.json",
    "desktop_package": ROOT / "apps" / "desktop" / "package.json",
    "tauri_config": ROOT / "apps" / "desktop" / "src-tauri" / "tauri.conf.json",
    "cargo_manifest": ROOT / "apps" / "desktop" / "src-tauri" / "Cargo.toml",
    "npm_template": ROOT / "packaging" / "npm" / "package.json",
}


def _read_json_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    version = data.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError(f"{path} is missing a non-empty version")
    return version


def _read_package_lock_version(path: Path, package_key: str) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    packages = data.get("packages")
    if not isinstance(packages, dict):
        raise ValueError(f"{path} is missing a packages table")
    package = packages.get(package_key)
    if not isinstance(package, dict):
        raise ValueError(f"{path} is missing package entry {package_key!r}")
    version = package.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError(f"{path} package {package_key!r} is missing a non-empty version")
    return version


def _read_assignment_version(path: Path, pattern: str) -> str:
    content = path.read_text(encoding="utf-8")
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        raise ValueError(f"{path} does not contain a release version")
    return match.group(1)


def collect_versions() -> dict[str, str]:
    return {
        "pyproject": _read_assignment_version(
            VERSION_FILES["pyproject"],
            r'^version\s*=\s*"([^"]+)"$',
        ),
        "python_package": _read_assignment_version(
            VERSION_FILES["python_package"],
            r'^__version__\s*=\s*"([^"]+)"$',
        ),
        "apps_workspace": _read_json_version(VERSION_FILES["apps_workspace"]),
        "apps_lockfile": _read_json_version(ROOT / "apps" / "package-lock.json"),
        "apps_lockfile_root": _read_package_lock_version(ROOT / "apps" / "package-lock.json", ""),
        "apps_lockfile_desktop": _read_package_lock_version(ROOT / "apps" / "package-lock.json", "desktop"),
        "apps_lockfile_web": _read_package_lock_version(ROOT / "apps" / "package-lock.json", "web"),
        "web_package": _read_json_version(VERSION_FILES["web_package"]),
        "desktop_package": _read_json_version(VERSION_FILES["desktop_package"]),
        "tauri_config": _read_json_version(VERSION_FILES["tauri_config"]),
        "cargo_manifest": _read_assignment_version(
            VERSION_FILES["cargo_manifest"],
            r'^version\s*=\s*"([^"]+)"$',
        ),
        "npm_template": _read_json_version(VERSION_FILES["npm_template"]),
    }


def normalize_expected(value: str, *, require_v_prefix: bool = False) -> str:
    value = value.strip()
    if require_v_prefix and not value.startswith("v"):
        raise ValueError(f"Release tag must start with 'v': {value!r}")
    return value[1:] if value.startswith("v") else value


def require_v_prefixed_tag(value: str) -> str:
    normalize_expected(value, require_v_prefix=True)
    return value.strip()


def verify_versions(expected: str | None = None, *, require_v_prefix: bool = False) -> dict[str, object]:
    normalized_expected = None
    if expected is not None:
        normalized_expected = normalize_expected(expected, require_v_prefix=require_v_prefix)

    versions = collect_versions()
    unique_versions = sorted(set(versions.values()))
    if len(unique_versions) != 1:
        raise ValueError(f"Release versions are inconsistent: {versions}")

    version = unique_versions[0]
    if normalized_expected is not None and version != normalized_expected:
        raise ValueError(f"Release version {version!r} does not match expected {normalized_expected!r}")

    return {"ok": True, "version": version, "files": versions}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", default=None, help="release tag or bare version")
    parser.add_argument(
        "--require-v-prefix",
        action="store_true",
        help="require --expected to be a release tag such as v1.0.2",
    )
    args = parser.parse_args(argv)

    result = verify_versions(args.expected, require_v_prefix=args.require_v_prefix)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
