import tempfile
import textwrap
import unittest
from pathlib import Path

from cc_branch.models import WindowState, WorkspaceState
from cc_branch.state import load_state, merge_state, save_state


class StateTests(unittest.TestCase):
    """Tests for state management functionality."""

    def _write(self, path: Path, content: str) -> None:
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def test_load_state_returns_empty_for_missing_file(self):
        """Test that load_state returns empty state for missing file."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "nonexistent.yaml"

            state = load_state(state_path)
            self.assertEqual(state.version, 1)
            self.assertEqual(state.windows, {})

    def test_load_state_parses_existing_state(self):
        """Test that load_state correctly parses existing state file."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / ".cc-branch.state.yaml"
            self._write(
                state_path,
                """
                version: 1
                windows:
                  dev.editor:
                    session_id: "12345678-1234-1234-1234-123456789012"
                    label: "project/dev/editor"
                    agent: "claude"
                """,
            )

            state = load_state(state_path)
            self.assertEqual(state.version, 1)
            self.assertIn("dev.editor", state.windows)
            self.assertEqual(
                state.windows["dev.editor"].session_id,
                "12345678-1234-1234-1234-123456789012"
            )
            self.assertEqual(state.windows["dev.editor"].label, "project/dev/editor")

    def test_save_state_creates_valid_yaml(self):
        """Test that save_state creates a valid YAML file."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / ".cc-branch.state.yaml"

            state = WorkspaceState(
                version=1,
                windows={
                    "dev.editor": WindowState(
                        session_id="test-session-id",
                        label="test/dev/editor",
                        agent="claude",
                    )
                },
            )

            save_state(state_path, state)
            self.assertTrue(state_path.exists())
            content = state_path.read_text(encoding="utf-8")
            self.assertIn("version: 1", content)
            self.assertIn("dev.editor:", content)
            self.assertNotIn("[windows.", content)

            # Verify it can be loaded back
            loaded_state = load_state(state_path)
            self.assertEqual(loaded_state.version, 1)
            self.assertEqual(
                loaded_state.windows["dev.editor"].session_id,
                "test-session-id"
            )

    def test_save_state_round_trip(self):
        """Test that state can be saved and loaded without data loss."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / ".cc-branch.state.yaml"

            original_state = WorkspaceState(
                version=1,
                windows={
                    "dev.planner": WindowState(
                        session_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                        label="demo/dev/planner",
                        agent="claude",
                    ),
                    "dev.review": WindowState(
                        session_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                        label="demo/dev/review",
                        agent="codex",
                    )
                },
            )

            save_state(state_path, original_state)
            loaded_state = load_state(state_path)

            self.assertEqual(loaded_state.to_dict(), original_state.to_dict())

    def test_merge_state_preserves_existing_windows(self):
        """Test that merge_state preserves existing window state."""
        existing_state = WorkspaceState(
            version=1,
            windows={
                "dev.editor": WindowState(
                    session_id="existing-id",
                    label="project/dev/editor",
                )
            },
        )

        state_updates = {}

        merged = merge_state(existing_state, state_updates)

        # Should keep existing session_id
        self.assertEqual(
            merged.windows["dev.editor"].session_id,
            "existing-id"
        )

    def test_merge_state_adds_new_windows(self):
        """Test that merge_state adds new windows from plan."""
        existing_state = WorkspaceState(
            version=1,
            windows={},
        )

        state_updates = {
            "dev.editor": {
                "session_id": "new-id",
                "label": "project/dev/editor",
                "agent": "claude",
            }
        }

        merged = merge_state(existing_state, state_updates)

        self.assertIn("dev.editor", merged.windows)
        self.assertEqual(
            merged.windows["dev.editor"].session_id,
            "new-id"
        )

    def test_merge_state_handles_empty_plan(self):
        """Test that merge_state handles empty plan gracefully."""
        existing_state = WorkspaceState(
            version=1,
            windows={
                "dev.editor": WindowState(
                    session_id="existing-id",
                    label="project/dev/editor",
                )
            },
        )

        state_updates = {}

        merged = merge_state(existing_state, state_updates)

        # Should preserve existing state
        self.assertEqual(merged.to_dict(), existing_state.to_dict())

    def test_state_version_is_preserved(self):
        """Test that state version is preserved through operations."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / ".cc-branch.state.yaml"

            state = WorkspaceState(version=1, windows={})
            save_state(state_path, state)
            loaded = load_state(state_path)

            self.assertEqual(loaded.version, 1)

    def test_load_state_rejects_toml_state_file(self):
        """TOML state files are not supported for the first release."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / ".cc-branch.state.toml"
            self._write(state_path, "version = 1")

            with self.assertRaises(ValueError):
                load_state(state_path)


if __name__ == '__main__':
    unittest.main()
