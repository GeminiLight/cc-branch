import importlib.util
import os
import plistlib
import tempfile
import unittest
from unittest import mock
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify-macos-dmg.py"
SPEC = importlib.util.spec_from_file_location("verify_macos_dmg", SCRIPT_PATH)
assert SPEC and SPEC.loader
verify_macos_dmg = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_macos_dmg)


class VerifyMacosDmgTests(unittest.TestCase):
    def test_find_app_bundle_prefers_expected_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            mountpoint = Path(tmp)
            expected = mountpoint / "CC Branch.app"
            expected.mkdir()

            self.assertEqual(
                verify_macos_dmg.find_app_bundle(mountpoint, "CC Branch.app"),
                expected,
            )

    def test_find_app_bundle_rejects_wrong_single_app_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            mountpoint = Path(tmp)
            (mountpoint / "Other.app").mkdir()

            with self.assertRaisesRegex(FileNotFoundError, "CC Branch.app"):
                verify_macos_dmg.find_app_bundle(mountpoint, "CC Branch.app")

    def test_find_app_bundle_rejects_extra_apps_next_to_expected_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            mountpoint = Path(tmp)
            (mountpoint / "CC Branch.app").mkdir()
            (mountpoint / "Other.app").mkdir()

            with self.assertRaisesRegex(ValueError, "unexpected app bundle"):
                verify_macos_dmg.find_app_bundle(mountpoint, "CC Branch.app")

    def test_verify_applications_shortcut_requires_drag_install_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            mountpoint = Path(tmp)
            (mountpoint / "Applications").symlink_to("/Applications")

            result = verify_macos_dmg.verify_applications_shortcut(mountpoint)

        self.assertEqual(result["applications_shortcut"], "/Applications")

    def test_verify_applications_shortcut_rejects_missing_drag_install_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(FileNotFoundError, "Applications"):
                verify_macos_dmg.verify_applications_shortcut(Path(tmp))

    def test_verify_applications_shortcut_rejects_wrong_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            mountpoint = Path(tmp)
            (mountpoint / "Applications").symlink_to("/tmp")

            with self.assertRaisesRegex(ValueError, "/Applications"):
                verify_macos_dmg.verify_applications_shortcut(mountpoint)

    def test_verify_applications_shortcut_rejects_plain_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            mountpoint = Path(tmp)
            (mountpoint / "Applications").mkdir()

            with self.assertRaisesRegex(ValueError, "not a symlink"):
                verify_macos_dmg.verify_applications_shortcut(mountpoint)

    def test_verify_app_bundle_requires_backend_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "CC Branch.app"
            macos = app / "Contents" / "MacOS"
            macos.mkdir(parents=True)
            main = macos / "cc-branch"
            main.write_bytes(b"app")
            main.chmod(0o755)

            with self.assertRaisesRegex(FileNotFoundError, "backend sidecar"):
                verify_macos_dmg.verify_app_bundle_contains_backend(app)

    def test_verify_app_bundle_accepts_executable_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "CC Branch.app"
            macos = app / "Contents" / "MacOS"
            contents = app / "Contents"
            macos.mkdir(parents=True)
            (contents / "Info.plist").write_bytes(
                plistlib.dumps({"CFBundleShortVersionString": "1.0.2"})
            )
            main = macos / "cc-branch"
            backend = macos / "cc-branch-backend"
            main.write_bytes(b"app")
            backend.write_bytes(b"backend")
            main.chmod(0o755)
            backend.chmod(0o755)

            result = verify_macos_dmg.verify_app_bundle_contains_backend(app)

            self.assertEqual(Path(result["backend_path"]), backend)
            self.assertGreater(result["backend_size"], 0)
            self.assertEqual(Path(result["app_binary_path"]), main)
            self.assertEqual(result["bundle_version"], "1.0.2")
            self.assertTrue(os.access(backend, os.X_OK))

    def test_verify_app_bundle_rejects_wrong_bundle_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "CC Branch.app"
            macos = app / "Contents" / "MacOS"
            contents = app / "Contents"
            macos.mkdir(parents=True)
            (contents / "Info.plist").write_bytes(
                plistlib.dumps({"CFBundleShortVersionString": "1.0.1"})
            )
            main = macos / "cc-branch"
            backend = macos / "cc-branch-backend"
            main.write_bytes(b"app")
            backend.write_bytes(b"backend")
            main.chmod(0o755)
            backend.chmod(0o755)

            with self.assertRaisesRegex(ValueError, "does not match expected"):
                verify_macos_dmg.verify_app_bundle_contains_backend(
                    app,
                    expected_version="1.0.2",
                )

    def test_verify_dmg_can_launch_app_after_content_check(self):
        app = Path("/Volumes/CC Branch/CC Branch.app")
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(verify_macos_dmg.platform, "system", return_value="Darwin"), \
                 mock.patch.object(verify_macos_dmg.tempfile, "TemporaryDirectory") as temporary_directory, \
                 mock.patch.object(verify_macos_dmg, "attach_dmg") as attach_dmg, \
                 mock.patch.object(verify_macos_dmg, "detach_dmg") as detach_dmg, \
                 mock.patch.object(verify_macos_dmg, "find_app_bundle", return_value=app), \
                 mock.patch.object(verify_macos_dmg, "verify_applications_shortcut", return_value={"applications_shortcut": "/Applications"}), \
                 mock.patch.object(verify_macos_dmg, "verify_app_bundle_contains_backend", return_value={"app_path": str(app)}), \
                 mock.patch.object(
                     verify_macos_dmg,
                     "verify_app_launches_backend",
                     return_value={
                         "ok": True,
                         "port": 12345,
                         "backend_source": "bundled-sidecar",
                     },
                 ) as launch_app:
                temporary_directory.return_value.__enter__.return_value = tmp
                temporary_directory.return_value.__exit__.return_value = False
                dmg = Path(tmp) / "CC.Branch_1.0.2_aarch64.dmg"
                dmg.write_bytes(b"dmg")

                result = verify_macos_dmg.verify_dmg(
                    dmg,
                    expected_app_name="CC Branch.app",
                    launch_app=True,
                    expected_version="1.0.2",
                )

        self.assertTrue(result["launch"]["ok"])
        self.assertEqual(result["applications_shortcut"], "/Applications")
        self.assertEqual(result["launch"]["port"], 12345)
        launch_app.assert_called_once_with(
            app,
            timeout=30.0,
            expected_version="1.0.2",
            expected_platform="darwin",
            expected_arch="aarch64",
            use_auto_port=True,
        )
        attach_dmg.assert_called_once()
        detach_dmg.assert_called_once()

    def test_verify_dmg_can_launch_installed_copy_after_drag_install(self):
        app = Path("/Volumes/CC Branch/CC Branch.app")
        copied_app = Path("/private/tmp/cc-branch-install/Applications/CC Branch.app")
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(verify_macos_dmg.platform, "system", return_value="Darwin"), \
                 mock.patch.object(verify_macos_dmg.tempfile, "TemporaryDirectory") as temporary_directory, \
                 mock.patch.object(verify_macos_dmg, "attach_dmg") as attach_dmg, \
                 mock.patch.object(verify_macos_dmg, "detach_dmg") as detach_dmg, \
                 mock.patch.object(verify_macos_dmg, "find_app_bundle", return_value=app), \
                 mock.patch.object(verify_macos_dmg, "verify_applications_shortcut", return_value={"applications_shortcut": "/Applications"}), \
                 mock.patch.object(verify_macos_dmg, "verify_app_bundle_contains_backend", return_value={"app_path": str(app)}), \
                 mock.patch.object(
                     verify_macos_dmg,
                     "copy_app_bundle_for_install_verification",
                     return_value=copied_app,
                 ) as copy_app, \
                 mock.patch.object(
                     verify_macos_dmg,
                     "verify_app_launches_backend",
                     return_value={
                         "ok": True,
                         "port": 12345,
                         "backend_source": "bundled-sidecar",
                     },
                 ) as launch_app:
                temporary_directory.return_value.__enter__.return_value = tmp
                temporary_directory.return_value.__exit__.return_value = False
                dmg = Path(tmp) / "CC.Branch_1.0.2_aarch64.dmg"
                dmg.write_bytes(b"dmg")

                result = verify_macos_dmg.verify_dmg(
                    dmg,
                    expected_app_name="CC Branch.app",
                    verify_installed_copy=True,
                    expected_version="1.0.2",
                )

        self.assertEqual(result["installed_copy"]["app_path"], str(copied_app))
        self.assertEqual(result["installed_copy"]["launch"]["backend_source"], "bundled-sidecar")
        copy_app.assert_called_once()
        launch_app.assert_called_once_with(
            copied_app,
            timeout=30.0,
            expected_version="1.0.2",
            expected_platform="darwin",
            expected_arch="aarch64",
            use_auto_port=True,
        )
        attach_dmg.assert_called_once()
        detach_dmg.assert_called_once()

    def test_verify_dmg_can_verify_stale_backend_rejection_after_launch(self):
        app = Path("/Volumes/CC Branch/CC Branch.app")
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(verify_macos_dmg.platform, "system", return_value="Darwin"), \
                 mock.patch.object(verify_macos_dmg.tempfile, "TemporaryDirectory") as temporary_directory, \
                 mock.patch.object(verify_macos_dmg, "attach_dmg"), \
                 mock.patch.object(verify_macos_dmg, "detach_dmg"), \
                 mock.patch.object(verify_macos_dmg, "find_app_bundle", return_value=app), \
                 mock.patch.object(verify_macos_dmg, "verify_applications_shortcut", return_value={"applications_shortcut": "/Applications"}), \
                 mock.patch.object(verify_macos_dmg, "verify_app_bundle_contains_backend", return_value={"app_path": str(app)}), \
                 mock.patch.object(
                     verify_macos_dmg,
                     "verify_app_launches_backend",
                     return_value={
                         "ok": True,
                         "port": 12345,
                         "backend_source": "bundled-sidecar",
                     },
                 ), \
                 mock.patch.object(
                     verify_macos_dmg,
                     "verify_app_rejects_stale_backend",
                     return_value={
                         "ok": True,
                         "expected_error": "Unexpected backend",
                     },
                 ) as stale:
                temporary_directory.return_value.__enter__.return_value = tmp
                temporary_directory.return_value.__exit__.return_value = False
                dmg = Path(tmp) / "CC.Branch_1.0.2_aarch64.dmg"
                dmg.write_bytes(b"dmg")

                result = verify_macos_dmg.verify_dmg(
                    dmg,
                    expected_app_name="CC Branch.app",
                    launch_app=True,
                    verify_stale_backend_rejection=True,
                )

        self.assertEqual(
            result["stale_backend_rejection"],
            {"ok": True, "expected_error": "Unexpected backend"},
        )
        stale.assert_called_once_with(app, timeout=30.0)

    def test_verify_dmg_rejects_wrong_asset_version_before_mounting(self):
        with tempfile.TemporaryDirectory() as tmp:
            dmg = Path(tmp) / "CC.Branch_1.0.1_aarch64.dmg"
            dmg.write_bytes(b"dmg")

            with mock.patch.object(verify_macos_dmg.platform, "system", return_value="Darwin"), \
                 mock.patch.object(verify_macos_dmg, "attach_dmg") as attach_dmg:
                with self.assertRaisesRegex(ValueError, "does not match expected"):
                    verify_macos_dmg.verify_dmg(
                        dmg,
                        expected_app_name="CC Branch.app",
                        expected_version="1.0.2",
                    )

        attach_dmg.assert_not_called()

    def test_require_asset_name_version_rejects_version_prefix_match(self):
        with self.assertRaisesRegex(ValueError, "does not match expected"):
            verify_macos_dmg.require_asset_name_version(
                Path("CC.Branch_1.0.20_aarch64.dmg"),
                "1.0.2",
                label="DMG",
            )

    def test_verify_dmg_rejects_launch_result_without_bundled_backend_source(self):
        app = Path("/Volumes/CC Branch/CC Branch.app")
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(verify_macos_dmg.platform, "system", return_value="Darwin"), \
                 mock.patch.object(verify_macos_dmg.tempfile, "TemporaryDirectory") as temporary_directory, \
                 mock.patch.object(verify_macos_dmg, "attach_dmg"), \
                 mock.patch.object(verify_macos_dmg, "detach_dmg"), \
                 mock.patch.object(verify_macos_dmg, "find_app_bundle", return_value=app), \
                 mock.patch.object(verify_macos_dmg, "verify_applications_shortcut", return_value={"applications_shortcut": "/Applications"}), \
                 mock.patch.object(verify_macos_dmg, "verify_app_bundle_contains_backend", return_value={"app_path": str(app)}), \
                 mock.patch.object(verify_macos_dmg, "verify_app_launches_backend", return_value={"ok": True, "port": 12345}):
                temporary_directory.return_value.__enter__.return_value = tmp
                temporary_directory.return_value.__exit__.return_value = False
                dmg = Path(tmp) / "CC.Branch_1.0.2_aarch64.dmg"
                dmg.write_bytes(b"dmg")

                with self.assertRaisesRegex(ValueError, "backend_source"):
                    verify_macos_dmg.verify_dmg(
                        dmg,
                        expected_app_name="CC Branch.app",
                        launch_app=True,
                    )

    def test_verify_dmg_can_validate_gatekeeper_before_mounting(self):
        with tempfile.TemporaryDirectory() as tmp:
            dmg = Path(tmp) / "CC.Branch_1.0.2_aarch64.dmg"
            dmg.write_bytes(b"dmg")
            with mock.patch.object(verify_macos_dmg.platform, "system", return_value="Darwin"), \
                 mock.patch.object(verify_macos_dmg, "verify_gatekeeper", return_value={"gatekeeper": "accepted"}) as gatekeeper, \
                 mock.patch.object(verify_macos_dmg, "attach_dmg"), \
                 mock.patch.object(verify_macos_dmg, "detach_dmg"), \
                 mock.patch.object(verify_macos_dmg, "find_app_bundle", return_value=Path("/Volumes/CC Branch/CC Branch.app")), \
                 mock.patch.object(verify_macos_dmg, "verify_applications_shortcut", return_value={"applications_shortcut": "/Applications"}), \
                 mock.patch.object(verify_macos_dmg, "verify_app_bundle_contains_backend", return_value={"app_path": "/Volumes/CC Branch/CC Branch.app"}):
                result = verify_macos_dmg.verify_dmg(
                    dmg,
                    expected_app_name="CC Branch.app",
                    verify_gatekeeper_check=True,
                )

        self.assertEqual(result["gatekeeper"], {"gatekeeper": "accepted"})
        gatekeeper.assert_called_once_with(dmg)

    def test_verify_dmg_rejects_launch_request_on_non_macos(self):
        with mock.patch.object(verify_macos_dmg.platform, "system", return_value="Linux"):
            with self.assertRaisesRegex(RuntimeError, "requires macOS"):
                verify_macos_dmg.verify_dmg(
                    Path("/tmp/CC.Branch_1.0.2_aarch64.dmg"),
                    expected_app_name="CC Branch.app",
                    launch_app=True,
                )

    def test_verify_dmg_rejects_installed_copy_request_on_non_macos(self):
        with mock.patch.object(verify_macos_dmg.platform, "system", return_value="Linux"):
            with self.assertRaisesRegex(RuntimeError, "requires macOS"):
                verify_macos_dmg.verify_dmg(
                    Path("/tmp/CC.Branch_1.0.2_aarch64.dmg"),
                    expected_app_name="CC Branch.app",
                    verify_installed_copy=True,
                )


if __name__ == "__main__":
    unittest.main()
