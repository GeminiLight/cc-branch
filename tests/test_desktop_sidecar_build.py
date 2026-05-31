from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build-desktop-sidecar.py"
spec = importlib.util.spec_from_file_location("build_desktop_sidecar", SCRIPT_PATH)
assert spec is not None
build_desktop_sidecar = importlib.util.module_from_spec(spec)
sys.modules["build_desktop_sidecar"] = build_desktop_sidecar
assert spec.loader is not None
spec.loader.exec_module(build_desktop_sidecar)


class DesktopSidecarBuildTests(unittest.TestCase):
    def test_windows_target_uses_exe_suffix(self):
        self.assertEqual(
            build_desktop_sidecar.executable_suffix("x86_64-pc-windows-msvc"),
            ".exe",
        )

    def test_unix_targets_do_not_use_exe_suffix(self):
        self.assertEqual(build_desktop_sidecar.executable_suffix("aarch64-apple-darwin"), "")
        self.assertEqual(build_desktop_sidecar.executable_suffix("x86_64-unknown-linux-gnu"), "")

    def test_rust_host_triple_parses_rustc_verbose_version(self):
        output = "rustc 1.77.2\nbinary: rustc\nhost: aarch64-apple-darwin\nrelease: 1.77.2\n"
        with patch("build_desktop_sidecar.subprocess.check_output", return_value=output):
            self.assertEqual(build_desktop_sidecar.rust_host_triple(), "aarch64-apple-darwin")

    def test_copy_sidecar_uses_tauri_target_triple_naming(self):
        with self.subTest("unix"):
            self.assertTrue(
                str(
                    build_desktop_sidecar.BINARIES_DIR
                    / "cc-branch-backend-x86_64-unknown-linux-gnu"
                ).endswith("cc-branch-backend-x86_64-unknown-linux-gnu")
            )
        with self.subTest("windows"):
            self.assertTrue(
                str(
                    build_desktop_sidecar.BINARIES_DIR
                    / "cc-branch-backend-x86_64-pc-windows-msvc.exe"
                ).endswith("cc-branch-backend-x86_64-pc-windows-msvc.exe")
            )

    def test_release_target_architecture_maps_to_binary_arch(self):
        self.assertEqual(
            build_desktop_sidecar.expected_binary_architecture("aarch64-apple-darwin"),
            "arm64",
        )
        self.assertEqual(
            build_desktop_sidecar.expected_binary_architecture("x86_64-apple-darwin"),
            "x86_64",
        )
        self.assertEqual(
            build_desktop_sidecar.expected_binary_architecture("x86_64-unknown-linux-gnu"),
            "x86_64",
        )
        self.assertEqual(
            build_desktop_sidecar.expected_binary_architecture("x86_64-pc-windows-msvc"),
            "x86_64",
        )

    def test_validate_sidecar_architecture_rejects_mislabeled_macos_binary(self):
        with patch("build_desktop_sidecar.subprocess.check_output", return_value="x86_64\n"):
            with self.assertRaisesRegex(RuntimeError, "expected arm64"):
                build_desktop_sidecar.validate_sidecar_architecture(
                    Path("/tmp/cc-branch-backend-aarch64-apple-darwin"),
                    "aarch64-apple-darwin",
                )

    def test_validate_sidecar_architecture_accepts_matching_macos_binary(self):
        with patch("build_desktop_sidecar.subprocess.check_output", return_value="x86_64 arm64\n"):
            build_desktop_sidecar.validate_sidecar_architecture(
                Path("/tmp/cc-branch-backend-aarch64-apple-darwin"),
                "aarch64-apple-darwin",
            )

    def test_validate_sidecar_architecture_rejects_mislabeled_linux_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "cc-branch-backend-x86_64-unknown-linux-gnu"
            header = bytearray(64)
            header[0:4] = b"\x7fELF"
            header[4] = 2
            header[5] = 1
            header[18:20] = (183).to_bytes(2, "little")  # AArch64
            binary.write_bytes(header)

            with self.assertRaisesRegex(RuntimeError, "expected x86_64"):
                build_desktop_sidecar.validate_sidecar_architecture(
                    binary,
                    "x86_64-unknown-linux-gnu",
                )

    def test_validate_sidecar_architecture_accepts_matching_linux_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "cc-branch-backend-x86_64-unknown-linux-gnu"
            header = bytearray(64)
            header[0:4] = b"\x7fELF"
            header[4] = 2
            header[5] = 1
            header[18:20] = (62).to_bytes(2, "little")  # x86_64
            binary.write_bytes(header)

            build_desktop_sidecar.validate_sidecar_architecture(
                binary,
                "x86_64-unknown-linux-gnu",
            )

    def test_validate_sidecar_architecture_rejects_mislabeled_windows_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "cc-branch-backend-x86_64-pc-windows-msvc.exe"
            content = bytearray(160)
            content[0:2] = b"MZ"
            content[0x3C:0x40] = (0x80).to_bytes(4, "little")
            content[0x80:0x84] = b"PE\0\0"
            content[0x84:0x86] = (0xAA64).to_bytes(2, "little")  # ARM64
            binary.write_bytes(content)

            with self.assertRaisesRegex(RuntimeError, "expected x86_64"):
                build_desktop_sidecar.validate_sidecar_architecture(
                    binary,
                    "x86_64-pc-windows-msvc",
                )

    def test_validate_sidecar_architecture_accepts_matching_windows_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "cc-branch-backend-x86_64-pc-windows-msvc.exe"
            content = bytearray(160)
            content[0:2] = b"MZ"
            content[0x3C:0x40] = (0x80).to_bytes(4, "little")
            content[0x80:0x84] = b"PE\0\0"
            content[0x84:0x86] = (0x8664).to_bytes(2, "little")  # x86_64
            binary.write_bytes(content)

            build_desktop_sidecar.validate_sidecar_architecture(
                binary,
                "x86_64-pc-windows-msvc",
            )

    def test_main_validates_pyinstaller_output_before_copying_sidecar(self):
        with patch("build_desktop_sidecar.run_pyinstaller") as run_pyinstaller, \
             patch("build_desktop_sidecar.pyinstaller_executable", return_value=Path("/tmp/cc-branch-backend")), \
             patch("build_desktop_sidecar.validate_sidecar_architecture", side_effect=RuntimeError("wrong arch")) as validate, \
             patch("build_desktop_sidecar.copy_sidecar") as copy_sidecar:
            with self.assertRaisesRegex(RuntimeError, "wrong arch"):
                build_desktop_sidecar.main(["--target", "aarch64-apple-darwin"])

        run_pyinstaller.assert_called_once_with("aarch64-apple-darwin")
        validate.assert_called_once_with(Path("/tmp/cc-branch-backend"), "aarch64-apple-darwin")
        copy_sidecar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
