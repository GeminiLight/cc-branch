import json
import hashlib
import plistlib
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.verify_release_canary import (
    CHECKSUMS_ASSET_NAME,
    parse_assets_json,
    validate_checksum_manifest,
    validate_download_assets,
    validate_latest_json,
    validate_release_notes,
    recommended_download_asset_names,
    verify_app_tarball_contains_backend,
    verify_release_dir,
)


def release_url(asset: str, tag: str = "v0.1.4") -> str:
    return f"https://github.com/GeminiLight/cc-branch/releases/download/{tag}/{asset}"


def write_app_tarball(
    path: Path,
    *,
    version: str = "0.1.4",
    include_backend: bool = True,
    include_main_binary: bool = True,
    executable_main_binary: bool = True,
    duplicate_main_binary: bool = False,
    duplicate_backend: bool = False,
    duplicate_info_plist: bool = False,
    app_name: str = "CC Branch.app",
) -> None:
    with tarfile.open(path, "w:gz") as archive:
        workdir = path.parent
        info_plist = workdir / "Info.plist"
        info_plist.write_bytes(
            plistlib.dumps({
                "CFBundleShortVersionString": version,
                "CFBundleVersion": version,
            })
        )
        archive.add(info_plist, arcname=f"{app_name}/Contents/Info.plist")
        if duplicate_info_plist:
            archive.add(info_plist, arcname=f"{app_name}/Contents/Info.plist")
        if include_main_binary:
            main = workdir / "cc-branch"
            main.write_bytes(b"app")
            main.chmod(0o755 if executable_main_binary else 0o644)
            archive.add(
                main,
                arcname=f"{app_name}/Contents/MacOS/cc-branch",
            )
            if duplicate_main_binary:
                duplicate = workdir / "cc-branch-copy"
                duplicate.write_bytes(b"app-copy")
                duplicate.chmod(0o755)
                archive.add(
                    duplicate,
                    arcname=f"{app_name}/Contents/MacOS/cc-branch",
                )
        if include_backend:
            backend = workdir / "cc-branch-backend"
            backend.write_bytes(b"backend")
            backend.chmod(0o755)
            archive.add(
                backend,
                arcname=f"{app_name}/Contents/MacOS/cc-branch-backend",
            )
            if duplicate_backend:
                archive.add(
                    backend,
                    arcname=f"{app_name}/Contents/MacOS/cc-branch-backend",
                )


def write_signature_files(release_dir: Path, signatures: dict[str, str]) -> None:
    for asset, signature in signatures.items():
        (release_dir / f"{asset}.sig").write_text(signature, encoding="utf-8")


def checksum_line(asset: str, digest: str = "") -> str:
    return f"{digest or 'a' * 64}  {asset}"


FIRST_LAUNCH_COPY = "On first launch, the app should show Local backend ready. Click Add project to connect a local directory or SSH workspace."


INSTALL_COPY_LINES = [
    "Do not use GitHub's Source code zip or tar.gz downloads for the desktop app.",
    "macOS: open the DMG, drag CC Branch to Applications, then launch it from Applications.",
    "Windows: run the MSI or setup EXE; no terminal or Python install is required.",
    "Linux: install the DEB/RPM or run the AppImage directly.",
    FIRST_LAUNCH_COPY,
    "Use the Retry button in the app first. If it still fails, download the installer for your platform from the table above and reinstall.",
    "If startup still fails, click Copy report and attach the report when filing an issue.",
]


DOWNLOAD_TABLE_ROWS = [
    "| Your computer | Download | Size | Notes |",
    "| --- | --- | ---: | --- |",
    f"| macOS Apple Silicon DMG | [CC.Branch_0.1.4_aarch64.dmg]({release_url('CC.Branch_0.1.4_aarch64.dmg')}) | 7 B | Signed and notarized DMG. |",
    f"| macOS Intel DMG | [CC.Branch_0.1.4_x64.dmg]({release_url('CC.Branch_0.1.4_x64.dmg')}) | 7 B | Signed and notarized DMG. |",
    f"| Windows MSI | [cc-branch_0.1.4_x64_en-US.msi]({release_url('cc-branch_0.1.4_x64_en-US.msi')}) | 7 B | Recommended Windows installer. |",
    f"| Windows NSIS setup | [cc-branch_0.1.4_x64-setup.exe]({release_url('cc-branch_0.1.4_x64-setup.exe')}) | 7 B | Alternative Windows installer. |",
    f"| Ubuntu/Debian package | [CC.Branch_0.1.4_amd64.deb]({release_url('CC.Branch_0.1.4_amd64.deb')}) | 7 B | Debian-based Linux distributions. |",
    f"| Fedora/RHEL package | [CC.Branch-0.1.4-1.x86_64.rpm]({release_url('CC.Branch-0.1.4-1.x86_64.rpm')}) | 7 B | RPM-based Linux distributions. |",
    f"| Linux AppImage | [cc-branch_0.1.4_amd64.AppImage]({release_url('cc-branch_0.1.4_amd64.AppImage')}) | 7 B | Portable Linux build. |",
]

DOWNLOAD_ASSETS = {
    "macOS Apple Silicon DMG": "CC.Branch_0.1.4_aarch64.dmg",
    "macOS Intel DMG": "CC.Branch_0.1.4_x64.dmg",
    "Windows MSI": "cc-branch_0.1.4_x64_en-US.msi",
    "Windows NSIS setup": "cc-branch_0.1.4_x64-setup.exe",
    "Ubuntu/Debian package": "CC.Branch_0.1.4_amd64.deb",
    "Fedora/RHEL package": "CC.Branch-0.1.4-1.x86_64.rpm",
    "Linux AppImage": "cc-branch_0.1.4_amd64.AppImage",
}

CHECKSUM_COPY = f"Verify the download with [{CHECKSUMS_ASSET_NAME}]({release_url(CHECKSUMS_ASSET_NAME)})."


def valid_release_notes(*extra_lines: str) -> str:
    return "\n".join(
        [
            "No separate Python install is required for the desktop app.",
            "## Download the right installer",
            *DOWNLOAD_TABLE_ROWS,
            "The bundled backend starts automatically.",
            CHECKSUM_COPY,
            *INSTALL_COPY_LINES,
            *extra_lines,
        ]
    )


