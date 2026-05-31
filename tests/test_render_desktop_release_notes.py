import json
import tempfile
import unittest
from pathlib import Path

from scripts.render_desktop_release_notes import DOWNLOAD_ROWS, render_release_notes, select_asset
from scripts.verify_release_canary import CHECKSUMS_ASSET_NAME, REQUIRED_DOWNLOAD_ASSETS


ASSETS = [
    {"name": "CC.Branch_1.0.2_aarch64.dmg", "size": 12_000_000},
    {"name": "CC.Branch_1.0.2_x64.dmg", "size": 13_000_000},
    {"name": "cc-branch_1.0.2_x64_en-US.msi", "size": 22_000_000},
    {"name": "cc-branch_1.0.2_x64-setup.exe", "size": 23_000_000},
    {"name": "cc-branch_1.0.2_amd64.deb", "size": 18_000_000},
    {"name": "cc-branch-1.0.2-1.x86_64.rpm", "size": 19_000_000},
    {"name": "cc-branch_1.0.2_amd64.AppImage", "size": 24_000_000},
]


class DesktopReleaseNotesTests(unittest.TestCase):
    def test_release_notes_include_exact_download_links(self):
        notes = render_release_notes(
            repo="GeminiLight/cc-branch",
            tag="v1.0.2",
            assets=ASSETS,
        )

        self.assertIn("# CC Branch Desktop v1.0.2", notes)
        self.assertIn("## Download the right installer", notes)
        self.assertIn(
            "[CC.Branch_1.0.2_aarch64.dmg](https://github.com/GeminiLight/cc-branch/releases/download/v1.0.2/CC.Branch_1.0.2_aarch64.dmg)",
            notes,
        )
        self.assertIn(
            "[cc-branch_1.0.2_x64_en-US.msi](https://github.com/GeminiLight/cc-branch/releases/download/v1.0.2/cc-branch_1.0.2_x64_en-US.msi)",
            notes,
        )
        self.assertIn("bundled backend starts automatically", notes)
        self.assertIn("No separate Python install is required for the desktop app.", notes)
        self.assertIn("drag CC Branch to Applications", notes)
        self.assertIn("run the MSI or setup EXE", notes)
        self.assertIn("run the AppImage directly", notes)
        self.assertIn("Do not use GitHub's Source code zip or tar.gz downloads", notes)
        self.assertIn("Copy report", notes)
        self.assertIn("attach the report when filing an issue", notes)
        self.assertIn("download the installer for your platform from the table above", notes)
        self.assertIn("Local backend ready", notes)
        self.assertIn("Add project", notes)
        self.assertIn("local directory or SSH workspace", notes)
        self.assertIn("## Verify your download", notes)
        self.assertIn(
            f"[{CHECKSUMS_ASSET_NAME}](https://github.com/GeminiLight/cc-branch/releases/download/v1.0.2/{CHECKSUMS_ASSET_NAME})",
            notes,
        )
        self.assertNotIn("download the latest installer", notes)

    def test_release_notes_use_canary_recommended_asset_contract(self):
        self.assertEqual(
            [(label, pattern) for label, pattern, _note in DOWNLOAD_ROWS],
            list(REQUIRED_DOWNLOAD_ASSETS),
        )

    def test_release_notes_reject_missing_recommended_asset(self):
        assets = [asset for asset in ASSETS if not asset["name"].endswith("x64_en-US.msi")]

        with self.assertRaisesRegex(ValueError, "Windows MSI"):
            render_release_notes(repo="GeminiLight/cc-branch", tag="v1.0.2", assets=assets)

    def test_release_notes_reject_stale_recommended_asset_from_wrong_version(self):
        assets = [
            {"name": "CC.Branch_1.0.1_aarch64.dmg", "size": 12_000_000},
            *ASSETS,
        ]

        with self.assertRaisesRegex(ValueError, "expected version 1.0.2"):
            render_release_notes(repo="GeminiLight/cc-branch", tag="v1.0.2", assets=assets)

    def test_release_notes_reject_stale_recommended_asset_from_version_prefix_match(self):
        assets = [
            {"name": "CC.Branch_1.0.20_aarch64.dmg", "size": 12_000_000},
            *[asset for asset in ASSETS if asset["name"] != "CC.Branch_1.0.2_aarch64.dmg"],
        ]

        with self.assertRaisesRegex(ValueError, "expected version 1.0.2"):
            render_release_notes(repo="GeminiLight/cc-branch", tag="v1.0.2", assets=assets)

    def test_release_notes_reject_ambiguous_recommended_assets(self):
        assets = [
            {"name": "CC.Branch_1.0.2_aarch64-copy.dmg", "size": 12_000_000},
            *ASSETS,
        ]

        with self.assertRaisesRegex(ValueError, "multiple recommended download assets"):
            render_release_notes(repo="GeminiLight/cc-branch", tag="v1.0.2", assets=assets)

    def test_select_asset_rejects_empty_asset(self):
        assets = [{"name": "cc-branch_1.0.2_x64_en-US.msi", "size": 0}]

        with self.assertRaisesRegex(ValueError, "empty"):
            select_asset(assets, "Windows MSI", r"x64_en-US\.msi$")

    def test_release_notes_do_not_select_auxiliary_assets(self):
        assets = [
            asset for asset in ASSETS if asset["name"] != "cc-branch_1.0.2_x64-setup.exe"
        ]
        assets.append({"name": "cc-branch_1.0.2_x64-setup.exe.blockmap", "size": 23_000_000})

        with self.assertRaisesRegex(ValueError, "Windows NSIS setup"):
            render_release_notes(repo="GeminiLight/cc-branch", tag="v1.0.2", assets=assets)

    def test_release_notes_can_read_gh_assets_json_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "assets.json"
            path.write_text(json.dumps({"assets": ASSETS}), encoding="utf-8")

            notes = render_release_notes(
                repo="GeminiLight/cc-branch",
                tag="v1.0.2",
                assets=path,
            )

        self.assertIn("cc-branch_1.0.2_amd64.AppImage", notes)


if __name__ == "__main__":
    unittest.main()
