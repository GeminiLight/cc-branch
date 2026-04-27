from __future__ import annotations

import importlib.util
import sys
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


if __name__ == "__main__":
    unittest.main()