class ReleaseCanaryTests(unittest.TestCase):
    def test_latest_json_requires_platform_urls_and_signatures(self):
        data = {
            "version": "0.1.4",
            "platforms": {
                "darwin-aarch64": {"url": "https://example.test/cc-branch_aarch64.app.tar.gz", "signature": "sig"},
                "darwin-x86_64": {"url": "https://example.test/cc-branch_x64.app.tar.gz", "signature": "sig"},
                "windows-x86_64": {"url": "https://example.test/cc-branch_0.1.4_x64_en-US.msi", "signature": "sig"},
                "linux-x86_64": {"url": "https://example.test/cc-branch_0.1.4_amd64.AppImage", "signature": "sig"},
            },
        }

        validate_latest_json(data)

    def test_latest_json_rejects_missing_platforms(self):
        with self.assertRaises(ValueError):
            validate_latest_json({"version": "0.1.4", "platforms": {}})

    def test_latest_json_rejects_platform_url_outside_expected_release(self):
        data = {
            "version": "0.1.4",
            "platforms": {
                "darwin-aarch64": {
                    "url": "https://example.test/cc-branch_aarch64.app.tar.gz",
                    "signature": "sig",
                },
                "darwin-x86_64": {
                    "url": release_url("cc-branch_x64.app.tar.gz"),
                    "signature": "sig",
                },
                "windows-x86_64": {
                    "url": release_url("cc-branch_0.1.4_x64_en-US.msi"),
                    "signature": "sig",
                },
                "linux-x86_64": {
                    "url": release_url("cc-branch_0.1.4_amd64.AppImage"),
                    "signature": "sig",
                },
            },
        }

        with self.assertRaisesRegex(ValueError, "expected release URL"):
            validate_latest_json(
                data,
                available_assets={
                    "cc-branch_aarch64.app.tar.gz",
                    "cc-branch_x64.app.tar.gz",
                    "cc-branch_0.1.4_x64_en-US.msi",
                    "cc-branch_0.1.4_amd64.AppImage",
                },
                expected_repo="GeminiLight/cc-branch",
                expected_tag="v0.1.4",
            )

    def test_release_dir_verifies_downloaded_canary_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            release_body = valid_release_notes()
            latest = {
                "version": "0.1.4",
                "notes": release_body,
                "platforms": {
                    "darwin-aarch64": {
                        "url": release_url("cc-branch_aarch64.app.tar.gz"),
                        "signature": "sig",
                    },
                    "darwin-x86_64": {
                        "url": release_url("cc-branch_x64.app.tar.gz"),
                        "signature": "sig",
                    },
                    "windows-x86_64": {
                        "url": release_url("cc-branch_0.1.4_x64_en-US.msi"),
                        "signature": "sig",
                    },
                    "linux-x86_64": {
                        "url": release_url("cc-branch_0.1.4_amd64.AppImage"),
                        "signature": "sig",
                    },
                },
            }
            (release_dir / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
            app_tar = release_dir / "cc-branch_aarch64.app.tar.gz"
            write_app_tarball(app_tar, version="0.1.4")
            write_app_tarball(release_dir / "cc-branch_x64.app.tar.gz", version="0.1.4")
            write_signature_files(
                release_dir,
                {
                    "cc-branch_aarch64.app.tar.gz": "sig",
                    "cc-branch_x64.app.tar.gz": "sig",
                    "cc-branch_0.1.4_x64_en-US.msi": "sig",
                    "cc-branch_0.1.4_amd64.AppImage": "sig",
                },
            )

            result = verify_release_dir(
                release_dir,
                sample_asset="cc-branch_aarch64.app.tar.gz",
                expected_version="0.1.4",
                available_assets={
                    "cc-branch_aarch64.app.tar.gz",
                    "cc-branch_x64.app.tar.gz",
                    "cc-branch_0.1.4_x64_en-US.msi",
                    "cc-branch_0.1.4_x64-setup.exe",
                    "cc-branch_0.1.4_amd64.AppImage",
                    "CC.Branch_0.1.4_aarch64.dmg",
                    "CC.Branch_0.1.4_x64.dmg",
                    "CC.Branch_0.1.4_amd64.deb",
                    "CC.Branch-0.1.4-1.x86_64.rpm",
                },
                asset_sizes={
                    "cc-branch_aarch64.app.tar.gz": 7,
                    "cc-branch_x64.app.tar.gz": 7,
                    "cc-branch_0.1.4_x64_en-US.msi": 7,
                    "cc-branch_0.1.4_x64-setup.exe": 7,
                    "cc-branch_0.1.4_amd64.AppImage": 7,
                    "CC.Branch_0.1.4_aarch64.dmg": 7,
                    "CC.Branch_0.1.4_x64.dmg": 7,
                    "CC.Branch_0.1.4_amd64.deb": 7,
                    "CC.Branch-0.1.4-1.x86_64.rpm": 7,
                },
                repo="GeminiLight/cc-branch",
                tag="v0.1.4",
                release_notes_body=release_body,
            )

            self.assertTrue(result["sample_content"]["checked"])
            self.assertEqual(result["repo"], "GeminiLight/cc-branch")
            self.assertEqual(result["tag"], "v0.1.4")
            self.assertEqual(result["download_assets"]["Windows MSI"], "cc-branch_0.1.4_x64_en-US.msi")
            self.assertEqual(result["download_assets"]["Windows NSIS setup"], "cc-branch_0.1.4_x64-setup.exe")
            self.assertEqual(
                result["sample_content"]["backend_path"],
                "CC Branch.app/Contents/MacOS/cc-branch-backend",
            )

    def test_release_dir_rejects_latest_json_signature_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            latest = {
                "version": "0.1.4",
                "platforms": {
                    "darwin-aarch64": {
                        "url": release_url("cc-branch_aarch64.app.tar.gz"),
                        "signature": "latest-json-signature",
                    },
                    "darwin-x86_64": {
                        "url": release_url("cc-branch_x64.app.tar.gz"),
                        "signature": "sig",
                    },
                    "windows-x86_64": {
                        "url": release_url("cc-branch_0.1.4_x64_en-US.msi"),
                        "signature": "sig",
                    },
                    "linux-x86_64": {
                        "url": release_url("cc-branch_0.1.4_amd64.AppImage"),
                        "signature": "sig",
                    },
                },
            }
            (release_dir / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
            write_app_tarball(release_dir / "cc-branch_aarch64.app.tar.gz", version="0.1.4")
            (release_dir / "cc-branch_aarch64.app.tar.gz.sig").write_text("release-asset-signature", encoding="utf-8")
            write_app_tarball(release_dir / "cc-branch_x64.app.tar.gz", version="0.1.4")
            (release_dir / "cc-branch_x64.app.tar.gz.sig").write_text("sig", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "signature"):
                verify_release_dir(
                    release_dir,
                    sample_asset="cc-branch_aarch64.app.tar.gz",
                    expected_version="0.1.4",
                    available_assets={
                        "cc-branch_aarch64.app.tar.gz",
                        "cc-branch_x64.app.tar.gz",
                        "cc-branch_0.1.4_x64_en-US.msi",
                        "cc-branch_0.1.4_x64-setup.exe",
                        "cc-branch_0.1.4_amd64.AppImage",
                        "CC.Branch_0.1.4_aarch64.dmg",
                        "CC.Branch_0.1.4_x64.dmg",
                        "CC.Branch_0.1.4_amd64.deb",
                        "CC.Branch-0.1.4-1.x86_64.rpm",
                    },
                    asset_sizes={
                        "cc-branch_aarch64.app.tar.gz": 7,
                        "cc-branch_x64.app.tar.gz": 7,
                        "cc-branch_0.1.4_x64_en-US.msi": 7,
                        "cc-branch_0.1.4_x64-setup.exe": 7,
                        "cc-branch_0.1.4_amd64.AppImage": 7,
                        "CC.Branch_0.1.4_aarch64.dmg": 7,
                        "CC.Branch_0.1.4_x64.dmg": 7,
                        "CC.Branch_0.1.4_amd64.deb": 7,
                        "CC.Branch-0.1.4-1.x86_64.rpm": 7,
                    },
                )

    def test_release_dir_rejects_latest_json_windows_signature_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            latest = {
                "version": "0.1.4",
                "platforms": {
                    "darwin-aarch64": {
                        "url": release_url("cc-branch_aarch64.app.tar.gz"),
                        "signature": "sig",
                    },
                    "darwin-x86_64": {
                        "url": release_url("cc-branch_x64.app.tar.gz"),
                        "signature": "sig",
                    },
                    "windows-x86_64": {
                        "url": release_url("cc-branch_0.1.4_x64_en-US.msi"),
                        "signature": "latest-json-windows-signature",
                    },
                    "linux-x86_64": {
                        "url": release_url("cc-branch_0.1.4_amd64.AppImage"),
                        "signature": "sig",
                    },
                },
            }
            (release_dir / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
            write_app_tarball(release_dir / "cc-branch_aarch64.app.tar.gz", version="0.1.4")
            write_app_tarball(release_dir / "cc-branch_x64.app.tar.gz", version="0.1.4")
            write_signature_files(
                release_dir,
                {
                    "cc-branch_aarch64.app.tar.gz": "sig",
                    "cc-branch_x64.app.tar.gz": "sig",
                    "cc-branch_0.1.4_x64_en-US.msi": "release-asset-windows-signature",
                    "cc-branch_0.1.4_amd64.AppImage": "sig",
                },
            )

            with self.assertRaisesRegex(ValueError, "cc-branch_0.1.4_x64_en-US.msi"):
                verify_release_dir(
                    release_dir,
                    sample_asset="cc-branch_aarch64.app.tar.gz",
                    expected_version="0.1.4",
                    available_assets={
                        "cc-branch_aarch64.app.tar.gz",
                        "cc-branch_x64.app.tar.gz",
                        "cc-branch_0.1.4_x64_en-US.msi",
                        "cc-branch_0.1.4_x64-setup.exe",
                        "cc-branch_0.1.4_amd64.AppImage",
                        "CC.Branch_0.1.4_aarch64.dmg",
                        "CC.Branch_0.1.4_x64.dmg",
                        "CC.Branch_0.1.4_amd64.deb",
                        "CC.Branch-0.1.4-1.x86_64.rpm",
                    },
                    asset_sizes={
                        "cc-branch_aarch64.app.tar.gz": 7,
                        "cc-branch_x64.app.tar.gz": 7,
                        "cc-branch_0.1.4_x64_en-US.msi": 7,
                        "cc-branch_0.1.4_x64-setup.exe": 7,
                        "cc-branch_0.1.4_amd64.AppImage": 7,
                        "CC.Branch_0.1.4_aarch64.dmg": 7,
                        "CC.Branch_0.1.4_x64.dmg": 7,
                        "CC.Branch_0.1.4_amd64.deb": 7,
                        "CC.Branch-0.1.4-1.x86_64.rpm": 7,
                    },
                )

    def test_release_dir_rejects_missing_macos_updater_tarball(self):
        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            latest = {
                "version": "0.1.4",
                "platforms": {
                    "darwin-aarch64": {
                        "url": release_url("cc-branch_aarch64.app.tar.gz"),
                        "signature": "sig",
                    },
                    "darwin-x86_64": {
                        "url": release_url("cc-branch_x64.app.tar.gz"),
                        "signature": "sig",
                    },
                    "windows-x86_64": {
                        "url": release_url("cc-branch_0.1.4_x64_en-US.msi"),
                        "signature": "sig",
                    },
                    "linux-x86_64": {
                        "url": release_url("cc-branch_0.1.4_amd64.AppImage"),
                        "signature": "sig",
                    },
                },
            }
            (release_dir / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
            write_app_tarball(release_dir / "cc-branch_aarch64.app.tar.gz", version="0.1.4")
            (release_dir / "cc-branch_aarch64.app.tar.gz.sig").write_text("sig", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "cc-branch_x64.app.tar.gz"):
                verify_release_dir(
                    release_dir,
                    sample_asset="cc-branch_aarch64.app.tar.gz",
                    expected_version="0.1.4",
                    available_assets={
                        "cc-branch_aarch64.app.tar.gz",
                        "cc-branch_x64.app.tar.gz",
                        "cc-branch_0.1.4_x64_en-US.msi",
                        "cc-branch_0.1.4_x64-setup.exe",
                        "cc-branch_0.1.4_amd64.AppImage",
                        "CC.Branch_0.1.4_aarch64.dmg",
                        "CC.Branch_0.1.4_x64.dmg",
                        "CC.Branch_0.1.4_amd64.deb",
                        "CC.Branch-0.1.4-1.x86_64.rpm",
                    },
                    asset_sizes={
                        "cc-branch_aarch64.app.tar.gz": 7,
                        "cc-branch_x64.app.tar.gz": 7,
                        "cc-branch_0.1.4_x64_en-US.msi": 7,
                        "cc-branch_0.1.4_x64-setup.exe": 7,
                        "cc-branch_0.1.4_amd64.AppImage": 7,
                        "CC.Branch_0.1.4_aarch64.dmg": 7,
                        "CC.Branch_0.1.4_x64.dmg": 7,
                        "CC.Branch_0.1.4_amd64.deb": 7,
                        "CC.Branch-0.1.4-1.x86_64.rpm": 7,
                    },
                )

    def test_release_notes_must_include_direct_download_links(self):
        download_assets = {
            "macOS Apple Silicon DMG": "CC.Branch_0.1.4_aarch64.dmg",
            "Windows MSI": "cc-branch_0.1.4_x64_en-US.msi",
        }
        body = "\n".join(
            [
                "# CC Branch Desktop v0.1.4",
                "No separate Python install is required for the desktop app.",
                "## Download the right installer",
                "| Your computer | Download | Size | Notes |",
                "| --- | --- | ---: | --- |",
                "| macOS Apple Silicon DMG | [CC.Branch_0.1.4_aarch64.dmg](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/CC.Branch_0.1.4_aarch64.dmg) | 12.0 MB | Signed and notarized DMG. |",
                "| Windows MSI | [cc-branch_0.1.4_x64_en-US.msi](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/cc-branch_0.1.4_x64_en-US.msi) | 22.0 MB | Recommended Windows installer. |",
                "The bundled backend starts automatically.",
                f"Verify the download with [{CHECKSUMS_ASSET_NAME}](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/{CHECKSUMS_ASSET_NAME}).",
                *INSTALL_COPY_LINES,
            ]
        )

        result = validate_release_notes(
            body,
            download_assets=download_assets,
            repo="GeminiLight/cc-branch",
            tag="v0.1.4",
        )

        self.assertEqual(result["assets"], sorted(download_assets))

    def test_release_notes_require_checksum_manifest_link(self):
        body = valid_release_notes().replace(
            f"{CHECKSUM_COPY}\n",
            "",
        )

        with self.assertRaisesRegex(ValueError, CHECKSUMS_ASSET_NAME):
            validate_release_notes(
                body,
                download_assets={"Windows MSI": "cc-branch_0.1.4_x64_en-US.msi"},
                repo="GeminiLight/cc-branch",
                tag="v0.1.4",
            )

    def test_checksum_manifest_must_cover_recommended_downloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            (release_dir / CHECKSUMS_ASSET_NAME).write_text(
                "\n".join(
                    [
                        checksum_line("CC.Branch_0.1.4_aarch64.dmg"),
                        checksum_line("cc-branch_0.1.4_x64_en-US.msi", "b" * 64),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = validate_checksum_manifest(
                release_dir,
                download_assets={
                    "macOS Apple Silicon DMG": "CC.Branch_0.1.4_aarch64.dmg",
                    "Windows MSI": "cc-branch_0.1.4_x64_en-US.msi",
                },
            )

        self.assertEqual(result["asset"], CHECKSUMS_ASSET_NAME)
        self.assertEqual(
            result["covered_assets"],
            ["CC.Branch_0.1.4_aarch64.dmg", "cc-branch_0.1.4_x64_en-US.msi"],
        )

    def test_checksum_manifest_rejects_missing_recommended_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            (release_dir / CHECKSUMS_ASSET_NAME).write_text(
                checksum_line("CC.Branch_0.1.4_aarch64.dmg") + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Windows MSI"):
                validate_checksum_manifest(
                    release_dir,
                    download_assets={
                        "macOS Apple Silicon DMG": "CC.Branch_0.1.4_aarch64.dmg",
                        "Windows MSI": "cc-branch_0.1.4_x64_en-US.msi",
                    },
                )

    def test_checksum_manifest_verifies_downloaded_asset_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            asset = release_dir / "cc-branch_0.1.4_x64_en-US.msi"
            asset.write_bytes(b"installer")
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            (release_dir / CHECKSUMS_ASSET_NAME).write_text(
                checksum_line(asset.name, digest) + "\n",
                encoding="utf-8",
            )

            result = validate_checksum_manifest(
                release_dir,
                download_assets={"Windows MSI": asset.name},
            )

        self.assertEqual(result["verified_assets"], [asset.name])

    def test_checksum_manifest_rejects_downloaded_asset_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            asset = release_dir / "cc-branch_0.1.4_x64_en-US.msi"
            asset.write_bytes(b"corrupt-installer")
            (release_dir / CHECKSUMS_ASSET_NAME).write_text(
                checksum_line(asset.name, "0" * 64) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                validate_checksum_manifest(
                    release_dir,
                    download_assets={"Windows MSI": asset.name},
                )

    def test_release_notes_must_list_downloads_in_platform_table(self):
        body = "\n".join(
            [
                "# CC Branch Desktop v0.1.4",
                "No separate Python install is required for the desktop app.",
                "## Download the right installer",
                "| Your computer | Download | Size | Notes |",
                "| --- | --- | ---: | --- |",
                "The bundled backend starts automatically.",
                CHECKSUM_COPY,
                *INSTALL_COPY_LINES,
                "[CC.Branch_0.1.4_aarch64.dmg](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/CC.Branch_0.1.4_aarch64.dmg)",
                "[cc-branch_0.1.4_x64_en-US.msi](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/cc-branch_0.1.4_x64_en-US.msi)",
            ]
        )

        with self.assertRaisesRegex(ValueError, "download table"):
            validate_release_notes(
                body,
                download_assets={
                    "macOS Apple Silicon DMG": "CC.Branch_0.1.4_aarch64.dmg",
                    "Windows MSI": "cc-branch_0.1.4_x64_en-US.msi",
                },
                repo="GeminiLight/cc-branch",
                tag="v0.1.4",
            )

    def test_release_notes_reject_missing_direct_download_link(self):
        with self.assertRaisesRegex(ValueError, "Windows MSI"):
            validate_release_notes(
                "\n".join(
                    [
                        "No separate Python install is required for the desktop app.",
                        "## Download the right installer",
                        "The bundled backend starts automatically.",
                        CHECKSUM_COPY,
                        *INSTALL_COPY_LINES,
                        "cc-branch_0.1.4_x64_en-US.msi",
                    ]
                ),
                download_assets={"Windows MSI": "cc-branch_0.1.4_x64_en-US.msi"},
                repo="GeminiLight/cc-branch",
                tag="v0.1.4",
            )

    def test_release_notes_reject_missing_platform_install_copy(self):
        body = "\n".join(
            [
                "No separate Python install is required for the desktop app.",
                "## Download the right installer",
                "The bundled backend starts automatically.",
                CHECKSUM_COPY,
                "Do not use GitHub's Source code zip or tar.gz downloads for the desktop app.",
                "[CC.Branch_0.1.4_aarch64.dmg](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/CC.Branch_0.1.4_aarch64.dmg)",
            ]
        )

        with self.assertRaisesRegex(ValueError, "drag CC Branch to Applications"):
            validate_release_notes(
                body,
                download_assets={
                    "macOS Apple Silicon DMG": "CC.Branch_0.1.4_aarch64.dmg",
                },
                repo="GeminiLight/cc-branch",
                tag="v0.1.4",
            )

    def test_release_notes_reject_missing_source_code_download_warning(self):
        body = "\n".join(
            [
                "No separate Python install is required for the desktop app.",
                "## Download the right installer",
                "The bundled backend starts automatically.",
                CHECKSUM_COPY,
                "macOS: open the DMG, drag CC Branch to Applications, then launch it from Applications.",
                "Windows: run the MSI or setup EXE; no terminal or Python install is required.",
                "Linux: install the DEB/RPM or run the AppImage directly.",
                "[CC.Branch_0.1.4_aarch64.dmg](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/CC.Branch_0.1.4_aarch64.dmg)",
            ]
        )

        with self.assertRaisesRegex(ValueError, "Source code zip or tar.gz"):
            validate_release_notes(
                body,
                download_assets={
                    "macOS Apple Silicon DMG": "CC.Branch_0.1.4_aarch64.dmg",
                },
                repo="GeminiLight/cc-branch",
                tag="v0.1.4",
            )

    def test_release_notes_reject_missing_copy_report_support_path(self):
        body = "\n".join(
            [
                "No separate Python install is required for the desktop app.",
                "## Download the right installer",
                "The bundled backend starts automatically.",
                CHECKSUM_COPY,
                "Do not use GitHub's Source code zip or tar.gz downloads for the desktop app.",
                "macOS: open the DMG, drag CC Branch to Applications, then launch it from Applications.",
                "Windows: run the MSI or setup EXE; no terminal or Python install is required.",
                "Linux: install the DEB/RPM or run the AppImage directly.",
                "[CC.Branch_0.1.4_aarch64.dmg](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/CC.Branch_0.1.4_aarch64.dmg)",
            ]
        )

        with self.assertRaisesRegex(ValueError, "Copy report"):
            validate_release_notes(
                body,
                download_assets={
                    "macOS Apple Silicon DMG": "CC.Branch_0.1.4_aarch64.dmg",
                },
                repo="GeminiLight/cc-branch",
                tag="v0.1.4",
            )

    def test_release_notes_reject_missing_first_launch_guidance(self):
        body = valid_release_notes().replace(f"{FIRST_LAUNCH_COPY}\n", "")

        with self.assertRaisesRegex(ValueError, "Local backend ready"):
            validate_release_notes(
                body,
                download_assets=DOWNLOAD_ASSETS,
                repo="GeminiLight/cc-branch",
                tag="v0.1.4",
            )

    def test_release_notes_reject_latest_installer_reinstall_guidance(self):
        body = "\n".join(
            [
                "No separate Python install is required for the desktop app.",
                "## Download the right installer",
                "The bundled backend starts automatically.",
                CHECKSUM_COPY,
                *INSTALL_COPY_LINES,
                "Use the Retry button first. If it still fails, download the latest installer for your platform and reinstall.",
                "Click Copy report in the startup error panel and attach the report when filing an issue.",
                "[CC.Branch_0.1.4_aarch64.dmg](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/CC.Branch_0.1.4_aarch64.dmg)",
            ]
        )

        with self.assertRaisesRegex(ValueError, "current release"):
            validate_release_notes(
                body,
                download_assets={
                    "macOS Apple Silicon DMG": "CC.Branch_0.1.4_aarch64.dmg",
                },
                repo="GeminiLight/cc-branch",
                tag="v0.1.4",
            )

    def test_release_notes_reject_auxiliary_assets_as_user_download_links(self):
        body = "\n".join(
            [
                "No separate Python install is required for the desktop app.",
                "## Download the right installer",
                "The bundled backend starts automatically.",
                CHECKSUM_COPY,
                *INSTALL_COPY_LINES,
                "[cc-branch_0.1.4_x64_en-US.msi](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/cc-branch_0.1.4_x64_en-US.msi)",
                "[cc-branch_0.1.4_x64_en-US.msi.sig](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/cc-branch_0.1.4_x64_en-US.msi.sig)",
            ]
        )

        with self.assertRaisesRegex(ValueError, "auxiliary release asset"):
            validate_release_notes(
                body,
                download_assets={"Windows MSI": "cc-branch_0.1.4_x64_en-US.msi"},
                repo="GeminiLight/cc-branch",
                tag="v0.1.4",
            )

    def test_release_notes_reject_non_recommended_download_links(self):
        body = "\n".join(
            [
                "No separate Python install is required for the desktop app.",
                "## Download the right installer",
                "The bundled backend starts automatically.",
                CHECKSUM_COPY,
                *INSTALL_COPY_LINES,
                "[cc-branch_0.1.4_x64_en-US.msi](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/cc-branch_0.1.4_x64_en-US.msi)",
                "[cc-branch_aarch64.app.tar.gz](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/cc-branch_aarch64.app.tar.gz)",
            ]
        )

        with self.assertRaisesRegex(ValueError, "non-recommended release asset"):
            validate_release_notes(
                body,
                download_assets={"Windows MSI": "cc-branch_0.1.4_x64_en-US.msi"},
                repo="GeminiLight/cc-branch",
                tag="v0.1.4",
            )

    def test_release_notes_reject_floating_latest_download_links(self):
        body = "\n".join(
            [
                "No separate Python install is required for the desktop app.",
                "## Download the right installer",
                "The bundled backend starts automatically.",
                CHECKSUM_COPY,
                *INSTALL_COPY_LINES,
                "[cc-branch_0.1.4_x64_en-US.msi](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/cc-branch_0.1.4_x64_en-US.msi)",
                "[latest Windows MSI](https://github.com/GeminiLight/cc-branch/releases/latest/download/cc-branch_0.1.4_x64_en-US.msi)",
            ]
        )

        with self.assertRaisesRegex(ValueError, "current release"):
            validate_release_notes(
                body,
                download_assets={"Windows MSI": "cc-branch_0.1.4_x64_en-US.msi"},
                repo="GeminiLight/cc-branch",
                tag="v0.1.4",
            )

    def test_release_notes_reject_old_tag_download_links(self):
        body = "\n".join(
            [
                "No separate Python install is required for the desktop app.",
                "## Download the right installer",
                "The bundled backend starts automatically.",
                CHECKSUM_COPY,
                *INSTALL_COPY_LINES,
                "[cc-branch_0.1.4_x64_en-US.msi](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.4/cc-branch_0.1.4_x64_en-US.msi)",
                "[old Windows MSI](https://github.com/GeminiLight/cc-branch/releases/download/v0.1.3/cc-branch_0.1.3_x64_en-US.msi)",
            ]
        )

        with self.assertRaisesRegex(ValueError, "current release"):
            validate_release_notes(
                body,
                download_assets={"Windows MSI": "cc-branch_0.1.4_x64_en-US.msi"},
                repo="GeminiLight/cc-branch",
                tag="v0.1.4",
            )

    def test_release_dir_rejects_latest_json_notes_without_download_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            latest = {
                "version": "0.1.4",
                "notes": "Old release notes without direct download links.",
                "platforms": {
                    "darwin-aarch64": {
                        "url": release_url("cc-branch_aarch64.app.tar.gz"),
                        "signature": "sig",
                    },
                    "darwin-x86_64": {
                        "url": release_url("cc-branch_x64.app.tar.gz"),
                        "signature": "sig",
                    },
                    "windows-x86_64": {
                        "url": release_url("cc-branch_0.1.4_x64_en-US.msi"),
                        "signature": "sig",
                    },
                    "linux-x86_64": {
                        "url": release_url("cc-branch_0.1.4_amd64.AppImage"),
                        "signature": "sig",
                    },
                },
            }
            (release_dir / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
            app_tar = release_dir / "cc-branch_aarch64.app.tar.gz"
            with tarfile.open(app_tar, "w:gz") as archive:
                backend = release_dir / "cc-branch-backend"
                backend.write_bytes(b"backend")
                backend.chmod(0o755)
                archive.add(
                    backend,
                    arcname="CC Branch.app/Contents/MacOS/cc-branch-backend",
                )
            (release_dir / "cc-branch_aarch64.app.tar.gz.sig").write_text("sig", encoding="utf-8")
            release_body = valid_release_notes()

            with self.assertRaisesRegex(ValueError, "latest.json notes"):
                verify_release_dir(
                    release_dir,
                    sample_asset="cc-branch_aarch64.app.tar.gz",
                    expected_version="0.1.4",
                    available_assets={
                        "cc-branch_aarch64.app.tar.gz",
                        "cc-branch_x64.app.tar.gz",
                        "cc-branch_0.1.4_x64_en-US.msi",
                        "cc-branch_0.1.4_x64-setup.exe",
                        "cc-branch_0.1.4_amd64.AppImage",
                        "CC.Branch_0.1.4_aarch64.dmg",
                        "CC.Branch_0.1.4_x64.dmg",
                        "CC.Branch_0.1.4_amd64.deb",
                        "CC.Branch-0.1.4-1.x86_64.rpm",
                    },
                    asset_sizes={
                        "cc-branch_aarch64.app.tar.gz": 7,
                        "cc-branch_x64.app.tar.gz": 7,
                        "cc-branch_0.1.4_x64_en-US.msi": 7,
                        "cc-branch_0.1.4_x64-setup.exe": 7,
                        "cc-branch_0.1.4_amd64.AppImage": 7,
                        "CC.Branch_0.1.4_aarch64.dmg": 7,
                        "CC.Branch_0.1.4_x64.dmg": 7,
                        "CC.Branch_0.1.4_amd64.deb": 7,
                        "CC.Branch-0.1.4-1.x86_64.rpm": 7,
                    },
                    release_notes_body=release_body,
                    repo="GeminiLight/cc-branch",
                    tag="v0.1.4",
                )

    def test_release_dir_rejects_latest_json_notes_that_differ_from_release_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            latest_notes = valid_release_notes("This text is only in latest.json.")
            release_body = latest_notes.replace(
                "This text is only in latest.json.",
                "This text is only in the GitHub release body.",
            )
            latest = {
                "version": "0.1.4",
                "notes": latest_notes,
                "platforms": {
                    "darwin-aarch64": {
                        "url": release_url("cc-branch_aarch64.app.tar.gz"),
                        "signature": "sig",
                    },
                    "darwin-x86_64": {
                        "url": release_url("cc-branch_x64.app.tar.gz"),
                        "signature": "sig",
                    },
                    "windows-x86_64": {
                        "url": release_url("cc-branch_0.1.4_x64_en-US.msi"),
                        "signature": "sig",
                    },
                    "linux-x86_64": {
                        "url": release_url("cc-branch_0.1.4_amd64.AppImage"),
                        "signature": "sig",
                    },
                },
            }
            (release_dir / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
            app_tar = release_dir / "cc-branch_aarch64.app.tar.gz"
            with tarfile.open(app_tar, "w:gz") as archive:
                backend = release_dir / "cc-branch-backend"
                backend.write_bytes(b"backend")
                backend.chmod(0o755)
                archive.add(
                    backend,
                    arcname="CC Branch.app/Contents/MacOS/cc-branch-backend",
                )
            (release_dir / "cc-branch_aarch64.app.tar.gz.sig").write_text("sig", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "latest.json notes do not match release body"):
                verify_release_dir(
                    release_dir,
                    sample_asset="cc-branch_aarch64.app.tar.gz",
                    expected_version="0.1.4",
                    available_assets={
                        "cc-branch_aarch64.app.tar.gz",
                        "cc-branch_x64.app.tar.gz",
                        "cc-branch_0.1.4_x64_en-US.msi",
                        "cc-branch_0.1.4_x64-setup.exe",
                        "cc-branch_0.1.4_amd64.AppImage",
                        "CC.Branch_0.1.4_aarch64.dmg",
                        "CC.Branch_0.1.4_x64.dmg",
                        "CC.Branch_0.1.4_amd64.deb",
                        "CC.Branch-0.1.4-1.x86_64.rpm",
                    },
                    asset_sizes={
                        "cc-branch_aarch64.app.tar.gz": 7,
                        "cc-branch_x64.app.tar.gz": 7,
                        "cc-branch_0.1.4_x64_en-US.msi": 7,
                        "cc-branch_0.1.4_x64-setup.exe": 7,
                        "cc-branch_0.1.4_amd64.AppImage": 7,
                        "CC.Branch_0.1.4_aarch64.dmg": 7,
                        "CC.Branch_0.1.4_x64.dmg": 7,
                        "CC.Branch_0.1.4_amd64.deb": 7,
                        "CC.Branch-0.1.4-1.x86_64.rpm": 7,
                    },
                    release_notes_body=release_body,
                    repo="GeminiLight/cc-branch",
                    tag="v0.1.4",
                )

    def test_release_dir_rejects_wrong_metadata_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            latest = {
                "version": "0.1.3",
                "platforms": {
                    "darwin-aarch64": {
                        "url": "https://example.test/cc-branch_aarch64.app.tar.gz",
                        "signature": "sig",
                    },
                    "darwin-x86_64": {
                        "url": "https://example.test/cc-branch_x64.app.tar.gz",
                        "signature": "sig",
                    },
                    "windows-x86_64": {
                        "url": "https://example.test/cc-branch_0.1.4_x64_en-US.msi",
                        "signature": "sig",
                    },
                    "linux-x86_64": {
                        "url": "https://example.test/cc-branch_0.1.4_amd64.AppImage",
                        "signature": "sig",
                    },
                },
            }
            (release_dir / "latest.json").write_text(json.dumps(latest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "does not match expected"):
                verify_release_dir(release_dir, expected_version="0.1.4")

    def test_release_dir_rejects_latest_json_referencing_missing_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            latest = {
                "version": "0.1.4",
                "platforms": {
                    "darwin-aarch64": {
                        "url": "https://example.test/cc-branch_aarch64.app.tar.gz",
                        "signature": "sig",
                    },
                    "darwin-x86_64": {
                        "url": "https://example.test/missing.app.tar.gz",
                        "signature": "sig",
                    },
                    "windows-x86_64": {
                        "url": "https://example.test/cc-branch_0.1.4_x64_en-US.msi",
                        "signature": "sig",
                    },
                    "linux-x86_64": {
                        "url": "https://example.test/cc-branch_0.1.4_amd64.AppImage",
                        "signature": "sig",
                    },
                },
            }
            (release_dir / "latest.json").write_text(json.dumps(latest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "references missing release asset"):
                verify_release_dir(
                    release_dir,
                    available_assets={
                        "cc-branch_aarch64.app.tar.gz",
                        "cc-branch_0.1.4_x64_en-US.msi",
                        "cc-branch_0.1.4_amd64.AppImage",
                        "CC.Branch_aarch64.dmg",
                        "CC.Branch_x64.dmg",
                        "CC.Branch_0.1.4_amd64.deb",
                        "CC.Branch-0.1.4-1.x86_64.rpm",
                    },
                )

    def test_release_dir_rejects_missing_recommended_download_asset(self):
        with self.assertRaisesRegex(ValueError, "macOS Apple Silicon DMG"):
            validate_download_assets({
                "cc-branch_aarch64.app.tar.gz",
                "cc-branch_x64.app.tar.gz",
                "cc-branch_0.1.4_x64_en-US.msi",
                "cc-branch_0.1.4_x64-setup.exe",
                "cc-branch_0.1.4_amd64.AppImage",
                "CC.Branch_x64.dmg",
                "CC.Branch_0.1.4_amd64.deb",
                "CC.Branch-0.1.4-1.x86_64.rpm",
            })

    def test_release_dir_rejects_empty_recommended_download_asset(self):
        with self.assertRaisesRegex(ValueError, "Windows MSI"):
            validate_download_assets(
                {
                    "CC.Branch_aarch64.dmg",
                    "CC.Branch_x64.dmg",
                    "cc-branch_0.1.4_x64_en-US.msi",
                    "cc-branch_0.1.4_x64-setup.exe",
                    "cc-branch_0.1.4_amd64.AppImage",
                    "CC.Branch_0.1.4_amd64.deb",
                    "CC.Branch-0.1.4-1.x86_64.rpm",
                },
                asset_sizes={
                    "CC.Branch_aarch64.dmg": 7,
                    "CC.Branch_x64.dmg": 7,
                    "cc-branch_0.1.4_x64_en-US.msi": 0,
                    "cc-branch_0.1.4_x64-setup.exe": 7,
                    "cc-branch_0.1.4_amd64.AppImage": 7,
                    "CC.Branch_0.1.4_amd64.deb": 7,
                    "CC.Branch-0.1.4-1.x86_64.rpm": 7,
                },
            )

    def test_release_dir_rejects_auxiliary_assets_as_recommended_downloads(self):
        with self.assertRaisesRegex(ValueError, "Windows NSIS setup"):
            validate_download_assets(
                {
                    "CC.Branch_0.1.4_aarch64.dmg",
                    "CC.Branch_0.1.4_x64.dmg",
                    "cc-branch_0.1.4_x64_en-US.msi",
                    "cc-branch_0.1.4_x64-setup.exe.blockmap",
                    "cc-branch_0.1.4_amd64.AppImage",
                    "CC.Branch_0.1.4_amd64.deb",
                    "CC.Branch-0.1.4-1.x86_64.rpm",
                },
                expected_version="0.1.4",
                asset_sizes={
                    "CC.Branch_0.1.4_aarch64.dmg": 7,
                    "CC.Branch_0.1.4_x64.dmg": 7,
                    "cc-branch_0.1.4_x64_en-US.msi": 7,
                    "cc-branch_0.1.4_x64-setup.exe.blockmap": 7,
                    "cc-branch_0.1.4_amd64.AppImage": 7,
                    "CC.Branch_0.1.4_amd64.deb": 7,
                    "CC.Branch-0.1.4-1.x86_64.rpm": 7,
                },
            )

    def test_recommended_download_asset_names_exclude_auxiliary_assets(self):
        self.assertEqual(
            recommended_download_asset_names(
                {
                    "cc-branch_0.1.4_x64-setup.exe",
                    "cc-branch_0.1.4_x64-setup.exe.blockmap",
                    "cc-branch_0.1.4_x64-setup.exe.sig",
                }
            ),
            ["cc-branch_0.1.4_x64-setup.exe"],
        )

    def test_release_dir_rejects_ambiguous_recommended_download_assets(self):
        with self.assertRaisesRegex(ValueError, "multiple recommended download assets"):
            validate_download_assets(
                {
                    "CC.Branch_0.1.4_aarch64.dmg",
                    "CC.Branch_0.1.4_aarch64-copy.dmg",
                    "CC.Branch_0.1.4_x64.dmg",
                    "cc-branch_0.1.4_x64_en-US.msi",
                    "cc-branch_0.1.4_x64-setup.exe",
                    "cc-branch_0.1.4_amd64.AppImage",
                    "CC.Branch_0.1.4_amd64.deb",
                    "CC.Branch-0.1.4-1.x86_64.rpm",
                },
                expected_version="0.1.4",
            )

    def test_release_dir_rejects_recommended_download_asset_from_wrong_version(self):
        with self.assertRaisesRegex(ValueError, "does not match expected version 0.1.4"):
            validate_download_assets(
                {
                    "CC.Branch_0.1.3_aarch64.dmg",
                    "CC.Branch_0.1.4_x64.dmg",
                    "cc-branch_0.1.4_x64_en-US.msi",
                    "cc-branch_0.1.4_x64-setup.exe",
                    "cc-branch_0.1.4_amd64.AppImage",
                    "CC.Branch_0.1.4_amd64.deb",
                    "CC.Branch-0.1.4-1.x86_64.rpm",
                },
                expected_version="0.1.4",
            )

    def test_release_dir_rejects_recommended_download_asset_from_version_prefix_match(self):
        with self.assertRaisesRegex(ValueError, "does not match expected version 0.1.4"):
            validate_download_assets(
                {
                    "CC.Branch_0.1.40_aarch64.dmg",
                    "CC.Branch_0.1.4_x64.dmg",
                    "cc-branch_0.1.4_x64_en-US.msi",
                    "cc-branch_0.1.4_x64-setup.exe",
                    "cc-branch_0.1.4_amd64.AppImage",
                    "CC.Branch_0.1.4_amd64.deb",
                    "CC.Branch-0.1.4-1.x86_64.rpm",
                },
                expected_version="0.1.4",
            )

    def test_release_dir_rejects_extra_recommended_download_asset_from_wrong_version(self):
        with self.assertRaisesRegex(ValueError, "macOS Apple Silicon DMG"):
            validate_download_assets(
                {
                    "CC.Branch_0.1.4_aarch64.dmg",
                    "CC.Branch_9.9.9_aarch64.dmg",
                    "CC.Branch_0.1.4_x64.dmg",
                    "cc-branch_0.1.4_x64_en-US.msi",
                    "cc-branch_0.1.4_x64-setup.exe",
                    "cc-branch_0.1.4_amd64.AppImage",
                    "CC.Branch_0.1.4_amd64.deb",
                    "CC.Branch-0.1.4-1.x86_64.rpm",
                },
                expected_version="0.1.4",
            )

    def test_release_dir_checks_recommended_download_asset_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            latest = {
                "version": "0.1.4",
                "platforms": {
                    "darwin-aarch64": {
                        "url": "https://example.test/cc-branch_aarch64.app.tar.gz",
                        "signature": "sig",
                    },
                    "darwin-x86_64": {
                        "url": "https://example.test/cc-branch_x64.app.tar.gz",
                        "signature": "sig",
                    },
                    "windows-x86_64": {
                        "url": "https://example.test/cc-branch_0.1.4_x64_en-US.msi",
                        "signature": "sig",
                    },
                    "linux-x86_64": {
                        "url": "https://example.test/cc-branch_0.1.4_amd64.AppImage",
                        "signature": "sig",
                    },
                },
            }
            (release_dir / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
            app_tar = release_dir / "cc-branch_aarch64.app.tar.gz"
            with tarfile.open(app_tar, "w:gz") as archive:
                backend = release_dir / "cc-branch-backend"
                backend.write_bytes(b"backend")
                backend.chmod(0o755)
                archive.add(
                    backend,
                    arcname="CC Branch.app/Contents/MacOS/cc-branch-backend",
                )
            (release_dir / "cc-branch_aarch64.app.tar.gz.sig").write_text("sig", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "macOS Apple Silicon DMG"):
                verify_release_dir(
                    release_dir,
                    sample_asset="cc-branch_aarch64.app.tar.gz",
                    expected_version="0.1.4",
                    available_assets={
                        "cc-branch_aarch64.app.tar.gz",
                        "cc-branch_x64.app.tar.gz",
                        "cc-branch_0.1.4_x64_en-US.msi",
                        "cc-branch_0.1.4_x64-setup.exe",
                        "cc-branch_0.1.4_amd64.AppImage",
                        "CC.Branch_0.1.3_aarch64.dmg",
                        "CC.Branch_0.1.4_x64.dmg",
                        "CC.Branch_0.1.4_amd64.deb",
                        "CC.Branch-0.1.4-1.x86_64.rpm",
                    },
                    asset_sizes={
                        "cc-branch_aarch64.app.tar.gz": 7,
                        "cc-branch_x64.app.tar.gz": 7,
                        "cc-branch_0.1.4_x64_en-US.msi": 7,
                        "cc-branch_0.1.4_x64-setup.exe": 7,
                        "cc-branch_0.1.4_amd64.AppImage": 7,
                        "CC.Branch_0.1.3_aarch64.dmg": 7,
                        "CC.Branch_0.1.4_x64.dmg": 7,
                        "CC.Branch_0.1.4_amd64.deb": 7,
                        "CC.Branch-0.1.4-1.x86_64.rpm": 7,
                    },
                )

    def test_latest_json_rejects_empty_referenced_asset(self):
        data = {
            "version": "0.1.4",
            "platforms": {
                "darwin-aarch64": {"url": "https://example.test/cc-branch_aarch64.app.tar.gz", "signature": "sig"},
                "darwin-x86_64": {"url": "https://example.test/cc-branch_x64.app.tar.gz", "signature": "sig"},
                "windows-x86_64": {"url": "https://example.test/cc-branch_0.1.4_x64_en-US.msi", "signature": "sig"},
                "linux-x86_64": {"url": "https://example.test/cc-branch_0.1.4_amd64.AppImage", "signature": "sig"},
            },
        }

        with self.assertRaisesRegex(ValueError, "empty release asset"):
            validate_latest_json(
                data,
                available_assets={
                    "cc-branch_aarch64.app.tar.gz",
                    "cc-branch_x64.app.tar.gz",
                    "cc-branch_0.1.4_x64_en-US.msi",
                    "cc-branch_0.1.4_x64-setup.exe",
                    "cc-branch_0.1.4_amd64.AppImage",
                },
                asset_sizes={
                    "cc-branch_aarch64.app.tar.gz": 7,
                    "cc-branch_x64.app.tar.gz": 0,
                    "cc-branch_0.1.4_x64_en-US.msi": 7,
                    "cc-branch_0.1.4_x64-setup.exe": 7,
                    "cc-branch_0.1.4_amd64.AppImage": 7,
                },
            )

    def test_parse_assets_json_reads_names_and_sizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "assets.json"
            path.write_text(
                json.dumps({
                    "assets": [
                        {"name": "CC.Branch_aarch64.dmg", "size": 10},
                        {"name": "CC.Branch_x64.dmg", "size": "11"},
                    ]
                }),
                encoding="utf-8",
            )

            names, sizes = parse_assets_json(path)

            self.assertEqual(names, {"CC.Branch_aarch64.dmg", "CC.Branch_x64.dmg"})
            self.assertEqual(sizes["CC.Branch_x64.dmg"], 11)

    def test_app_tarball_rejects_missing_backend_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cc-branch_aarch64.app.tar.gz"
            write_app_tarball(path, include_backend=False)

            with self.assertRaisesRegex(ValueError, "cc-branch-backend"):
                verify_app_tarball_contains_backend(path)

    def test_app_tarball_rejects_missing_main_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cc-branch_aarch64.app.tar.gz"
            write_app_tarball(path, include_main_binary=False)

            with self.assertRaisesRegex(ValueError, "Contents/MacOS/cc-branch"):
                verify_app_tarball_contains_backend(path)

    def test_app_tarball_rejects_non_executable_main_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cc-branch_aarch64.app.tar.gz"
            write_app_tarball(path, executable_main_binary=False)

            with self.assertRaisesRegex(ValueError, "app binary.*not executable"):
                verify_app_tarball_contains_backend(path)

    def test_app_tarball_rejects_duplicate_main_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cc-branch_aarch64.app.tar.gz"
            write_app_tarball(path, duplicate_main_binary=True)

            with self.assertRaisesRegex(ValueError, "multiple.*Contents/MacOS/cc-branch"):
                verify_app_tarball_contains_backend(path)

    def test_app_tarball_rejects_duplicate_backend_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cc-branch_aarch64.app.tar.gz"
            write_app_tarball(path, duplicate_backend=True)

            with self.assertRaisesRegex(ValueError, "multiple.*cc-branch-backend"):
                verify_app_tarball_contains_backend(path)

    def test_app_tarball_rejects_duplicate_info_plist(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cc-branch_aarch64.app.tar.gz"
            write_app_tarball(path, duplicate_info_plist=True)

            with self.assertRaisesRegex(ValueError, "multiple.*Info.plist"):
                verify_app_tarball_contains_backend(path)

    def test_app_tarball_rejects_wrong_app_bundle_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cc-branch_aarch64.app.tar.gz"
            write_app_tarball(path, app_name="Other.app")

            with self.assertRaisesRegex(ValueError, "CC Branch.app"):
                verify_app_tarball_contains_backend(path)

    def test_app_tarball_rejects_wrong_bundle_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cc-branch_aarch64.app.tar.gz"
            write_app_tarball(path, version="0.1.3")

            with self.assertRaisesRegex(ValueError, "version"):
                verify_app_tarball_contains_backend(path, expected_version="0.1.4")


if __name__ == "__main__":
    unittest.main()
