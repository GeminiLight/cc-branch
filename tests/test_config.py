import tempfile
import textwrap
import unittest
from pathlib import Path

from cc_branch.config import init_workspace, load_workspace


class ConfigTests(unittest.TestCase):
    """Tests for configuration loading and initialization."""

    def _write(self, path: Path, content: str) -> None:
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def test_load_workspace_parses_basic_config(self):
        """Test that load_workspace correctly parses a basic configuration."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "test-project"
                root: "."
                """,
            )

            workspace = load_workspace(config_path)
            self.assertEqual(workspace.version, 1)
            self.assertEqual(workspace.project, "test-project")
            # root is resolved to absolute path
            self.assertTrue(workspace.root.endswith(tmp))

    def test_load_workspace_parses_agents(self):
        """Test that load_workspace correctly parses agent definitions."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "test"
                root: "."

                agents:
                  claude:
                    command: "claude"
                    create_mode: "generated_uuid"
                """,
            )

            workspace = load_workspace(config_path)
            self.assertIn("claude", workspace.agents)
            self.assertEqual(workspace.agents["claude"].command, "claude")
            self.assertEqual(workspace.agents["claude"].create_mode, "generated_uuid")

    def test_load_workspace_parses_slots(self):
        """Test that load_workspace correctly parses slot definitions."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "test"
                root: "."

                slots:
                  - name: "dev"
                    backend: "tmux"
                    windows:
                      - name: "editor"
                        command: "vim"
                """,
            )

            workspace = load_workspace(config_path)
            self.assertEqual(len(workspace.slots), 1)
            self.assertEqual(workspace.slots[0].name, "dev")
            self.assertEqual(workspace.slots[0].backend, "tmux")
            self.assertEqual(len(workspace.slots[0].windows), 1)
            self.assertEqual(workspace.slots[0].windows[0].name, "editor")

    def test_load_workspace_raises_on_missing_file(self):
        """Test that load_workspace raises FileNotFoundError for missing config."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "nonexistent.toml"

            with self.assertRaises(FileNotFoundError):
                load_workspace(config_path)

    def test_init_workspace_creates_default_config(self):
        """Test that init_workspace creates a valid default configuration."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, state_path = init_workspace(root, force=False, bootstrap_sessions=False)

            self.assertTrue(config_path.exists())
            self.assertTrue(state_path.exists())

            # Verify the config is valid
            workspace = load_workspace(config_path)
            self.assertEqual(workspace.version, 1)
            self.assertTrue(hasattr(workspace, "project"))

    def test_init_workspace_with_bootstrap_sessions(self):
        """Test that init_workspace with bootstrap_sessions creates state."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, state_path = init_workspace(root, force=False, bootstrap_sessions=True)

            self.assertTrue(state_path.exists())
            content = state_path.read_text()
            self.assertIn("windows", content)

    def test_init_workspace_force_overwrites_existing(self):
        """Test that init_workspace with force=True overwrites existing files."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch.yaml"
            config_path.write_text("old content")

            new_config_path, _ = init_workspace(root, force=True, bootstrap_sessions=False)

            self.assertEqual(config_path, new_config_path)
            self.assertNotEqual(config_path.read_text(), "old content")

    def test_load_workspace_parses_display_config(self):
        """Test that load_workspace correctly parses display configuration."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "test"
                root: "."

                display:
                  dashboard: true
                  mode: "grid"
                  columns: 2
                """,
            )

            workspace = load_workspace(config_path)
            self.assertTrue(workspace.display.dashboard)
            self.assertEqual(workspace.display.mode, "grid")
            self.assertEqual(workspace.display.columns, 2)

    def test_load_workspace_parses_env_variables(self):
        """Test that load_workspace correctly parses environment variables."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "test"
                root: "."

                slots:
                  - name: "dev"
                    backend: "shell"
                    command: "bash"
                    env:
                      DEBUG: "true"
                      PORT: 8080
                """,
            )

            workspace = load_workspace(config_path)
            slot = workspace.slots[0]
            self.assertIn("DEBUG", slot.env)
            self.assertEqual(slot.env["DEBUG"], "true")
            self.assertEqual(slot.env["PORT"], 8080)


if __name__ == '__main__':
    unittest.main()
