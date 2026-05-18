from __future__ import annotations

import json
import unittest
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
TAURI_DIR = ROOT / "apps" / "desktop" / "src-tauri"


class DesktopTauriConfigTests(unittest.TestCase):
    def test_macos_entitlements_disable_library_validation_for_pyinstaller_sidecar(self):
        config = json.loads((TAURI_DIR / "tauri.conf.json").read_text(encoding="utf-8"))
        entitlements = config["bundle"]["macOS"]["entitlements"]
        self.assertEqual(entitlements, "entitlements.plist")

        tree = ElementTree.parse(TAURI_DIR / entitlements)
        keys = [
            element.text
            for element in tree.findall("./dict/key")
        ]
        self.assertIn("com.apple.security.cs.disable-library-validation", keys)


if __name__ == "__main__":
    unittest.main()
