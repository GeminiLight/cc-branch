import unittest
from unittest import mock
from pathlib import Path

from scripts.verify_github_release import (
    build_verification_summary,
    collect_launch_backend_sources,
    collect_launch_desktop_metadata,
    collect_launch_port_modes,
    collect_stale_backend_rejections,
    macos_dmg_assets,
    release_download_command,
    release_view_command,
    require_launch_desktop_metadata,
    require_launch_port_modes,
    selected_download_asset,
    selected_latest_platform_assets,
    selected_platform_asset,
    verify_github_release,
    verify_github_release_is_latest,
    verify_macos_dmg_asset,
    verify_platform_installers,
)


DESKTOP_METADATA = {
    "desktop_version": "1.0.2",
    "desktop_platform": "linux",
    "desktop_arch": "x86_64",
}

WINDOWS_DESKTOP_METADATA = {
    "desktop_version": "1.0.2",
    "desktop_platform": "windows",
    "desktop_arch": "x86_64",
}


class VerifyGithubReleaseTests(unittest.TestCase):
    def test_build_verification_summary_marks_unrequired_draft_release_state_checks_as_met(self):
        summary = build_verification_summary(
            repo="owner/repo",
            release_tag="v1.0.2",
            release_url="https://github.com/example/releases/tag/v1.0.2",
            is_draft=True,
            is_prerelease=False,
            latest_release=None,
            require_latest=False,
            require_public=False,
            required_launch_labels=[],
            required_stale_labels=[],
            launch_backend_sources={},
            launch_desktop_metadata={},
            launch_port_modes={},
            stale_backend_rejections={},
            release_notes_checked=True,
            latest_json_notes_checked=True,
        )

        self.assertFalse(summary["release_state"]["is_public"])
        self.assertIsNone(summary["release_state"]["latest_matches_tag"])
        self.assertTrue(summary["checks"]["public_release_requirement_met"])
        self.assertTrue(summary["checks"]["latest_release_requirement_met"])
        self.assertTrue(summary["ready_for_public_download"])
        self.assertNotIn("release_is_public", summary["checks"])
        self.assertNotIn("latest_release_matches_tag", summary["checks"])

    def test_build_verification_summary_reports_release_notes_checks(self):
        summary = build_verification_summary(
            repo="owner/repo",
            release_tag="v1.0.2",
            release_url="https://github.com/example/releases/tag/v1.0.2",
            is_draft=False,
            is_prerelease=False,
            latest_release={"tagName": "v1.0.2", "url": "https://github.com/example/releases/tag/v1.0.2"},
            require_latest=True,
            require_public=True,
            required_launch_labels=[],
            required_stale_labels=[],
            launch_backend_sources={},
            launch_desktop_metadata={},
            launch_port_modes={},
            stale_backend_rejections={},
            release_notes_checked=False,
            latest_json_notes_checked=True,
        )

        self.assertFalse(summary["checks"]["release_notes_verified"])
        self.assertTrue(summary["checks"]["latest_json_notes_verified"])
        self.assertFalse(summary["ready_for_public_download"])

    def test_build_verification_summary_does_not_default_notes_checks_to_verified(self):
        summary = build_verification_summary(
            repo="owner/repo",
            release_tag="v1.0.2",
            release_url="https://github.com/example/releases/tag/v1.0.2",
            is_draft=False,
            is_prerelease=False,
            latest_release={"tagName": "v1.0.2", "url": "https://github.com/example/releases/tag/v1.0.2"},
            require_latest=True,
            require_public=True,
            required_launch_labels=[],
            required_stale_labels=[],
            launch_backend_sources={},
            launch_desktop_metadata={},
            launch_port_modes={},
            stale_backend_rejections={},
        )

        self.assertFalse(summary["checks"]["release_notes_verified"])
        self.assertFalse(summary["checks"]["latest_json_notes_verified"])
        self.assertFalse(summary["ready_for_public_download"])

    def test_selected_platform_asset_reads_latest_json_url(self):
        latest = {
            "platforms": {
                "darwin-aarch64": {
                    "url": "https://github.com/example/releases/download/v1.0.2/CC%20Branch_aarch64.app.tar.gz",
                    "signature": "sig",
                }
            }
        }

        self.assertEqual(
            selected_platform_asset(latest, "darwin-aarch64"),
            "CC Branch_aarch64.app.tar.gz",
        )

    def test_selected_platform_asset_rejects_missing_platform(self):
        with self.assertRaisesRegex(ValueError, "linux-x86_64"):
            selected_platform_asset({"platforms": {}}, "linux-x86_64")

    def test_selected_latest_platform_assets_reads_unique_latest_json_assets(self):
        latest = {
            "platforms": {
                "linux-x86_64": {
                    "url": "https://example.test/cc-branch_1.0.2_amd64.AppImage",
                    "signature": "sig",
                },
                "linux-x86_64-appimage": {
                    "url": "https://example.test/cc-branch_1.0.2_amd64.AppImage",
                    "signature": "sig",
                },
                "windows-x86_64": {
                    "url": "https://example.test/cc-branch_1.0.2_x64_en-US.msi",
                    "signature": "sig",
                },
            }
        }

        self.assertEqual(
            selected_latest_platform_assets(latest),
            [
                "cc-branch_1.0.2_amd64.AppImage",
                "cc-branch_1.0.2_x64_en-US.msi",
            ],
        )

    def test_selected_download_asset_reads_recommended_dmg(self):
        self.assertEqual(
            selected_download_asset(
                {
                    "CC.Branch_1.0.2_aarch64.dmg",
                    "CC.Branch_1.0.2_x64.dmg",
                },
                "macOS Apple Silicon DMG",
            ),
            "CC.Branch_1.0.2_aarch64.dmg",
        )

    def test_selected_download_asset_rejects_missing_recommended_asset(self):
        with self.assertRaisesRegex(ValueError, "macOS Intel DMG"):
            selected_download_asset({"CC.Branch_1.0.2_aarch64.dmg"}, "macOS Intel DMG")

    def test_selected_download_asset_rejects_ambiguous_recommended_assets(self):
        with self.assertRaisesRegex(ValueError, "multiple recommended download assets"):
            selected_download_asset(
                {
                    "CC.Branch_1.0.2_aarch64.dmg",
                    "CC.Branch_1.0.2_aarch64-copy.dmg",
                },
                "macOS Apple Silicon DMG",
            )

    def test_macos_dmg_assets_selects_apple_silicon_and_intel_dmgs(self):
        self.assertEqual(
            macos_dmg_assets(
                {
                    "CC.Branch_1.0.2_aarch64.dmg",
                    "CC.Branch_1.0.2_x64.dmg",
                    "cc-branch_1.0.2_x64_en-US.msi",
                }
            ),
            {
                "apple_silicon": "CC.Branch_1.0.2_aarch64.dmg",
                "intel": "CC.Branch_1.0.2_x64.dmg",
            },
        )

    def test_release_view_command_uses_latest_when_tag_is_omitted(self):
        self.assertEqual(
            release_view_command(None, "owner/repo"),
            [
                "gh",
                "release",
                "view",
                "--json",
                "assets,body,isDraft,isPrerelease,name,tagName,url",
                "--repo",
                "owner/repo",
            ],
        )

    def test_release_download_command_downloads_exact_patterns(self):
        self.assertEqual(
            release_download_command(
                "v1.0.2",
                Path("/tmp/release"),
                ["latest.json", "CC Branch.app.tar.gz"],
                "owner/repo",
            ),
            [
                "gh",
                "release",
                "download",
                "v1.0.2",
                "--dir",
                "/tmp/release",
                "--clobber",
                "--pattern",
                "latest.json",
                "--pattern",
                "CC Branch.app.tar.gz",
                "--repo",
                "owner/repo",
            ],
        )

    def test_verify_github_release_is_latest_rejects_old_latest_release(self):
        with mock.patch(
            "scripts.verify_github_release.run_json",
            return_value={"tagName": "v1.0.1", "url": "https://github.com/example/releases/tag/v1.0.1"},
        ):
            with self.assertRaisesRegex(ValueError, "GitHub latest release is v1.0.1"):
                verify_github_release_is_latest("v1.0.2", "owner/repo", timeout=0)

    def test_verify_github_release_is_latest_accepts_expected_tag(self):
        with mock.patch(
            "scripts.verify_github_release.run_json",
            return_value={"tagName": "v1.0.2", "url": "https://github.com/example/releases/tag/v1.0.2"},
        ):
            result = verify_github_release_is_latest("v1.0.2", "owner/repo")

        self.assertEqual(result["tagName"], "v1.0.2")

    def test_verify_github_release_rejects_draft_when_public_release_is_required(self):
        release = {
            "tagName": "v1.0.2",
            "name": "CC Branch Desktop v1.0.2",
            "url": "https://github.com/example/releases/tag/v1.0.2",
            "body": "release body with direct links",
            "isDraft": True,
            "isPrerelease": False,
            "assets": [],
        }

        with mock.patch("scripts.verify_github_release.run_json", return_value=release):
            with self.assertRaisesRegex(ValueError, "draft"):
                verify_github_release(
                    tag="v1.0.2",
                    repo="owner/repo",
                    verify_dmg_download=False,
                    require_public=True,
                )

    def test_verify_github_release_rejects_prerelease_when_public_release_is_required(self):
        release = {
            "tagName": "v1.0.2",
            "name": "CC Branch Desktop v1.0.2",
            "url": "https://github.com/example/releases/tag/v1.0.2",
            "body": "release body with direct links",
            "isDraft": False,
            "isPrerelease": True,
            "assets": [],
        }

        with mock.patch("scripts.verify_github_release.run_json", return_value=release):
            with self.assertRaisesRegex(ValueError, "prerelease"):
                verify_github_release(
                    tag="v1.0.2",
                    repo="owner/repo",
                    verify_dmg_download=False,
                    require_public=True,
                )

    def test_verify_github_release_is_latest_retries_until_expected_tag(self):
        with mock.patch(
            "scripts.verify_github_release.run_json",
            side_effect=[
                {"tagName": "v1.0.1", "url": "https://github.com/example/releases/tag/v1.0.1"},
                {"tagName": "v1.0.2", "url": "https://github.com/example/releases/tag/v1.0.2"},
            ],
        ) as run_json, \
             mock.patch("scripts.verify_github_release.time.sleep") as sleep:
            result = verify_github_release_is_latest(
                "v1.0.2",
                "owner/repo",
                timeout=10,
                poll_interval=0.1,
            )

        self.assertEqual(result["tagName"], "v1.0.2")
        self.assertEqual(run_json.call_count, 2)
        sleep.assert_called_once_with(0.1)

    def test_verify_macos_dmg_asset_passes_launch_flag(self):
        with mock.patch("importlib.util.spec_from_file_location") as spec_from_file_location, \
             mock.patch("importlib.util.module_from_spec") as module_from_spec:
            module = mock.Mock()
            module.verify_dmg.return_value = {"ok": True, "launch": {"ok": True}}
            module_from_spec.return_value = module
            loader = mock.Mock()
            spec_from_file_location.return_value = mock.Mock(loader=loader)

            result = verify_macos_dmg_asset(Path("/tmp/CC.Branch.dmg"), launch_app=True)

        self.assertTrue(result["ok"])
        module.verify_dmg.assert_called_once_with(
            Path("/tmp/CC.Branch.dmg"),
            expected_app_name="CC Branch.app",
            launch_app=True,
            verify_installed_copy=False,
            verify_stale_backend_rejection=True,
            verify_gatekeeper_check=False,
            expected_version=None,
        )

    def test_verify_macos_dmg_asset_passes_installed_copy_flag(self):
        with mock.patch("importlib.util.spec_from_file_location") as spec_from_file_location, \
             mock.patch("importlib.util.module_from_spec") as module_from_spec:
            module = mock.Mock()
            module.verify_dmg.return_value = {
                "ok": True,
                "installed_copy": {
                    "launch": {"ok": True, "backend_source": "bundled-sidecar"}
                },
            }
            module_from_spec.return_value = module
            loader = mock.Mock()
            spec_from_file_location.return_value = mock.Mock(loader=loader)

            result = verify_macos_dmg_asset(
                Path("/tmp/CC.Branch.dmg"),
                launch_app=False,
                verify_installed_copy=True,
            )

        self.assertTrue(result["ok"])
        module.verify_dmg.assert_called_once_with(
            Path("/tmp/CC.Branch.dmg"),
            expected_app_name="CC Branch.app",
            launch_app=False,
            verify_installed_copy=True,
            verify_stale_backend_rejection=False,
            verify_gatekeeper_check=False,
            expected_version=None,
        )

    def test_verify_macos_dmg_asset_passes_gatekeeper_flag(self):
        with mock.patch("importlib.util.spec_from_file_location") as spec_from_file_location, \
             mock.patch("importlib.util.module_from_spec") as module_from_spec:
            module = mock.Mock()
            module.verify_dmg.return_value = {"ok": True, "gatekeeper": {"ok": True}}
            module_from_spec.return_value = module
            loader = mock.Mock()
            spec_from_file_location.return_value = mock.Mock(loader=loader)

            result = verify_macos_dmg_asset(
                Path("/tmp/CC.Branch.dmg"),
                launch_app=False,
                verify_gatekeeper_check=True,
                expected_version="1.0.2",
            )

        self.assertTrue(result["ok"])
        module.verify_dmg.assert_called_once_with(
            Path("/tmp/CC.Branch.dmg"),
            expected_app_name="CC Branch.app",
            launch_app=False,
            verify_installed_copy=False,
            verify_stale_backend_rejection=False,
            verify_gatekeeper_check=True,
            expected_version="1.0.2",
        )

    def test_verify_platform_installers_delegates_to_installer_verifier(self):
        with mock.patch("importlib.util.spec_from_file_location") as spec_from_file_location, \
             mock.patch("importlib.util.module_from_spec") as module_from_spec:
            module = mock.Mock()
            module.verify_installers.return_value = {"ok": True, "platform": "linux"}
            module_from_spec.return_value = module
            loader = mock.Mock()
            spec_from_file_location.return_value = mock.Mock(loader=loader)

            result = verify_platform_installers(
                Path("/tmp/release"),
                "linux",
                launch_appimage=True,
                launch_linux_packages=True,
                launch_windows_msi=True,
                launch_windows_nsis=True,
            )

        self.assertTrue(result["ok"])
        module.verify_installers.assert_called_once_with(
            Path("/tmp/release"),
            "linux",
            expected_version=None,
            launch_appimage=True,
            launch_linux_packages=True,
            launch_windows_msi=True,
            launch_windows_nsis=True,
        )

    def test_verify_github_release_downloads_and_launches_windows_msi_and_nsis(self):
        release = {
            "tagName": "v1.0.2",
            "name": "CC Branch Desktop v1.0.2",
            "url": "https://github.com/example/releases/tag/v1.0.2",
            "body": "release body with direct links",
            "isDraft": False,
            "isPrerelease": False,
            "assets": [
                {"name": "latest.json", "size": 100},
                {"name": "CC Branch_aarch64.app.tar.gz", "size": 100},
                {"name": "CC Branch_aarch64.app.tar.gz.sig", "size": 10},
                {"name": "CC Branch_x64.app.tar.gz", "size": 100},
                {"name": "CC Branch_x64.app.tar.gz.sig", "size": 10},
                {"name": "CC.Branch_1.0.2_aarch64.dmg", "size": 100},
                {"name": "CC.Branch_1.0.2_x64.dmg", "size": 100},
                {"name": "cc-branch_1.0.2_x64_en-US.msi", "size": 100},
                {"name": "cc-branch_1.0.2_x64_en-US.msi.sig", "size": 10},
                {"name": "cc-branch_1.0.2_x64-setup.exe", "size": 100},
                {"name": "cc-branch_1.0.2_amd64.AppImage", "size": 100},
                {"name": "cc-branch_1.0.2_amd64.AppImage.sig", "size": 10},
                {"name": "CC.Branch_1.0.2_amd64.deb", "size": 100},
                {"name": "CC.Branch-1.0.2-1.x86_64.rpm", "size": 100},
            ],
        }
        download_commands = []

        def fake_run(command):
            download_commands.append(command)
            if "--pattern" in command and "latest.json" in command:
                destination = Path(command[command.index("--dir") + 1])
                (destination / "latest.json").write_text(
                    '{"version":"1.0.2","platforms":{"darwin-aarch64":{"url":"https://example.test/CC%20Branch_aarch64.app.tar.gz","signature":"sig"},"darwin-x86_64":{"url":"https://example.test/CC%20Branch_x64.app.tar.gz","signature":"sig"},"windows-x86_64":{"url":"https://example.test/cc-branch_1.0.2_x64_en-US.msi","signature":"sig"},"linux-x86_64":{"url":"https://example.test/cc-branch_1.0.2_amd64.AppImage","signature":"sig"}}}',
                    encoding="utf-8",
                )

        with mock.patch("scripts.verify_github_release.run_json", return_value=release), \
             mock.patch("scripts.verify_github_release.run", side_effect=fake_run), \
             mock.patch("scripts.verify_github_release.verify_release_dir", return_value={
                 "ok": True,
                 "download_assets": {
                     "Windows MSI": "cc-branch_1.0.2_x64_en-US.msi",
                     "Windows NSIS setup": "cc-branch_1.0.2_x64-setup.exe",
                 },
             }) as release_dir, \
             mock.patch(
                 "scripts.verify_github_release.validate_checksum_manifest",
                 return_value={
                     "checked": True,
                     "asset": "SHA256SUMS",
                     "covered_assets": [
                         "cc-branch_1.0.2_x64_en-US.msi",
                         "cc-branch_1.0.2_x64-setup.exe",
                     ],
                     "verified_assets": [
                         "cc-branch_1.0.2_x64_en-US.msi",
                         "cc-branch_1.0.2_x64-setup.exe",
                     ],
                 },
             ) as checksum_manifest, \
             mock.patch(
                 "scripts.verify_github_release.verify_platform_installers",
                 return_value={
                     "ok": True,
                     "platform": "windows",
                     "msi": {
                         "launch": {
                             "ok": True,
                             "backend_source": "bundled-sidecar",
                             "port_mode": "auto",
                             **WINDOWS_DESKTOP_METADATA,
                         },
                         "stale_backend_rejection": {
                             "ok": True,
                             "expected_error": "Unexpected backend",
                         },
                     },
                     "nsis": {
                         "launch": {
                             "ok": True,
                             "backend_source": "bundled-sidecar",
                             "port_mode": "auto",
                             **WINDOWS_DESKTOP_METADATA,
                         },
                         "stale_backend_rejection": {
                             "ok": True,
                             "expected_error": "Unexpected backend",
                         },
                     },
                 },
             ) as installers:
            result = verify_github_release(
                tag="v1.0.2",
                repo="owner/repo",
                expected_version="1.0.2",
                verify_dmg_download=False,
                verify_windows_installer=True,
                launch_windows_msi=True,
                launch_windows_nsis=True,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["repo"], "owner/repo")
        self.assertEqual(result["tag"], "v1.0.2")
        self.assertEqual(release_dir.call_args.kwargs["release_notes_body"], release["body"])
        self.assertEqual(release_dir.call_args.kwargs["repo"], "owner/repo")
        self.assertEqual(release_dir.call_args.kwargs["tag"], "v1.0.2")
        self.assertEqual(
            result["checksum_manifest"]["verified_assets"],
            [
                "cc-branch_1.0.2_x64_en-US.msi",
                "cc-branch_1.0.2_x64-setup.exe",
            ],
        )
        self.assertEqual(
            result["verification_summary"]["checksum_manifest"],
            {
                "required_assets": [
                    "cc-branch_1.0.2_x64-setup.exe",
                    "cc-branch_1.0.2_x64_en-US.msi",
                ],
                "verified_assets": [
                    "cc-branch_1.0.2_x64-setup.exe",
                    "cc-branch_1.0.2_x64_en-US.msi",
                ],
            },
        )
        self.assertTrue(
            result["verification_summary"]["checks"]["all_required_checksum_assets_verified"]
        )
        checksum_manifest.assert_called_once()
        self.assertTrue(
            any(
                "CC Branch_aarch64.app.tar.gz" in command
                and "CC Branch_aarch64.app.tar.gz.sig" in command
                and "CC Branch_x64.app.tar.gz" in command
                and "CC Branch_x64.app.tar.gz.sig" in command
                and "cc-branch_1.0.2_x64_en-US.msi.sig" in command
                and "cc-branch_1.0.2_amd64.AppImage.sig" in command
                for command in download_commands
            )
        )
        self.assertTrue(
            any(
                "cc-branch_1.0.2_x64_en-US.msi" in command
                and "cc-branch_1.0.2_x64-setup.exe" in command
                for command in download_commands
            )
        )
        installers.assert_called_once()
        self.assertTrue(installers.call_args.kwargs["launch_windows_msi"])
        self.assertTrue(installers.call_args.kwargs["launch_windows_nsis"])

    def test_verify_github_release_rejects_missing_checksum_verification_for_downloaded_installer(self):
        release = {
            "tagName": "v1.0.2",
            "name": "CC Branch Desktop v1.0.2",
            "url": "https://github.com/example/releases/tag/v1.0.2",
            "body": "release body with direct links",
            "isDraft": False,
            "isPrerelease": False,
            "assets": [
                {"name": "latest.json", "size": 100},
                {"name": "CC Branch_aarch64.app.tar.gz", "size": 100},
                {"name": "CC Branch_aarch64.app.tar.gz.sig", "size": 10},
                {"name": "CC Branch_x64.app.tar.gz", "size": 100},
                {"name": "CC Branch_x64.app.tar.gz.sig", "size": 10},
                {"name": "CC.Branch_1.0.2_aarch64.dmg", "size": 100},
                {"name": "CC.Branch_1.0.2_x64.dmg", "size": 100},
                {"name": "cc-branch_1.0.2_x64_en-US.msi", "size": 100},
                {"name": "cc-branch_1.0.2_x64_en-US.msi.sig", "size": 10},
                {"name": "cc-branch_1.0.2_x64-setup.exe", "size": 100},
                {"name": "cc-branch_1.0.2_amd64.AppImage", "size": 100},
                {"name": "cc-branch_1.0.2_amd64.AppImage.sig", "size": 10},
                {"name": "CC.Branch_1.0.2_amd64.deb", "size": 100},
                {"name": "CC.Branch-1.0.2-1.x86_64.rpm", "size": 100},
            ],
        }

        def fake_run(command):
            if "--pattern" in command and "latest.json" in command:
                destination = Path(command[command.index("--dir") + 1])
                (destination / "latest.json").write_text(
                    '{"version":"1.0.2","platforms":{"darwin-aarch64":{"url":"https://example.test/CC%20Branch_aarch64.app.tar.gz","signature":"sig"},"darwin-x86_64":{"url":"https://example.test/CC%20Branch_x64.app.tar.gz","signature":"sig"},"windows-x86_64":{"url":"https://example.test/cc-branch_1.0.2_x64_en-US.msi","signature":"sig"},"linux-x86_64":{"url":"https://example.test/cc-branch_1.0.2_amd64.AppImage","signature":"sig"}}}',
                    encoding="utf-8",
                )

        with mock.patch("scripts.verify_github_release.run_json", return_value=release), \
             mock.patch("scripts.verify_github_release.run", side_effect=fake_run), \
             mock.patch("scripts.verify_github_release.verify_release_dir", return_value={
                 "ok": True,
                 "download_assets": {
                     "Windows MSI": "cc-branch_1.0.2_x64_en-US.msi",
                     "Windows NSIS setup": "cc-branch_1.0.2_x64-setup.exe",
                 },
             }), \
             mock.patch(
                 "scripts.verify_github_release.validate_checksum_manifest",
                 return_value={
                     "checked": True,
                     "asset": "SHA256SUMS",
                     "covered_assets": [
                         "cc-branch_1.0.2_x64_en-US.msi",
                         "cc-branch_1.0.2_x64-setup.exe",
                     ],
                     "verified_assets": ["cc-branch_1.0.2_x64_en-US.msi"],
                 },
             ), \
             mock.patch(
                 "scripts.verify_github_release.verify_platform_installers",
                 return_value={
                     "ok": True,
                     "platform": "windows",
                     "msi": {
                         "launch": {"ok": True, "backend_source": "bundled-sidecar", "port_mode": "auto", **WINDOWS_DESKTOP_METADATA},
                         "stale_backend_rejection": {"ok": True, "expected_error": "Unexpected backend"},
                     },
                     "nsis": {
                         "launch": {"ok": True, "backend_source": "bundled-sidecar", "port_mode": "auto", **WINDOWS_DESKTOP_METADATA},
                         "stale_backend_rejection": {"ok": True, "expected_error": "Unexpected backend"},
                     },
                 },
             ):
            with self.assertRaisesRegex(ValueError, "checksum"):
                verify_github_release(
                    tag="v1.0.2",
                    repo="owner/repo",
                    expected_version="1.0.2",
                    verify_dmg_download=False,
                    verify_windows_installer=True,
                    launch_windows_msi=True,
                    launch_windows_nsis=True,
                )

    def test_verify_github_release_summarizes_launch_backend_sources(self):
        release = {
            "tagName": "v1.0.2",
            "name": "CC Branch Desktop v1.0.2",
            "url": "https://github.com/example/releases/tag/v1.0.2",
            "body": "release body with direct links",
            "isDraft": False,
            "isPrerelease": False,
            "assets": [
                {"name": "latest.json", "size": 100},
                {"name": "CC Branch_aarch64.app.tar.gz", "size": 100},
                {"name": "CC Branch_aarch64.app.tar.gz.sig", "size": 10},
                {"name": "CC Branch_x64.app.tar.gz", "size": 100},
                {"name": "CC Branch_x64.app.tar.gz.sig", "size": 10},
                {"name": "CC.Branch_1.0.2_aarch64.dmg", "size": 100},
                {"name": "CC.Branch_1.0.2_x64.dmg", "size": 100},
                {"name": "cc-branch_1.0.2_x64_en-US.msi", "size": 100},
                {"name": "cc-branch_1.0.2_x64_en-US.msi.sig", "size": 10},
                {"name": "cc-branch_1.0.2_x64-setup.exe", "size": 100},
                {"name": "cc-branch_1.0.2_amd64.AppImage", "size": 100},
                {"name": "cc-branch_1.0.2_amd64.AppImage.sig", "size": 10},
                {"name": "CC.Branch_1.0.2_amd64.deb", "size": 100},
                {"name": "CC.Branch-1.0.2-1.x86_64.rpm", "size": 100},
            ],
        }

        def fake_run(command):
            if "--pattern" in command and "latest.json" in command:
                destination = Path(command[command.index("--dir") + 1])
                (destination / "latest.json").write_text(
                    '{"version":"1.0.2","platforms":{"darwin-aarch64":{"url":"https://example.test/CC%20Branch_aarch64.app.tar.gz","signature":"sig"},"darwin-x86_64":{"url":"https://example.test/CC%20Branch_x64.app.tar.gz","signature":"sig"},"windows-x86_64":{"url":"https://example.test/cc-branch_1.0.2_x64_en-US.msi","signature":"sig"},"linux-x86_64":{"url":"https://example.test/cc-branch_1.0.2_amd64.AppImage","signature":"sig"}}}',
                    encoding="utf-8",
                )

        with mock.patch("scripts.verify_github_release.run_json", return_value=release), \
             mock.patch("scripts.verify_github_release.run", side_effect=fake_run), \
             mock.patch(
                 "scripts.verify_github_release.verify_release_dir",
                 return_value={
                     "ok": True,
                     "release_notes": {"checked": True},
                     "latest_notes": {"checked": True},
                 },
             ), \
             mock.patch(
                 "scripts.verify_github_release.verify_platform_installers",
                 return_value={
                     "ok": True,
                     "platform": "linux",
                     "deb": {
                        "launch": {
                            "ok": True,
                            "backend_source": "bundled-sidecar",
                            "port_mode": "auto",
                            **DESKTOP_METADATA,
                        },
                         "stale_backend_rejection": {
                             "ok": True,
                             "expected_error": "Unexpected backend",
                         },
                     },
                     "rpm": {
                        "launch": {
                            "ok": True,
                            "backend_source": "bundled-sidecar",
                            "port_mode": "auto",
                            **DESKTOP_METADATA,
                        },
                         "stale_backend_rejection": {
                             "ok": True,
                             "expected_error": "Unexpected backend",
                         },
                     },
                     "appimage": {
                        "launch": {
                            "ok": True,
                            "backend_source": "bundled-sidecar",
                            "port_mode": "auto",
                            **DESKTOP_METADATA,
                        },
                         "stale_backend_rejection": {
                             "ok": True,
                             "expected_error": "Unexpected backend",
                         },
                     },
                 },
             ):
            result = verify_github_release(
                tag="v1.0.2",
                repo="owner/repo",
                expected_version="1.0.2",
                verify_dmg_download=False,
                verify_linux_installers=True,
                launch_linux_packages=True,
                launch_linux_appimage=True,
                require_latest=True,
                require_public=True,
            )

        self.assertEqual(
            result["launch_backend_sources"],
            {
                "linux.appimage": "bundled-sidecar",
                "linux.deb": "bundled-sidecar",
                "linux.rpm": "bundled-sidecar",
            },
        )
        self.assertEqual(
            result["launch_desktop_metadata"],
            {
                "linux.appimage": DESKTOP_METADATA,
                "linux.deb": DESKTOP_METADATA,
                "linux.rpm": DESKTOP_METADATA,
            },
        )
        self.assertEqual(
            result["launch_port_modes"],
            {
                "linux.appimage": "auto",
                "linux.deb": "auto",
                "linux.rpm": "auto",
            },
        )
        self.assertEqual(
            result["stale_backend_rejections"],
            {
                "linux.appimage": "Unexpected backend",
                "linux.deb": "Unexpected backend",
                "linux.rpm": "Unexpected backend",
            },
        )
        self.assertEqual(
            result["verification_summary"],
            {
                "required_launch_labels": [
                    "linux.appimage",
                    "linux.deb",
                    "linux.rpm",
                ],
                "required_stale_backend_rejection_labels": [
                    "linux.appimage",
                    "linux.deb",
                    "linux.rpm",
                ],
                "release_state": {
                    "repo": "owner/repo",
                    "tag": "v1.0.2",
                    "url": "https://github.com/example/releases/tag/v1.0.2",
                    "is_public": True,
                    "is_draft": False,
                    "is_prerelease": False,
                    "public_required": True,
                    "latest_checked": True,
                    "latest_required": True,
                    "latest_matches_tag": True,
                    "latest_tag": "v1.0.2",
                    "latest_url": "https://github.com/example/releases/tag/v1.0.2",
                },
                "checks": {
                    "public_release_requirement_met": True,
                    "latest_release_requirement_met": True,
                    "all_required_launches_verified": True,
                    "all_required_stale_backend_rejections_verified": True,
                    "release_notes_verified": True,
                    "latest_json_notes_verified": True,
                    "all_launch_backend_sources_bundled_sidecar": True,
                    "all_launch_port_modes_auto": True,
                    "all_launch_desktop_metadata_present": True,
                    "all_required_checksum_assets_verified": True,
                },
                "ready_for_public_download": True,
                "launch_backend_sources": {
                    "linux.appimage": "bundled-sidecar",
                    "linux.deb": "bundled-sidecar",
                    "linux.rpm": "bundled-sidecar",
                },
                "launch_port_modes": {
                    "linux.appimage": "auto",
                    "linux.deb": "auto",
                    "linux.rpm": "auto",
                },
                "launch_desktop_metadata": {
                    "linux.appimage": DESKTOP_METADATA,
                    "linux.deb": DESKTOP_METADATA,
                    "linux.rpm": DESKTOP_METADATA,
                },
                "stale_backend_rejections": {
                    "linux.appimage": "Unexpected backend",
                    "linux.deb": "Unexpected backend",
                    "linux.rpm": "Unexpected backend",
                },
                "checksum_manifest": {
                    "required_assets": [],
                    "verified_assets": [],
                },
            },
        )

    def test_verify_github_release_reports_intel_dmg_launch_backend_source(self):
        release = {
            "tagName": "v1.0.2",
            "name": "CC Branch Desktop v1.0.2",
            "url": "https://github.com/example/releases/tag/v1.0.2",
            "body": "release body with direct links",
            "assets": [
                {"name": "latest.json", "size": 100},
                {"name": "CC Branch_aarch64.app.tar.gz", "size": 100},
                {"name": "CC Branch_aarch64.app.tar.gz.sig", "size": 10},
                {"name": "CC Branch_x64.app.tar.gz", "size": 100},
                {"name": "CC Branch_x64.app.tar.gz.sig", "size": 10},
                {"name": "CC.Branch_1.0.2_aarch64.dmg", "size": 100},
                {"name": "CC.Branch_1.0.2_x64.dmg", "size": 100},
                {"name": "cc-branch_1.0.2_x64_en-US.msi", "size": 100},
                {"name": "cc-branch_1.0.2_x64_en-US.msi.sig", "size": 10},
                {"name": "cc-branch_1.0.2_x64-setup.exe", "size": 100},
                {"name": "cc-branch_1.0.2_amd64.AppImage", "size": 100},
                {"name": "cc-branch_1.0.2_amd64.AppImage.sig", "size": 10},
                {"name": "CC.Branch_1.0.2_amd64.deb", "size": 100},
                {"name": "CC.Branch-1.0.2-1.x86_64.rpm", "size": 100},
            ],
        }

        def fake_run(command):
            if "--pattern" in command and "latest.json" in command:
                destination = Path(command[command.index("--dir") + 1])
                (destination / "latest.json").write_text(
                    '{"version":"1.0.2","platforms":{"darwin-aarch64":{"url":"https://example.test/CC%20Branch_aarch64.app.tar.gz","signature":"sig"},"darwin-x86_64":{"url":"https://example.test/CC%20Branch_x64.app.tar.gz","signature":"sig"},"windows-x86_64":{"url":"https://example.test/cc-branch_1.0.2_x64_en-US.msi","signature":"sig"},"linux-x86_64":{"url":"https://example.test/cc-branch_1.0.2_amd64.AppImage","signature":"sig"}}}',
                    encoding="utf-8",
                )

        def fake_verify_dmg(
            path,
            *,
            launch_app,
            verify_stale_backend_rejection,
            verify_gatekeeper_check,
            expected_version,
            verify_installed_copy=False,
        ):
            return {
                "ok": True,
                "asset": path.name,
                "bundle_version": expected_version,
                "launch": {
                    "ok": True,
                    "backend_source": "bundled-sidecar",
                    "port_mode": "auto",
                    "desktop_version": "1.0.2",
                    "desktop_platform": "darwin",
                    "desktop_arch": "x86_64",
                } if launch_app else None,
                "installed_copy": {
                    "launch": {
                        "ok": True,
                        "backend_source": "bundled-sidecar",
                        "port_mode": "auto",
                        "desktop_version": "1.0.2",
                        "desktop_platform": "darwin",
                        "desktop_arch": "x86_64",
                    }
                } if verify_installed_copy else None,
                "stale_backend_rejection": {
                    "ok": True,
                    "expected_error": "Unexpected backend",
                } if verify_stale_backend_rejection else None,
                "gatekeeper": {"ok": True} if verify_gatekeeper_check else None,
            }

        with mock.patch("scripts.verify_github_release.run_json", return_value=release), \
             mock.patch("scripts.verify_github_release.run", side_effect=fake_run), \
             mock.patch("scripts.verify_github_release.verify_release_dir", return_value={"ok": True}), \
             mock.patch("scripts.verify_github_release.verify_macos_dmg_asset", side_effect=fake_verify_dmg) as verify_dmg:
            result = verify_github_release(
                tag="v1.0.2",
                repo="owner/repo",
                expected_version="1.0.2",
                sample_platform="darwin-x86_64",
                verify_dmg_download=True,
                launch_dmg_app=True,
                verify_macos_gatekeeper=True,
            )

        self.assertEqual(
            result["launch_backend_sources"],
            {"macos.intel": "bundled-sidecar"},
        )
        self.assertEqual(
            result["launch_desktop_metadata"],
            {
                "macos.intel": {
                    "desktop_version": "1.0.2",
                    "desktop_platform": "darwin",
                    "desktop_arch": "x86_64",
                }
            },
        )
        self.assertEqual(
            result["stale_backend_rejections"],
            {"macos.intel": "Unexpected backend"},
        )
        self.assertEqual(result["launch_port_modes"], {"macos.intel": "auto"})
        self.assertIsNone(result["macos_dmgs"]["apple_silicon"]["launch"])
        self.assertEqual(result["macos_dmgs"]["intel"]["asset"], "CC.Branch_1.0.2_x64.dmg")
        self.assertEqual(result["macos_dmgs"]["intel"]["bundle_version"], "1.0.2")
        self.assertEqual(verify_dmg.call_count, 2)

    def test_verify_github_release_rejects_missing_requested_dmg_launch_evidence(self):
        release = {
            "tagName": "v1.0.2",
            "name": "CC Branch Desktop v1.0.2",
            "url": "https://github.com/example/releases/tag/v1.0.2",
            "body": "release body with direct links",
            "assets": [
                {"name": "latest.json", "size": 100},
                {"name": "CC Branch_aarch64.app.tar.gz", "size": 100},
                {"name": "CC Branch_aarch64.app.tar.gz.sig", "size": 10},
                {"name": "CC Branch_x64.app.tar.gz", "size": 100},
                {"name": "CC Branch_x64.app.tar.gz.sig", "size": 10},
                {"name": "CC.Branch_1.0.2_aarch64.dmg", "size": 100},
                {"name": "CC.Branch_1.0.2_x64.dmg", "size": 100},
                {"name": "cc-branch_1.0.2_x64_en-US.msi", "size": 100},
                {"name": "cc-branch_1.0.2_x64_en-US.msi.sig", "size": 10},
                {"name": "cc-branch_1.0.2_x64-setup.exe", "size": 100},
                {"name": "cc-branch_1.0.2_amd64.AppImage", "size": 100},
                {"name": "cc-branch_1.0.2_amd64.AppImage.sig", "size": 10},
                {"name": "CC.Branch_1.0.2_amd64.deb", "size": 100},
                {"name": "CC.Branch-1.0.2-1.x86_64.rpm", "size": 100},
            ],
        }

        def fake_run(command):
            if "--pattern" in command and "latest.json" in command:
                destination = Path(command[command.index("--dir") + 1])
                (destination / "latest.json").write_text(
                    '{"version":"1.0.2","platforms":{"darwin-aarch64":{"url":"https://example.test/CC%20Branch_aarch64.app.tar.gz","signature":"sig"},"darwin-x86_64":{"url":"https://example.test/CC%20Branch_x64.app.tar.gz","signature":"sig"},"windows-x86_64":{"url":"https://example.test/cc-branch_1.0.2_x64_en-US.msi","signature":"sig"},"linux-x86_64":{"url":"https://example.test/cc-branch_1.0.2_amd64.AppImage","signature":"sig"}}}',
                    encoding="utf-8",
                )

        with mock.patch("scripts.verify_github_release.run_json", return_value=release), \
             mock.patch("scripts.verify_github_release.run", side_effect=fake_run), \
             mock.patch("scripts.verify_github_release.verify_release_dir", return_value={"ok": True}), \
            mock.patch(
                "scripts.verify_github_release.verify_macos_dmg_asset",
                return_value={"ok": True, "launch": None},
            ):
            with self.assertRaisesRegex(ValueError, "required launch verification: macos.intel"):
                verify_github_release(
                    tag="v1.0.2",
                    repo="owner/repo",
                    expected_version="1.0.2",
                    sample_platform="darwin-x86_64",
                    verify_dmg_download=True,
                    launch_dmg_app=True,
                )

    def test_verify_github_release_rejects_missing_stale_backend_rejection_evidence(self):
        release = {
            "tagName": "v1.0.2",
            "name": "CC Branch Desktop v1.0.2",
            "url": "https://github.com/example/releases/tag/v1.0.2",
            "body": "release body with direct links",
            "assets": [
                {"name": "latest.json", "size": 100},
                {"name": "CC Branch_aarch64.app.tar.gz", "size": 100},
                {"name": "CC Branch_aarch64.app.tar.gz.sig", "size": 10},
                {"name": "CC Branch_x64.app.tar.gz", "size": 100},
                {"name": "CC Branch_x64.app.tar.gz.sig", "size": 10},
                {"name": "cc-branch_1.0.2_amd64.AppImage", "size": 100},
                {"name": "cc-branch_1.0.2_amd64.AppImage.sig", "size": 10},
                {"name": "CC.Branch_1.0.2_amd64.deb", "size": 100},
                {"name": "CC.Branch-1.0.2-1.x86_64.rpm", "size": 100},
            ],
        }

        def fake_run(command):
            if "--pattern" in command and "latest.json" in command:
                destination = Path(command[command.index("--dir") + 1])
                (destination / "latest.json").write_text(
                    '{"version":"1.0.2","platforms":{"darwin-aarch64":{"url":"https://example.test/CC%20Branch_aarch64.app.tar.gz","signature":"sig"},"darwin-x86_64":{"url":"https://example.test/CC%20Branch_x64.app.tar.gz","signature":"sig"},"linux-x86_64":{"url":"https://example.test/cc-branch_1.0.2_amd64.AppImage","signature":"sig"}}}',
                    encoding="utf-8",
                )

        with mock.patch("scripts.verify_github_release.run_json", return_value=release), \
             mock.patch("scripts.verify_github_release.run", side_effect=fake_run), \
             mock.patch("scripts.verify_github_release.verify_release_dir", return_value={"ok": True}), \
             mock.patch(
                 "scripts.verify_github_release.verify_platform_installers",
                 return_value={
                     "ok": True,
                     "platform": "linux",
                     "appimage": {
                         "launch": {
                             "ok": True,
                             "backend_source": "bundled-sidecar",
                             "port_mode": "auto",
                             **DESKTOP_METADATA,
                         },
                     },
                 },
             ):
            with self.assertRaisesRegex(ValueError, "stale backend rejection verification: linux.appimage"):
                verify_github_release(
                    tag="v1.0.2",
                    repo="owner/repo",
                    expected_version="1.0.2",
                    verify_dmg_download=False,
                    verify_linux_installers=True,
                    launch_linux_appimage=True,
                )

    def test_verify_github_release_rejects_missing_requested_launch_desktop_metadata(self):
        release = {
            "tagName": "v1.0.2",
            "name": "CC Branch Desktop v1.0.2",
            "url": "https://github.com/example/releases/tag/v1.0.2",
            "body": "release body with direct links",
            "assets": [
                {"name": "latest.json", "size": 100},
                {"name": "CC Branch_aarch64.app.tar.gz", "size": 100},
                {"name": "CC Branch_aarch64.app.tar.gz.sig", "size": 10},
                {"name": "CC Branch_x64.app.tar.gz", "size": 100},
                {"name": "CC Branch_x64.app.tar.gz.sig", "size": 10},
                {"name": "cc-branch_1.0.2_amd64.AppImage", "size": 100},
                {"name": "cc-branch_1.0.2_amd64.AppImage.sig", "size": 10},
                {"name": "CC.Branch_1.0.2_amd64.deb", "size": 100},
                {"name": "CC.Branch-1.0.2-1.x86_64.rpm", "size": 100},
            ],
        }

        def fake_run(command):
            if "--pattern" in command and "latest.json" in command:
                destination = Path(command[command.index("--dir") + 1])
                (destination / "latest.json").write_text(
                    '{"version":"1.0.2","platforms":{"darwin-aarch64":{"url":"https://example.test/CC%20Branch_aarch64.app.tar.gz","signature":"sig"},"darwin-x86_64":{"url":"https://example.test/CC%20Branch_x64.app.tar.gz","signature":"sig"},"linux-x86_64":{"url":"https://example.test/cc-branch_1.0.2_amd64.AppImage","signature":"sig"}}}',
                    encoding="utf-8",
                )

        with mock.patch("scripts.verify_github_release.run_json", return_value=release), \
             mock.patch("scripts.verify_github_release.run", side_effect=fake_run), \
             mock.patch("scripts.verify_github_release.verify_release_dir", return_value={"ok": True}), \
             mock.patch(
                 "scripts.verify_github_release.verify_platform_installers",
                 return_value={
                     "ok": True,
                     "platform": "linux",
                     "appimage": {
                         "launch": {
                             "ok": True,
                             "backend_source": "bundled-sidecar",
                         },
                         "stale_backend_rejection": {
                             "ok": True,
                             "expected_error": "Unexpected backend",
                         },
                     },
                 },
             ):
            with self.assertRaisesRegex(ValueError, "linux.appimage.*desktop_version"):
                verify_github_release(
                    tag="v1.0.2",
                    repo="owner/repo",
                    expected_version="1.0.2",
                    verify_dmg_download=False,
                    verify_linux_installers=True,
                    launch_linux_appimage=True,
                )

    def test_collect_launch_backend_sources_rejects_python_fallback(self):
        with self.assertRaisesRegex(ValueError, "linux.appimage.*python-fallback"):
            collect_launch_backend_sources(
                {
                    "linux": {
                        "appimage": {
                            "launch": {
                                "ok": True,
                                "backend_source": "python-fallback",
                            }
                        }
                    }
                }
            )

    def test_collect_launch_backend_sources_includes_installed_macos_copy(self):
        sources = collect_launch_backend_sources(
            {
                "macos_dmgs": {
                    "apple_silicon": {
                        "installed_copy": {
                            "launch": {
                                "ok": True,
                                "backend_source": "bundled-sidecar",
                            }
                        }
                    }
                }
            }
        )

        self.assertEqual(
            sources,
            {"macos.apple_silicon.installed_copy": "bundled-sidecar"},
        )

    def test_collect_launch_desktop_metadata_includes_installed_macos_copy(self):
        metadata = collect_launch_desktop_metadata(
            {
                "macos_dmgs": {
                    "apple_silicon": {
                        "installed_copy": {
                            "launch": {
                                "ok": True,
                                "backend_source": "bundled-sidecar",
                                "desktop_version": "1.0.2",
                                "desktop_platform": "darwin",
                                "desktop_arch": "aarch64",
                            }
                        }
                    }
                }
            }
        )

        self.assertEqual(
            metadata,
            {
                "macos.apple_silicon.installed_copy": {
                    "desktop_version": "1.0.2",
                    "desktop_platform": "darwin",
                    "desktop_arch": "aarch64",
                }
            },
        )

    def test_collect_launch_port_modes_requires_auto_for_user_download_launches(self):
        modes = collect_launch_port_modes(
            {
                "macos_dmgs": {
                    "apple_silicon": {
                        "installed_copy": {
                            "launch": {
                                "ok": True,
                                "backend_source": "bundled-sidecar",
                                "port_mode": "auto",
                            }
                        }
                    }
                },
                "linux": {
                    "appimage": {
                        "launch": {
                            "ok": True,
                            "backend_source": "bundled-sidecar",
                            "port_mode": "fixed",
                        }
                    }
                },
            }
        )

        self.assertEqual(
            modes,
            {
                "macos.apple_silicon.installed_copy": "auto",
                "linux.appimage": "fixed",
            },
        )
        with self.assertRaisesRegex(ValueError, "linux.appimage.*port_mode='fixed'"):
            require_launch_port_modes(modes, ["linux.appimage"])

    def test_collect_launch_port_modes_rejects_missing_port_mode(self):
        with self.assertRaisesRegex(ValueError, "linux.appimage.*port_mode"):
            collect_launch_port_modes(
                {
                    "linux": {
                        "appimage": {
                            "launch": {
                                "ok": True,
                                "backend_source": "bundled-sidecar",
                            }
                        }
                    }
                }
            )

    def test_collect_launch_desktop_metadata_rejects_blank_metadata(self):
        with self.assertRaisesRegex(ValueError, "linux.appimage.*desktop_platform"):
            collect_launch_desktop_metadata(
                {
                    "linux": {
                        "appimage": {
                            "launch": {
                                "ok": True,
                                "backend_source": "bundled-sidecar",
                                "desktop_version": "1.0.2",
                                "desktop_platform": "",
                                "desktop_arch": "x86_64",
                            }
                        }
                    }
                }
            )

    def test_require_launch_desktop_metadata_rejects_version_mismatch(self):
        with self.assertRaisesRegex(ValueError, "linux.appimage.*desktop_version"):
            require_launch_desktop_metadata(
                {
                    "linux.appimage": {
                        "desktop_version": "1.0.1",
                        "desktop_platform": "linux",
                        "desktop_arch": "x86_64",
                    }
                },
                ["linux.appimage"],
                expected_version="1.0.2",
            )

    def test_require_launch_desktop_metadata_rejects_platform_arch_mismatch(self):
        with self.assertRaisesRegex(ValueError, "macos.apple_silicon.*desktop_arch"):
            require_launch_desktop_metadata(
                {
                    "macos.apple_silicon": {
                        "desktop_version": "1.0.2",
                        "desktop_platform": "darwin",
                        "desktop_arch": "x86_64",
                    }
                },
                ["macos.apple_silicon"],
                expected_version="1.0.2",
            )

    def test_collect_launch_backend_sources_rejects_failed_launch_result(self):
        with self.assertRaisesRegex(ValueError, "macos.intel.*did not pass"):
            collect_launch_backend_sources(
                {
                    "macos_dmgs": {
                        "intel": {
                            "launch": {
                                "ok": False,
                                "backend_source": "bundled-sidecar",
                            }
                        }
                    }
                }
            )

    def test_collect_stale_backend_rejections_rejects_failed_rejection_result(self):
        with self.assertRaisesRegex(ValueError, "windows.msi.*did not pass"):
            collect_stale_backend_rejections(
                {
                    "windows": {
                        "msi": {
                            "stale_backend_rejection": {
                                "ok": False,
                                "expected_error": "Unexpected backend",
                            }
                        }
                    }
                }
            )


if __name__ == "__main__":
    unittest.main()
