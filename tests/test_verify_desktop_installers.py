import importlib.util
import tempfile
import unittest
from unittest import mock
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify-desktop-installers.py"
SPEC = importlib.util.spec_from_file_location("verify_desktop_installers", SCRIPT_PATH)
assert SPEC and SPEC.loader
verify_desktop_installers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_desktop_installers)


class VerifyDesktopInstallersTests(unittest.TestCase):
    def test_verify_desktop_app_launch_uses_auto_port_for_user_download_path(self):
        with mock.patch("importlib.util.spec_from_file_location") as spec_from_file_location, \
             mock.patch("importlib.util.module_from_spec") as module_from_spec:
            module = mock.Mock()
            module.verify_desktop_app.return_value = {
                "ok": True,
                "backend_source": "bundled-sidecar",
            }
            module_from_spec.return_value = module
            loader = mock.Mock()
            spec_from_file_location.return_value = mock.Mock(loader=loader)

            result = verify_desktop_installers.verify_desktop_app_launch(
                Path("/tmp/cc-branch"),
                expected_version="1.0.2",
                expected_platform="linux",
                expected_arch="x86_64",
            )

        self.assertTrue(result["ok"])
        module.verify_desktop_app.assert_called_once_with(
            Path("/tmp/cc-branch"),
            timeout=30.0,
            expected_version="1.0.2",
            expected_platform="linux",
            expected_arch="x86_64",
            use_auto_port=True,
        )

    def test_find_one_returns_first_matching_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "bundle" / "deb"
            nested.mkdir(parents=True)
            package = nested / "CC.Branch_1.0.2_amd64.deb"
            package.write_bytes(b"deb")

            self.assertEqual(verify_desktop_installers.find_one(root, "*.deb"), package)

    def test_find_one_rejects_ambiguous_matching_installers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CC.Branch_1.0.2_amd64.deb").write_bytes(b"deb")
            (root / "CC.Branch_1.0.2_amd64-copy.deb").write_bytes(b"deb")

            with self.assertRaisesRegex(ValueError, "multiple installers"):
                verify_desktop_installers.find_one(root, "*.deb")

    def test_path_mentions_backend_matches_platform_sidecar_names(self):
        self.assertTrue(
            verify_desktop_installers.path_mentions_backend("./usr/bin/cc-branch-backend")
        )
        self.assertTrue(
            verify_desktop_installers.path_mentions_backend(
                r"Program Files\\CC Branch\\cc-branch-backend.exe",
                windows=True,
            )
        )
        self.assertFalse(
            verify_desktop_installers.path_mentions_backend("./usr/bin/cc-branch")
        )

    def test_require_backend_in_listing_returns_matching_entry(self):
        listing = "\n".join([
            "-rwxr-xr-x root/root 123 ./usr/bin/cc-branch",
            "-rwxr-xr-x root/root 456 ./usr/bin/cc-branch-backend",
        ])

        self.assertEqual(
            verify_desktop_installers.require_backend_in_listing(
                listing,
                label="package",
            ),
            "-rwxr-xr-x root/root 456 ./usr/bin/cc-branch-backend",
        )

    def test_require_backend_in_listing_rejects_non_executable_backend_entry(self):
        listing = "\n".join([
            "-rwxr-xr-x root/root 123 ./usr/bin/cc-branch",
            "-rw-r--r-- root/root 456 ./usr/bin/cc-branch-backend",
        ])

        with self.assertRaisesRegex(PermissionError, "not executable"):
            verify_desktop_installers.require_backend_in_listing(
                listing,
                label="package",
            )

    def test_require_backend_in_listing_rejects_missing_backend(self):
        with self.assertRaisesRegex(ValueError, "cc-branch-backend"):
            verify_desktop_installers.require_backend_in_listing(
                "./usr/bin/cc-branch",
                label="package",
            )

    def test_require_listing_entries_colocated_rejects_split_directories(self):
        app = "-rwxr-xr-x root/root 123 ./usr/bin/cc-branch"
        backend = "-rwxr-xr-x root/root 456 ./opt/cc-branch/cc-branch-backend"

        with self.assertRaisesRegex(ValueError, "same directory"):
            verify_desktop_installers.require_listing_entries_colocated(
                app,
                backend,
                label="package",
            )

    def test_verify_deb_rejects_missing_app_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp)
            deb = bundle_dir / "CC.Branch_1.0.2_amd64.deb"
            deb.write_bytes(b"deb")
            listing = "\n".join([
                "-rwxr-xr-x root/root 456 ./usr/bin/cc-branch-backend",
            ])

            with mock.patch.object(verify_desktop_installers, "require_tool"), \
                 mock.patch.object(verify_desktop_installers, "run_text", return_value=listing):
                with self.assertRaisesRegex(ValueError, "cc-branch"):
                    verify_desktop_installers.verify_deb(bundle_dir)

    def test_verify_deb_rejects_non_executable_app_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp)
            deb = bundle_dir / "CC.Branch_1.0.2_amd64.deb"
            deb.write_bytes(b"deb")
            listing = "\n".join([
                "-rw-r--r-- root/root 123 ./usr/bin/cc-branch",
                "-rwxr-xr-x root/root 456 ./usr/bin/cc-branch-backend",
            ])

            with mock.patch.object(verify_desktop_installers, "require_tool"), \
                 mock.patch.object(verify_desktop_installers, "run_text", return_value=listing):
                with self.assertRaisesRegex(PermissionError, "app executable"):
                    verify_desktop_installers.verify_deb(bundle_dir)

    def test_verify_deb_rejects_duplicate_app_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp)
            deb = bundle_dir / "CC.Branch_1.0.2_amd64.deb"
            deb.write_bytes(b"deb")
            listing = "\n".join([
                "-rwxr-xr-x root/root 123 ./usr/bin/cc-branch",
                "-rwxr-xr-x root/root 456 ./opt/cc-branch/cc-branch",
                "-rwxr-xr-x root/root 789 ./usr/bin/cc-branch-backend",
            ])

            with mock.patch.object(verify_desktop_installers, "require_tool"), \
                 mock.patch.object(verify_desktop_installers, "run_text", return_value=listing):
                with self.assertRaisesRegex(ValueError, "multiple.*cc-branch"):
                    verify_desktop_installers.verify_deb(bundle_dir)

    def test_verify_deb_rejects_empty_backend_listing_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp)
            deb = bundle_dir / "CC.Branch_1.0.2_amd64.deb"
            deb.write_bytes(b"deb")
            listing = "\n".join([
                "-rwxr-xr-x root/root 123 ./usr/bin/cc-branch",
                "-rwxr-xr-x root/root 0 ./usr/bin/cc-branch-backend",
            ])

            with mock.patch.object(verify_desktop_installers, "require_tool"), \
                 mock.patch.object(verify_desktop_installers, "run_text", return_value=listing):
                with self.assertRaisesRegex(ValueError, "empty"):
                    verify_desktop_installers.verify_deb(bundle_dir)

    def test_verify_deb_rejects_split_app_and_backend_listing_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp)
            deb = bundle_dir / "CC.Branch_1.0.2_amd64.deb"
            deb.write_bytes(b"deb")
            listing = "\n".join([
                "-rwxr-xr-x root/root 123 ./usr/bin/cc-branch",
                "-rwxr-xr-x root/root 456 ./opt/cc-branch/cc-branch-backend",
            ])

            with mock.patch.object(verify_desktop_installers, "require_tool"), \
                 mock.patch.object(verify_desktop_installers, "run_text", return_value=listing):
                with self.assertRaisesRegex(ValueError, "same directory"):
                    verify_desktop_installers.verify_deb(bundle_dir)

    def test_verify_deb_rejects_wrong_package_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp)
            deb = bundle_dir / "CC.Branch_1.0.2_amd64.deb"
            deb.write_bytes(b"deb")
            listing = "\n".join([
                "-rwxr-xr-x root/root 123 ./usr/bin/cc-branch",
                "-rwxr-xr-x root/root 456 ./usr/bin/cc-branch-backend",
            ])

            def fake_run_text(command, *, cwd=None):
                if command[:2] == ["dpkg-deb", "--contents"]:
                    return listing
                if command[:2] == ["dpkg-deb", "--field"]:
                    return "1.0.1\n"
                raise AssertionError(f"Unexpected command: {command}")

            with mock.patch.object(verify_desktop_installers, "require_tool"), \
                 mock.patch.object(verify_desktop_installers, "run_text", side_effect=fake_run_text):
                with self.assertRaisesRegex(ValueError, "does not match expected"):
                    verify_desktop_installers.verify_deb(bundle_dir, expected_version="1.0.2")

    def test_verify_deb_can_launch_extracted_package_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            deb = bundle_dir / "CC.Branch_1.0.2_amd64.deb"
            deb.write_bytes(b"deb")
            listing = "\n".join([
                "-rwxr-xr-x root/root 123 ./usr/bin/cc-branch",
                "-rwxr-xr-x root/root 456 ./usr/bin/cc-branch-backend",
            ])

            def fake_run_text(command, *, cwd=None):
                if command[:2] == ["dpkg-deb", "--contents"]:
                    return listing
                if command[:2] == ["dpkg-deb", "--field"]:
                    return "1.0.2\n"
                if command[:2] == ["dpkg-deb", "--extract"]:
                    target = Path(command[3])
                    (target / "usr" / "bin").mkdir(parents=True)
                    app = target / "usr" / "bin" / "cc-branch"
                    backend = target / "usr" / "bin" / "cc-branch-backend"
                    app.write_text("app", encoding="utf-8")
                    backend.write_text("backend", encoding="utf-8")
                    app.chmod(0o755)
                    backend.chmod(0o755)
                    return ""
                raise AssertionError(f"Unexpected command: {command}")

            with mock.patch.object(verify_desktop_installers, "require_tool"), \
                 mock.patch.object(verify_desktop_installers, "run_text", side_effect=fake_run_text), \
                 mock.patch.object(
                     verify_desktop_installers,
                     "verify_desktop_app_launch",
                     return_value={
                         "ok": True,
                         "port": 18123,
                         "backend_source": "bundled-sidecar",
                     },
                 ) as launch, \
                 mock.patch.object(
                     verify_desktop_installers,
                     "verify_desktop_app_stale_backend_rejection",
                     return_value={
                         "ok": True,
                         "expected_error": "Unexpected backend",
                     },
                 ) as stale:
                result = verify_desktop_installers.verify_deb(
                    bundle_dir,
                    expected_version="1.0.2",
                    launch_app=True,
                )

        self.assertEqual(result["launch"]["backend_source"], "bundled-sidecar")
        self.assertEqual(result["stale_backend_rejection"]["expected_error"], "Unexpected backend")
        self.assertEqual(result["extracted_app"], "usr/bin/cc-branch")
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0].name, "cc-branch")
        stale.assert_called_once()
        self.assertEqual(stale.call_args.kwargs["sidecar_executable"].name, "cc-branch-backend")

    def test_verify_extracted_linux_package_rejects_split_app_and_backend_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = root / "usr" / "bin" / "cc-branch"
            backend = root / "opt" / "cc-branch" / "cc-branch-backend"
            app.parent.mkdir(parents=True)
            backend.parent.mkdir(parents=True)
            app.write_text("app", encoding="utf-8")
            backend.write_text("backend", encoding="utf-8")
            app.chmod(0o755)
            backend.chmod(0o755)

            with self.assertRaisesRegex(ValueError, "same directory"):
                verify_desktop_installers.find_extracted_linux_executables(
                    root,
                    label="Linux package",
                )

    def test_require_tool_reports_missing_system_dependency(self):
        with mock.patch.object(verify_desktop_installers.shutil, "which", return_value=None):
            with self.assertRaisesRegex(FileNotFoundError, "dpkg-deb"):
                verify_desktop_installers.require_tool("dpkg-deb")

    def test_verify_rpm_requests_verbose_listing_for_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp)
            rpm = bundle_dir / "CC.Branch-1.0.2-1.x86_64.rpm"
            rpm.write_bytes(b"rpm")
            with mock.patch.object(verify_desktop_installers, "require_tool"), \
                 mock.patch.object(
                     verify_desktop_installers.subprocess,
                     "run",
                     return_value=mock.Mock(
                         stdout="\n".join([
                             "-rwxr-xr-x 1 root root 123 ./usr/bin/cc-branch",
                             "-rwxr-xr-x 1 root root 456 ./usr/bin/cc-branch-backend",
                         ]),
                         stderr="",
                     ),
                 ) as run:
                result = verify_desktop_installers.verify_rpm(bundle_dir)

        self.assertIn("cc-branch-backend", result["backend"])
        self.assertIn("cc-branch", result["app"])
        self.assertIn("cpio -tv", run.call_args.args[0])

    def test_verify_rpm_rejects_split_app_and_backend_listing_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp)
            rpm = bundle_dir / "CC.Branch-1.0.2-1.x86_64.rpm"
            rpm.write_bytes(b"rpm")
            with mock.patch.object(verify_desktop_installers, "require_tool"), \
                 mock.patch.object(
                     verify_desktop_installers.subprocess,
                     "run",
                     return_value=mock.Mock(
                         stdout="\n".join([
                             "-rwxr-xr-x 1 root root 123 ./usr/bin/cc-branch",
                             "-rwxr-xr-x 1 root root 456 ./opt/cc-branch/cc-branch-backend",
                         ]),
                         stderr="",
                     ),
                 ):
                with self.assertRaisesRegex(ValueError, "same directory"):
                    verify_desktop_installers.verify_rpm(bundle_dir)

    def test_verify_rpm_reports_package_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp)
            rpm = bundle_dir / "CC.Branch-1.0.2-1.x86_64.rpm"
            rpm.write_bytes(b"rpm")
            with mock.patch.object(verify_desktop_installers, "require_tool"), \
                 mock.patch.object(
                     verify_desktop_installers.subprocess,
                     "run",
                     return_value=mock.Mock(
                         stdout="\n".join([
                             "-rwxr-xr-x 1 root root 123 ./usr/bin/cc-branch",
                             "-rwxr-xr-x 1 root root 456 ./usr/bin/cc-branch-backend",
                         ]),
                         stderr="",
                     ),
                 ), \
                 mock.patch.object(verify_desktop_installers, "run_text", return_value="1.0.2"):
                result = verify_desktop_installers.verify_rpm(
                    bundle_dir,
                    expected_version="1.0.2",
                )

        self.assertEqual(result["package_version"], "1.0.2")

    def test_verify_rpm_rejects_wrong_package_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp)
            rpm = bundle_dir / "CC.Branch-1.0.2-1.x86_64.rpm"
            rpm.write_bytes(b"rpm")
            with mock.patch.object(verify_desktop_installers, "require_tool"), \
                 mock.patch.object(
                     verify_desktop_installers.subprocess,
                     "run",
                     return_value=mock.Mock(
                         stdout="\n".join([
                             "-rwxr-xr-x 1 root root 123 ./usr/bin/cc-branch",
                             "-rwxr-xr-x 1 root root 456 ./usr/bin/cc-branch-backend",
                         ]),
                         stderr="",
                     ),
                 ), \
                 mock.patch.object(verify_desktop_installers, "run_text", return_value="1.0.1"):
                with self.assertRaisesRegex(ValueError, "does not match expected"):
                    verify_desktop_installers.verify_rpm(
                        bundle_dir,
                        expected_version="1.0.2",
                    )

    def test_verify_rpm_can_launch_extracted_package_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            rpm = bundle_dir / "CC.Branch-1.0.2-1.x86_64.rpm"
            rpm.write_bytes(b"rpm")

            def fake_subprocess_run(command, **kwargs):
                if isinstance(command, str) and "cpio -tv" in command:
                    return mock.Mock(
                        stdout="\n".join([
                            "-rwxr-xr-x 1 root root 123 ./usr/bin/cc-branch",
                            "-rwxr-xr-x 1 root root 456 ./usr/bin/cc-branch-backend",
                        ]),
                        stderr="",
                    )
                if isinstance(command, str) and "cpio -idmv" in command:
                    cwd = Path(kwargs["cwd"])
                    (cwd / "usr" / "bin").mkdir(parents=True)
                    app = cwd / "usr" / "bin" / "cc-branch"
                    backend = cwd / "usr" / "bin" / "cc-branch-backend"
                    app.write_text("app", encoding="utf-8")
                    backend.write_text("backend", encoding="utf-8")
                    app.chmod(0o755)
                    backend.chmod(0o755)
                    return mock.Mock(stdout="", stderr="")
                raise AssertionError(f"Unexpected command: {command}")

            with mock.patch.object(verify_desktop_installers, "require_tool"), \
                 mock.patch.object(verify_desktop_installers.subprocess, "run", side_effect=fake_subprocess_run), \
                 mock.patch.object(verify_desktop_installers, "run_text", return_value="1.0.2"), \
                 mock.patch.object(
                     verify_desktop_installers,
                     "verify_desktop_app_launch",
                     return_value={
                         "ok": True,
                         "port": 18123,
                         "backend_source": "bundled-sidecar",
                     },
                 ) as launch, \
                 mock.patch.object(
                     verify_desktop_installers,
                     "verify_desktop_app_stale_backend_rejection",
                     return_value={
                         "ok": True,
                         "expected_error": "Unexpected backend",
                     },
                 ) as stale:
                result = verify_desktop_installers.verify_rpm(
                    bundle_dir,
                    expected_version="1.0.2",
                    launch_app=True,
                )

        self.assertEqual(result["launch"]["backend_source"], "bundled-sidecar")
        self.assertEqual(result["stale_backend_rejection"]["expected_error"], "Unexpected backend")
        self.assertEqual(result["extracted_app"], "usr/bin/cc-branch")
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0].name, "cc-branch")
        stale.assert_called_once()
        self.assertEqual(stale.call_args.kwargs["sidecar_executable"].name, "cc-branch-backend")

    def test_verify_appimage_launches_downloaded_appimage_not_extracted_apprun(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            appimage = bundle_dir / "CC.Branch_1.0.2_amd64.AppImage"
            appimage.write_text("#!/bin/sh\n", encoding="utf-8")
            appimage.chmod(0o755)

            def fake_run_text(command, *, cwd=None):
                extracted = cwd / "squashfs-root"
                backend = extracted / "usr" / "bin" / "cc-branch-backend"
                app_run = extracted / "AppRun"
                backend.parent.mkdir(parents=True)
                backend.write_text("backend", encoding="utf-8")
                backend.chmod(0o755)
                app_run.write_text("#!/bin/sh\n", encoding="utf-8")
                app_run.chmod(0o755)
                return ""

            with mock.patch.object(verify_desktop_installers, "run_text", side_effect=fake_run_text), \
                 mock.patch.object(
                     verify_desktop_installers,
                     "verify_desktop_app_launch",
                     return_value={
                         "ok": True,
                         "port": 18123,
                         "backend_source": "bundled-sidecar",
                     },
                 ) as launch, \
                 mock.patch.object(
                     verify_desktop_installers,
                     "verify_desktop_app_stale_backend_rejection",
                     return_value={
                         "ok": True,
                         "expected_error": "Unexpected backend",
                     },
                 ):
                result = verify_desktop_installers.verify_appimage(bundle_dir, launch_app=True)

        self.assertEqual(
            result["launch"],
            {"ok": True, "port": 18123, "backend_source": "bundled-sidecar"},
        )
        self.assertEqual(result["app"], "AppRun")
        self.assertGreater(result["app_size"], 0)
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0], appimage)

    def test_verify_appimage_runs_stale_backend_rejection_when_launching(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            appimage = bundle_dir / "CC.Branch_1.0.2_amd64.AppImage"
            appimage.write_text("#!/bin/sh\n", encoding="utf-8")
            appimage.chmod(0o755)

            def fake_run_text(command, *, cwd=None):
                extracted = cwd / "squashfs-root"
                backend = extracted / "usr" / "bin" / "cc-branch-backend"
                app_run = extracted / "AppRun"
                backend.parent.mkdir(parents=True)
                backend.write_text("backend", encoding="utf-8")
                backend.chmod(0o755)
                app_run.write_text("#!/bin/sh\n", encoding="utf-8")
                app_run.chmod(0o755)
                return ""

            with mock.patch.object(verify_desktop_installers, "run_text", side_effect=fake_run_text), \
                 mock.patch.object(
                     verify_desktop_installers,
                     "verify_desktop_app_launch",
                     return_value={
                         "ok": True,
                         "port": 18123,
                         "backend_source": "bundled-sidecar",
                     },
                 ), \
                 mock.patch.object(
                     verify_desktop_installers,
                     "verify_desktop_app_stale_backend_rejection",
                     return_value={
                         "ok": True,
                         "expected_error": "Unexpected backend",
                     },
                 ) as stale:
                result = verify_desktop_installers.verify_appimage(
                    bundle_dir,
                    launch_app=True,
                )

        self.assertEqual(
            result["stale_backend_rejection"],
            {"ok": True, "expected_error": "Unexpected backend"},
        )
        stale.assert_called_once()
        self.assertEqual(stale.call_args.args[0], appimage)
        self.assertEqual(stale.call_args.kwargs["sidecar_executable"].name, "cc-branch-backend")

    def test_verify_appimage_rejects_launch_result_without_bundled_backend_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            appimage = bundle_dir / "CC.Branch_1.0.2_amd64.AppImage"
            appimage.write_text("#!/bin/sh\n", encoding="utf-8")
            appimage.chmod(0o755)

            def fake_run_text(command, *, cwd=None):
                extracted = cwd / "squashfs-root"
                backend = extracted / "usr" / "bin" / "cc-branch-backend"
                app_run = extracted / "AppRun"
                backend.parent.mkdir(parents=True)
                backend.write_text("backend", encoding="utf-8")
                backend.chmod(0o755)
                app_run.write_text("#!/bin/sh\n", encoding="utf-8")
                app_run.chmod(0o755)
                return ""

            with mock.patch.object(verify_desktop_installers, "run_text", side_effect=fake_run_text), \
                 mock.patch.object(
                     verify_desktop_installers,
                     "verify_desktop_app_launch",
                     return_value={"ok": True, "port": 18123},
                 ):
                with self.assertRaisesRegex(ValueError, "backend_source"):
                    verify_desktop_installers.verify_appimage(bundle_dir, launch_app=True)

    def test_verify_appimage_rejects_empty_backend_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            appimage = bundle_dir / "CC.Branch_1.0.2_amd64.AppImage"
            appimage.write_text("#!/bin/sh\n", encoding="utf-8")
            appimage.chmod(0o755)

            def fake_run_text(command, *, cwd=None):
                extracted = cwd / "squashfs-root"
                backend = extracted / "usr" / "bin" / "cc-branch-backend"
                backend.parent.mkdir(parents=True)
                backend.write_bytes(b"")
                backend.chmod(0o755)
                return ""

            with mock.patch.object(verify_desktop_installers, "run_text", side_effect=fake_run_text):
                with self.assertRaisesRegex(ValueError, "empty"):
                    verify_desktop_installers.verify_appimage(bundle_dir)

    def test_verify_appimage_rejects_empty_apprun(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            appimage = bundle_dir / "CC.Branch_1.0.2_amd64.AppImage"
            appimage.write_text("#!/bin/sh\n", encoding="utf-8")
            appimage.chmod(0o755)

            def fake_run_text(command, *, cwd=None):
                extracted = cwd / "squashfs-root"
                backend = extracted / "usr" / "bin" / "cc-branch-backend"
                app_run = extracted / "AppRun"
                backend.parent.mkdir(parents=True)
                backend.write_text("backend", encoding="utf-8")
                backend.chmod(0o755)
                app_run.write_bytes(b"")
                app_run.chmod(0o755)
                return ""

            with mock.patch.object(verify_desktop_installers, "run_text", side_effect=fake_run_text):
                with self.assertRaisesRegex(ValueError, "AppImage AppRun.*empty"):
                    verify_desktop_installers.verify_appimage(bundle_dir)

    def test_verify_appimage_rejects_duplicate_backend_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            appimage = bundle_dir / "CC.Branch_1.0.2_amd64.AppImage"
            appimage.write_text("#!/bin/sh\n", encoding="utf-8")
            appimage.chmod(0o755)

            def fake_run_text(command, *, cwd=None):
                extracted = cwd / "squashfs-root"
                first = extracted / "usr" / "bin" / "cc-branch-backend"
                second = extracted / "opt" / "cc-branch" / "cc-branch-backend"
                first.parent.mkdir(parents=True)
                second.parent.mkdir(parents=True)
                first.write_text("backend", encoding="utf-8")
                second.write_text("backend", encoding="utf-8")
                first.chmod(0o755)
                second.chmod(0o755)
                return ""

            with mock.patch.object(verify_desktop_installers, "run_text", side_effect=fake_run_text):
                with self.assertRaisesRegex(ValueError, "multiple.*cc-branch-backend"):
                    verify_desktop_installers.verify_appimage(bundle_dir)

    def test_verify_appimage_rejects_wrong_asset_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            appimage = bundle_dir / "CC.Branch_1.0.1_amd64.AppImage"
            appimage.write_text("#!/bin/sh\n", encoding="utf-8")
            appimage.chmod(0o755)

            with self.assertRaisesRegex(ValueError, "does not match expected"):
                verify_desktop_installers.verify_appimage(
                    bundle_dir,
                    expected_version="1.0.2",
                )

    def test_require_asset_name_version_rejects_version_prefix_match(self):
        with self.assertRaisesRegex(ValueError, "does not match expected"):
            verify_desktop_installers.require_asset_name_version(
                Path("CC.Branch_1.0.20_amd64.AppImage"),
                "1.0.2",
                label="AppImage",
            )

    def test_verify_installers_passes_appimage_launch_flag(self):
        with mock.patch.object(verify_desktop_installers, "verify_deb", return_value={"asset": "deb"}), \
             mock.patch.object(verify_desktop_installers, "verify_rpm", return_value={"asset": "rpm"}), \
             mock.patch.object(verify_desktop_installers, "verify_appimage", return_value={"asset": "appimage"}) as appimage:
            verify_desktop_installers.verify_installers(
                Path("/tmp/release"),
                "linux",
                launch_appimage=True,
                expected_version="1.0.2",
            )

        appimage.assert_called_once_with(
            Path("/tmp/release"),
            expected_version="1.0.2",
            launch_app=True,
        )

    def test_verify_installers_passes_linux_package_launch_flag(self):
        with mock.patch.object(verify_desktop_installers, "verify_deb", return_value={"asset": "deb"}) as deb, \
             mock.patch.object(verify_desktop_installers, "verify_rpm", return_value={"asset": "rpm"}) as rpm, \
             mock.patch.object(verify_desktop_installers, "verify_appimage", return_value={"asset": "appimage"}):
            verify_desktop_installers.verify_installers(
                Path("/tmp/release"),
                "linux",
                launch_linux_packages=True,
                expected_version="1.0.2",
            )

        deb.assert_called_once_with(
            Path("/tmp/release"),
            expected_version="1.0.2",
            launch_app=True,
        )
        rpm.assert_called_once_with(
            Path("/tmp/release"),
            expected_version="1.0.2",
            launch_app=True,
        )

    def test_verify_msi_can_launch_extracted_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            msi = bundle_dir / "CC.Branch_1.0.2_x64_en-US.msi"
            msi.write_bytes(b"msi")

            def fake_run(command, check):
                target_arg = next(arg for arg in command if str(arg).startswith("TARGETDIR="))
                target = Path(str(target_arg).split("=", 1)[1])
                install_dir = target / "PFiles" / "CC Branch"
                install_dir.mkdir(parents=True)
                backend = install_dir / "cc-branch-backend.exe"
                app = install_dir / "cc-branch.exe"
                backend.write_text("backend", encoding="utf-8")
                app.write_text("app", encoding="utf-8")
                return mock.Mock(returncode=0)

            with mock.patch.object(verify_desktop_installers.platform, "system", return_value="Windows"), \
                 mock.patch.object(verify_desktop_installers.subprocess, "run", side_effect=fake_run), \
                 mock.patch.object(verify_desktop_installers, "read_windows_executable_version", return_value="1.0.2"), \
                 mock.patch.object(
                     verify_desktop_installers,
                     "verify_desktop_app_launch",
                     return_value={
                         "ok": True,
                         "port": 18123,
                         "backend_source": "bundled-sidecar",
                     },
                ) as launch, \
                 mock.patch.object(
                     verify_desktop_installers,
                     "verify_desktop_app_stale_backend_rejection",
                     return_value={
                         "ok": True,
                         "expected_error": "Unexpected backend",
                     },
                ) as stale:
                result = verify_desktop_installers.verify_msi(
                    bundle_dir,
                    launch_app=True,
                    expected_version="1.0.2",
                )

        self.assertEqual(
            result["launch"],
            {"ok": True, "port": 18123, "backend_source": "bundled-sidecar"},
        )
        self.assertEqual(result["app"], "PFiles/CC Branch/cc-branch.exe")
        self.assertGreater(result["app_size"], 0)
        self.assertEqual(result["app_version"], "1.0.2")
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0].name, "cc-branch.exe")
        self.assertEqual(
            result["stale_backend_rejection"],
            {"ok": True, "expected_error": "Unexpected backend"},
        )
        stale.assert_called_once()
        self.assertEqual(stale.call_args.args[0].name, "cc-branch.exe")
        self.assertEqual(stale.call_args.kwargs["sidecar_executable"].name, "cc-branch-backend.exe")

    def test_verify_msi_repairs_extracted_windows_acl(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            msi = bundle_dir / "CC.Branch_1.0.2_x64_en-US.msi"
            msi.write_bytes(b"msi")
            commands = []

            def fake_run(command, check=False, capture_output=False, text=False):
                commands.append(command)
                if command[0] == "msiexec":
                    target_arg = next(arg for arg in command if str(arg).startswith("TARGETDIR="))
                    target = Path(str(target_arg).split("=", 1)[1])
                    install_dir = target / "PFiles" / "CC Branch"
                    install_dir.mkdir(parents=True)
                    (install_dir / "cc-branch-backend.exe").write_text("backend", encoding="utf-8")
                    (install_dir / "cc-branch.exe").write_text("app", encoding="utf-8")
                return mock.Mock(returncode=0, stdout="", stderr="")

            with mock.patch.object(verify_desktop_installers.platform, "system", return_value="Windows"), \
                 mock.patch.object(verify_desktop_installers.shutil, "which", return_value="icacls"), \
                 mock.patch.dict(verify_desktop_installers.os.environ, {"USERNAME": "runneradmin"}), \
                 mock.patch.object(verify_desktop_installers.subprocess, "run", side_effect=fake_run):
                result = verify_desktop_installers.verify_msi(bundle_dir)

        self.assertTrue(result["checked"])
        self.assertTrue(any(command[0] == "icacls" and "/T" in command for command in commands))

    def test_verify_msi_rejects_wrong_app_executable_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            msi = bundle_dir / "CC.Branch_1.0.2_x64_en-US.msi"
            msi.write_bytes(b"msi")

            def fake_run(command, check):
                target_arg = next(arg for arg in command if str(arg).startswith("TARGETDIR="))
                target = Path(str(target_arg).split("=", 1)[1])
                install_dir = target / "PFiles" / "CC Branch"
                install_dir.mkdir(parents=True)
                (install_dir / "cc-branch-backend.exe").write_text("backend", encoding="utf-8")
                (install_dir / "cc-branch.exe").write_text("app", encoding="utf-8")
                return mock.Mock(returncode=0)

            with mock.patch.object(verify_desktop_installers.platform, "system", return_value="Windows"), \
                 mock.patch.object(verify_desktop_installers.subprocess, "run", side_effect=fake_run), \
                 mock.patch.object(verify_desktop_installers, "read_windows_executable_version", return_value="1.0.1"):
                with self.assertRaisesRegex(ValueError, "does not match expected"):
                    verify_desktop_installers.verify_msi(
                        bundle_dir,
                        expected_version="1.0.2",
                    )

    def test_verify_msi_rejects_wrong_asset_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            msi = bundle_dir / "CC.Branch_1.0.1_x64_en-US.msi"
            msi.write_bytes(b"msi")

            with self.assertRaisesRegex(ValueError, "does not match expected"):
                verify_desktop_installers.verify_msi(
                    bundle_dir,
                    expected_version="1.0.2",
                )

    def test_verify_msi_rejects_launch_request_on_non_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "CC.Branch_1.0.2_x64_en-US.msi").write_bytes(b"msi")

            with mock.patch.object(verify_desktop_installers.platform, "system", return_value="Linux"):
                with self.assertRaisesRegex(RuntimeError, "requires Windows"):
                    verify_desktop_installers.verify_msi(bundle_dir, launch_app=True)

    def test_verify_msi_rejects_empty_backend_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            msi = bundle_dir / "CC.Branch_1.0.2_x64_en-US.msi"
            msi.write_bytes(b"msi")

            def fake_run(command, check):
                target_arg = next(arg for arg in command if str(arg).startswith("TARGETDIR="))
                target = Path(str(target_arg).split("=", 1)[1])
                install_dir = target / "PFiles" / "CC Branch"
                install_dir.mkdir(parents=True)
                (install_dir / "cc-branch-backend.exe").write_bytes(b"")
                (install_dir / "cc-branch.exe").write_text("app", encoding="utf-8")
                return mock.Mock(returncode=0)

            with mock.patch.object(verify_desktop_installers.platform, "system", return_value="Windows"), \
                 mock.patch.object(verify_desktop_installers.subprocess, "run", side_effect=fake_run):
                with self.assertRaisesRegex(ValueError, "empty"):
                    verify_desktop_installers.verify_msi(bundle_dir)

    def test_verify_msi_rejects_duplicate_backend_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            msi = bundle_dir / "CC.Branch_1.0.2_x64_en-US.msi"
            msi.write_bytes(b"msi")

            def fake_run(command, check):
                target_arg = next(arg for arg in command if str(arg).startswith("TARGETDIR="))
                target = Path(str(target_arg).split("=", 1)[1])
                install_dir = target / "PFiles" / "CC Branch"
                alt_dir = target / "PFiles" / "CC Branch Copy"
                install_dir.mkdir(parents=True)
                alt_dir.mkdir(parents=True)
                (install_dir / "cc-branch-backend.exe").write_text("backend", encoding="utf-8")
                (alt_dir / "cc-branch-backend.exe").write_text("backend", encoding="utf-8")
                (install_dir / "cc-branch.exe").write_text("app", encoding="utf-8")
                return mock.Mock(returncode=0)

            with mock.patch.object(verify_desktop_installers.platform, "system", return_value="Windows"), \
                 mock.patch.object(verify_desktop_installers.subprocess, "run", side_effect=fake_run):
                with self.assertRaisesRegex(ValueError, "multiple.*cc-branch-backend.exe"):
                    verify_desktop_installers.verify_msi(bundle_dir)

    def test_verify_msi_rejects_split_app_and_backend_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            msi = bundle_dir / "CC.Branch_1.0.2_x64_en-US.msi"
            msi.write_bytes(b"msi")

            def fake_run(command, check):
                target_arg = next(arg for arg in command if str(arg).startswith("TARGETDIR="))
                target = Path(str(target_arg).split("=", 1)[1])
                app_dir = target / "PFiles" / "CC Branch"
                backend_dir = target / "ProgramData" / "CC Branch"
                app_dir.mkdir(parents=True)
                backend_dir.mkdir(parents=True)
                (app_dir / "cc-branch.exe").write_text("app", encoding="utf-8")
                (backend_dir / "cc-branch-backend.exe").write_text("backend", encoding="utf-8")
                return mock.Mock(returncode=0)

            with mock.patch.object(verify_desktop_installers.platform, "system", return_value="Windows"), \
                 mock.patch.object(verify_desktop_installers.subprocess, "run", side_effect=fake_run):
                with self.assertRaisesRegex(ValueError, "same directory"):
                    verify_desktop_installers.verify_msi(bundle_dir)

    def test_verify_nsis_can_launch_extracted_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            nsis = bundle_dir / "CC.Branch_1.0.2_x64-setup.exe"
            nsis.write_bytes(b"exe")

            def fake_run_text(command, *, cwd=None):
                output_arg = next(arg for arg in command if str(arg).startswith("-o"))
                target = Path(str(output_arg)[2:])
                install_dir = target / "$PLUGINSDIR" / "app"
                install_dir.mkdir(parents=True)
                backend = install_dir / "cc-branch-backend.exe"
                app = install_dir / "cc-branch.exe"
                backend.write_text("backend", encoding="utf-8")
                app.write_text("app", encoding="utf-8")
                return ""

            with mock.patch.object(verify_desktop_installers.platform, "system", return_value="Windows"), \
                 mock.patch.object(verify_desktop_installers, "find_7z", return_value="7z"), \
                 mock.patch.object(verify_desktop_installers, "run_text", side_effect=fake_run_text), \
                 mock.patch.object(verify_desktop_installers, "read_windows_executable_version", return_value="1.0.2"), \
                 mock.patch.object(
                     verify_desktop_installers,
                     "verify_desktop_app_launch",
                     return_value={
                         "ok": True,
                         "port": 18123,
                         "backend_source": "bundled-sidecar",
                     },
                ) as launch, \
                 mock.patch.object(
                     verify_desktop_installers,
                     "verify_desktop_app_stale_backend_rejection",
                     return_value={
                         "ok": True,
                         "expected_error": "Unexpected backend",
                     },
                ) as stale:
                result = verify_desktop_installers.verify_nsis(
                    bundle_dir,
                    launch_app=True,
                    expected_version="1.0.2",
                )

        self.assertEqual(
            result["launch"],
            {"ok": True, "port": 18123, "backend_source": "bundled-sidecar"},
        )
        self.assertEqual(result["app"], "$PLUGINSDIR/app/cc-branch.exe")
        self.assertGreater(result["app_size"], 0)
        self.assertEqual(result["app_version"], "1.0.2")
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0].name, "cc-branch.exe")
        self.assertEqual(
            result["stale_backend_rejection"],
            {"ok": True, "expected_error": "Unexpected backend"},
        )
        stale.assert_called_once()
        self.assertEqual(stale.call_args.args[0].name, "cc-branch.exe")
        self.assertEqual(stale.call_args.kwargs["sidecar_executable"].name, "cc-branch-backend.exe")

    def test_verify_nsis_rejects_wrong_app_executable_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            nsis = bundle_dir / "CC.Branch_1.0.2_x64-setup.exe"
            nsis.write_bytes(b"exe")

            def fake_run_text(command, *, cwd=None):
                output_arg = next(arg for arg in command if str(arg).startswith("-o"))
                target = Path(str(output_arg)[2:])
                install_dir = target / "$PLUGINSDIR" / "app"
                install_dir.mkdir(parents=True)
                (install_dir / "cc-branch-backend.exe").write_text("backend", encoding="utf-8")
                (install_dir / "cc-branch.exe").write_text("app", encoding="utf-8")
                return ""

            with mock.patch.object(verify_desktop_installers.platform, "system", return_value="Windows"), \
                 mock.patch.object(verify_desktop_installers, "find_7z", return_value="7z"), \
                 mock.patch.object(verify_desktop_installers, "run_text", side_effect=fake_run_text), \
                 mock.patch.object(verify_desktop_installers, "read_windows_executable_version", return_value="1.0.1"):
                with self.assertRaisesRegex(ValueError, "does not match expected"):
                    verify_desktop_installers.verify_nsis(
                        bundle_dir,
                        expected_version="1.0.2",
                    )

    def test_verify_nsis_rejects_wrong_asset_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            nsis = bundle_dir / "CC.Branch_1.0.1_x64-setup.exe"
            nsis.write_bytes(b"exe")

            with self.assertRaisesRegex(ValueError, "does not match expected"):
                verify_desktop_installers.verify_nsis(
                    bundle_dir,
                    expected_version="1.0.2",
                )

    def test_verify_nsis_rejects_launch_request_on_non_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            (bundle_dir / "CC.Branch_1.0.2_x64-setup.exe").write_bytes(b"exe")

            with mock.patch.object(verify_desktop_installers.platform, "system", return_value="Linux"):
                with self.assertRaisesRegex(RuntimeError, "requires Windows"):
                    verify_desktop_installers.verify_nsis(bundle_dir, launch_app=True)

    def test_verify_nsis_rejects_empty_backend_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            nsis = bundle_dir / "CC.Branch_1.0.2_x64-setup.exe"
            nsis.write_bytes(b"exe")

            def fake_run_text(command, *, cwd=None):
                output_arg = next(arg for arg in command if str(arg).startswith("-o"))
                target = Path(str(output_arg)[2:])
                install_dir = target / "$PLUGINSDIR" / "app"
                install_dir.mkdir(parents=True)
                (install_dir / "cc-branch-backend.exe").write_bytes(b"")
                (install_dir / "cc-branch.exe").write_text("app", encoding="utf-8")
                return ""

            with mock.patch.object(verify_desktop_installers.platform, "system", return_value="Windows"), \
                 mock.patch.object(verify_desktop_installers, "find_7z", return_value="7z"), \
                 mock.patch.object(verify_desktop_installers, "run_text", side_effect=fake_run_text):
                with self.assertRaisesRegex(ValueError, "empty"):
                    verify_desktop_installers.verify_nsis(bundle_dir)

    def test_verify_nsis_rejects_duplicate_app_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            nsis = bundle_dir / "CC.Branch_1.0.2_x64-setup.exe"
            nsis.write_bytes(b"exe")

            def fake_run_text(command, *, cwd=None):
                output_arg = next(arg for arg in command if str(arg).startswith("-o"))
                target = Path(str(output_arg)[2:])
                install_dir = target / "$PLUGINSDIR" / "app"
                alt_dir = target / "$PLUGINSDIR" / "app-copy"
                install_dir.mkdir(parents=True)
                alt_dir.mkdir(parents=True)
                (install_dir / "cc-branch-backend.exe").write_text("backend", encoding="utf-8")
                (install_dir / "cc-branch.exe").write_text("app", encoding="utf-8")
                (alt_dir / "cc-branch.exe").write_text("app", encoding="utf-8")
                return ""

            with mock.patch.object(verify_desktop_installers.platform, "system", return_value="Windows"), \
                 mock.patch.object(verify_desktop_installers, "find_7z", return_value="7z"), \
                 mock.patch.object(verify_desktop_installers, "run_text", side_effect=fake_run_text):
                with self.assertRaisesRegex(ValueError, "multiple.*cc-branch.exe"):
                    verify_desktop_installers.verify_nsis(bundle_dir)

    def test_verify_nsis_rejects_split_app_and_backend_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()
            nsis = bundle_dir / "CC.Branch_1.0.2_x64-setup.exe"
            nsis.write_bytes(b"exe")

            def fake_run_text(command, *, cwd=None):
                output_arg = next(arg for arg in command if str(arg).startswith("-o"))
                target = Path(str(output_arg)[2:])
                app_dir = target / "$PLUGINSDIR" / "app"
                backend_dir = target / "$PLUGINSDIR" / "sidecar"
                app_dir.mkdir(parents=True)
                backend_dir.mkdir(parents=True)
                (app_dir / "cc-branch.exe").write_text("app", encoding="utf-8")
                (backend_dir / "cc-branch-backend.exe").write_text("backend", encoding="utf-8")
                return ""

            with mock.patch.object(verify_desktop_installers.platform, "system", return_value="Windows"), \
                 mock.patch.object(verify_desktop_installers, "find_7z", return_value="7z"), \
                 mock.patch.object(verify_desktop_installers, "run_text", side_effect=fake_run_text):
                with self.assertRaisesRegex(ValueError, "same directory"):
                    verify_desktop_installers.verify_nsis(bundle_dir)

    def test_verify_installers_passes_windows_msi_launch_flag(self):
        with mock.patch.object(verify_desktop_installers, "verify_msi", return_value={"asset": "msi"}) as msi, \
             mock.patch.object(verify_desktop_installers, "verify_nsis", return_value={"asset": "nsis"}):
            verify_desktop_installers.verify_installers(
                Path("/tmp/release"),
                "windows",
                launch_windows_msi=True,
            )

        msi.assert_called_once_with(
            Path("/tmp/release"),
            expected_version=None,
            launch_app=True,
        )

    def test_verify_installers_passes_windows_nsis_launch_flag(self):
        with mock.patch.object(verify_desktop_installers, "verify_msi", return_value={"asset": "msi"}), \
             mock.patch.object(verify_desktop_installers, "verify_nsis", return_value={"asset": "nsis"}) as nsis:
            verify_desktop_installers.verify_installers(
                Path("/tmp/release"),
                "windows",
                launch_windows_nsis=True,
            )

        nsis.assert_called_once_with(
            Path("/tmp/release"),
            expected_version=None,
            launch_app=True,
        )


if __name__ == "__main__":
    unittest.main()
