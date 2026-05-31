import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cc_branch.application.diagnostics import get_diagnostic_bundle


class DiagnosticBundleTests(unittest.TestCase):
    def test_bundle_includes_redacted_paths_schema_and_doctor_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cc_dir = root / ".cc-branch"
            cc_dir.mkdir()
            config_path = cc_dir / "config.yaml"
            state_path = cc_dir / "state.yaml"
            config_path.write_text(
                """
version: 2
project: demo
root: .
tabs:
  - name: dev
    panes:
      - name: shell
        command: zsh
""".strip(),
                encoding="utf-8",
            )
            state_path.write_text("version: 1\nwindows: {}\nslots: {}\n", encoding="utf-8")

            bundle = get_diagnostic_bundle(config_path, state_path, backend_port=5192)

            self.assertEqual(bundle["kind"], "cc-branch-diagnostic-bundle")
            self.assertEqual(bundle["backend"]["port"], 5192)
            self.assertEqual(bundle["backend"]["source"], "cli")
            self.assertEqual(bundle["schema"]["config"]["current_version"], 2)
            self.assertEqual(bundle["schema"]["state"]["current_version"], 1)
            self.assertEqual(bundle["project"]["name"], "demo")
            self.assertIn("doctor", bundle)
            self.assertIn("logs", bundle)
            self.assertNotIn(str(Path.home()), str(bundle))

    def test_bundle_includes_desktop_backend_source_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch" / "config.yaml"
            state_path = root / ".cc-branch" / "state.yaml"

            with patch.dict("os.environ", {"CC_BRANCH_BACKEND_SOURCE": "bundled-sidecar"}):
                bundle = get_diagnostic_bundle(config_path, state_path, backend_port=5192)

            self.assertEqual(bundle["backend"]["source"], "bundled-sidecar")

    def test_bundle_reports_missing_config_without_throwing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch" / "config.yaml"
            state_path = root / ".cc-branch" / "state.yaml"

            bundle = get_diagnostic_bundle(config_path, state_path)

            self.assertEqual(bundle["doctor"]["status"], "needs_init")
            self.assertEqual(bundle["files"]["config"]["exists"], False)

    def test_bundle_collects_recent_redacted_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cc_dir = root / ".cc-branch"
            logs_dir = root / "logs"
            cc_dir.mkdir()
            logs_dir.mkdir()
            config_path = cc_dir / "config.yaml"
            state_path = cc_dir / "state.yaml"
            config_path.write_text(
                """
version: 2
project: demo
root: .
tabs:
  - name: dev
    panes:
      - name: shell
        command: zsh
""".strip(),
                encoding="utf-8",
            )
            state_path.write_text("version: 1\nwindows: {}\nslots: {}\n", encoding="utf-8")
            log_file = logs_dir / "desktop.log"
            log_file.write_text(f"started in {Path.home()}\nready\n", encoding="utf-8")

            bundle = get_diagnostic_bundle(config_path, state_path, log_dirs=[logs_dir])

            self.assertEqual(bundle["logs"]["available"], True)
            self.assertEqual(bundle["logs"]["recent"][0]["lines"][-1], "ready")
            self.assertNotIn(str(Path.home()), str(bundle["logs"]))


if __name__ == "__main__":
    unittest.main()
