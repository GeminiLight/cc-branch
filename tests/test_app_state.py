from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cc_branch.app_state import ProjectIndexStore


class ProjectIndexStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tmpdir.name) / ".cc-branch/app/projects.yaml"
        self.store = ProjectIndexStore(self.path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_empty_payload_when_file_missing(self):
        payload = self.store.payload()

        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["projects"], [])
        self.assertIsNone(payload["active_project_id"])
        self.assertEqual(payload["storage_path"], str(self.path))

    def test_add_project_sets_active(self):
        payload = self.store.add_project("/tmp/demo")

        self.assertEqual(len(payload["projects"]), 1)
        self.assertEqual(payload["projects"][0]["name"], "demo")
        self.assertEqual(payload["active_project_id"], payload["projects"][0]["id"])

    def test_add_project_derives_name_from_trailing_slash_path(self):
        payload = self.store.add_project("/tmp/demo/")

        self.assertEqual(payload["projects"][0]["name"], "demo")

    def test_add_project_deduplicates_by_path(self):
        first = self.store.add_project("/tmp/demo", name="demo-a")
        first_id = first["projects"][0]["id"]

        second = self.store.add_project("/tmp/demo", name="demo-b")
        self.assertEqual(len(second["projects"]), 1)
        self.assertEqual(second["projects"][0]["id"], first_id)
        self.assertEqual(second["projects"][0]["name"], "demo-b")

    def test_remove_active_project_falls_back_to_previous(self):
        added = self.store.add_project("/tmp/a")
        a_id = added["projects"][0]["id"]
        added = self.store.add_project("/tmp/b")
        b_id = added["projects"][1]["id"]
        self.store.activate_project(a_id)

        payload = self.store.remove_project(a_id)
        self.assertEqual([item["id"] for item in payload["projects"]], [b_id])
        self.assertEqual(payload["active_project_id"], b_id)

    def test_inject_current_upgrades_existing_path(self):
        self.store.add_project("/tmp/demo", name="workspace")

        payload = self.store.inject_current_project(
            "/tmp/demo",
            selected_config_path="/tmp/demo/.cc-branch/config.yaml",
        )
        self.assertEqual(payload["projects"][0]["id"], "current")
        self.assertEqual(payload["active_project_id"], "current")
        self.assertEqual(
            payload["projects"][0]["selected_config_path"],
            str(Path("/tmp/demo/.cc-branch/config.yaml").resolve(strict=False)),
        )

    def test_inject_current_preserves_different_active_project(self):
        first = self.store.add_project("/tmp/current")
        current_project_id = first["projects"][0]["id"]
        second = self.store.add_project("/tmp/research")
        research_project_id = second["projects"][1]["id"]
        self.store.activate_project(research_project_id)

        payload = self.store.inject_current_project(
            "/tmp/current",
            selected_config_path="/tmp/current/.cc-branch/config.yaml",
        )

        self.assertEqual(payload["active_project_id"], research_project_id)
        self.assertEqual(payload["projects"][0]["id"], "current")
        self.assertNotIn(current_project_id, {item["id"] for item in payload["projects"]})

    def test_set_project_config_updates_record(self):
        self.store.add_project("/tmp/demo")

        payload = self.store.set_project_config("/tmp/demo", "/tmp/demo/.cc-branch/configs/review.yaml")
        self.assertEqual(len(payload["projects"]), 1)
        self.assertEqual(
            payload["projects"][0]["selected_config_path"],
            str(Path("/tmp/demo/.cc-branch/configs/review.yaml").resolve(strict=False)),
        )

    def test_project_pin_state_is_persisted(self):
        added = self.store.add_project("/tmp/demo")
        project_id = added["projects"][0]["id"]

        pinned = self.store.set_project_pinned(project_id, True)

        self.assertTrue(pinned["projects"][0]["pinned"])
        reloaded = ProjectIndexStore(self.path).payload()
        self.assertTrue(reloaded["projects"][0]["pinned"])

    def test_reorder_project_moves_before_target(self):
        a = self.store.add_project("/tmp/a")["projects"][0]["id"]
        b = self.store.add_project("/tmp/b")["projects"][1]["id"]
        c = self.store.add_project("/tmp/c")["projects"][2]["id"]

        payload = self.store.reorder_project(c, before_id=a)

        self.assertEqual([item["id"] for item in payload["projects"]], [c, a, b])

    def test_save_creates_backup(self):
        self.store.add_project("/tmp/a")
        self.assertTrue(self.path.exists())

        self.store.add_project("/tmp/b")
        backup_path = self.path.with_suffix(".yaml.bak")
        self.assertTrue(backup_path.exists())

    def test_payload_recovers_from_backup_when_index_is_malformed(self):
        saved = self.store.add_project("/tmp/a")
        first_id = saved["projects"][0]["id"]
        backup_path = self.path.with_suffix(".yaml.bak")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
        self.path.write_text("projects: [", encoding="utf-8")

        payload = self.store.payload()

        self.assertEqual(payload["active_project_id"], first_id)
        self.assertEqual([item["path"] for item in payload["projects"]], [str(Path("/tmp/a").resolve(strict=False))])

    def test_add_project_preserves_backup_projects_when_index_is_malformed(self):
        self.store.add_project("/tmp/a")
        backup_path = self.path.with_suffix(".yaml.bak")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
        self.path.write_text("projects: [", encoding="utf-8")

        payload = self.store.add_project("/tmp/b")

        self.assertEqual(
            [item["path"] for item in payload["projects"]],
            [str(Path("/tmp/a").resolve(strict=False)), str(Path("/tmp/b").resolve(strict=False))],
        )

    def test_add_project_does_not_replace_valid_backup_with_malformed_index(self):
        self.store.add_project("/tmp/a")
        backup_path = self.path.with_suffix(".yaml.bak")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
        self.path.write_text("projects: [", encoding="utf-8")

        self.store.add_project("/tmp/b")

        backup_payload = ProjectIndexStore(backup_path).payload()
        self.assertEqual(
            [item["path"] for item in backup_payload["projects"]],
            [str(Path("/tmp/a").resolve(strict=False))],
        )


if __name__ == "__main__":
    unittest.main()
