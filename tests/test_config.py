import tempfile
import textwrap
import unittest
from pathlib import Path

from cc_branch.config import (
    config_options,
    init_workspace,
    load_workspace,
    project_dir_for_config,
    resolve_config_path,
    resolve_config_selection,
    resolve_state_path,
)


class ConfigTests(unittest.TestCase):
    """Tests for configuration loading and initialization."""

    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def test_load_workspace_parses_basic_config(self):
        """Test that load_workspace correctly parses a basic configuration."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 2
                project: "test-project"
                root: "."
                """,
            )

            workspace = load_workspace(config_path)
            self.assertEqual(workspace.version, 2)
            self.assertEqual(workspace.project, "test-project")
            # root is resolved to absolute path
            self.assertTrue(workspace.root.endswith(tmp))

    def test_load_workspace_parses_agents(self):
        """Test that load_workspace correctly parses agent definitions."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
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

    def test_load_workspace_uses_builtin_agent_registry_when_agents_omitted(self):
        """Agent references should work without repeating built-in profiles in each config."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "test"
                root: "."

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "planner"
                        agent: "codex"
                """,
            )

            workspace = load_workspace(config_path)

            self.assertIn("codex", workspace.agents)
            self.assertEqual(workspace.agents["codex"].command, "codex")
            self.assertEqual(workspace.agents["codex"].resume_mode, "flag")
            self.assertEqual(workspace.agents["codex"].resume_template, "resume {session_id}")
            self.assertNotIn("agents", workspace.to_dict())

    def test_load_workspace_agent_overrides_merge_with_registry_defaults(self):
        """Project agent overrides should not require copying every default field."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "test"
                root: "."

                agents:
                  codex:
                    command: "codex --sandbox read-only"

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "planner"
                        agent: "codex"
                """,
            )

            workspace = load_workspace(config_path)

            self.assertEqual(workspace.agents["codex"].command, "codex --sandbox read-only")
            self.assertEqual(workspace.agents["codex"].resume_mode, "flag")
            self.assertEqual(workspace.agents["codex"].resume_template, "resume {session_id}")
            self.assertEqual(workspace.agents["codex"].label_template, "{project}/{tab}/{pane}")
            self.assertEqual(
                workspace.to_dict()["agents"],
                {"codex": {"command": "codex --sandbox read-only"}},
            )

    def test_load_workspace_reads_workspace_local_agent_registry(self):
        """Workspace-local registry files should add agents without bloating .cc-branch/config.yaml."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/agents.yaml",
                """
                agents:
                  local-agent:
                    command: "local-agent"
                    resume_mode: "flag"
                    resume_template: "--resume {session_id}"
                """,
            )
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "test"
                root: "."

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "main"
                        agent: "local-agent"
                """,
            )

            workspace = load_workspace(config_path)

            self.assertIn("local-agent", workspace.agents)
            self.assertEqual(workspace.agents["local-agent"].command, "local-agent")

    def test_load_workspace_parses_slots(self):
        """Test that load_workspace correctly parses slot definitions."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "test"
                root: "."

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    layout: "main-left"
                    windows:
                      - name: "editor"
                        command: "vim"
                """,
            )

            workspace = load_workspace(config_path)
            self.assertEqual(len(workspace.slots), 1)
            self.assertEqual(workspace.slots[0].name, "dev")
            self.assertEqual(workspace.slots[0].runtime, "tmux")
            self.assertEqual(workspace.slots[0].layout, "main-left")
            self.assertEqual(len(workspace.slots[0].windows), 1)
            self.assertEqual(workspace.slots[0].windows[0].name, "editor")

    def test_load_workspace_parses_agent_session_intent(self):
        """Agent-backed panes should use one session field for intent."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 2
                project: "test"
                root: "."

                tabs:
                  - name: "dev"
                    panes:
                      - name: "planner"
                        runtime: "tmux"
                        agent: "codex"
                        session: "fresh"
                        windows:
                          - name: "planner"
                            agent: "codex"
                            session: "fresh"
                """,
            )

            workspace = load_workspace(config_path)

            slot = workspace.slots[0]
            self.assertEqual(slot.session, "fresh")
            self.assertEqual(slot.windows[0].session, "fresh")

    def test_load_workspace_parses_canonical_workspace_terms(self):
        """Public config should use openWith, layoutBackend, defaults, tabs, and panes."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 2
                project: "test"
                root: "."
                openWith: "cursor"
                layoutBackend: "tmux"
                defaults:
                  shell: "system-default"

                tabs:
                  - name: "dev"
                    panes:
                      - name: "planner"
                        agent: "codex"
                        session: "auto"
                      - name: "server"
                        command: "pnpm dev"
                        shell: "zsh"
                """,
            )

            workspace = load_workspace(config_path)

            self.assertEqual(workspace.default_opener, "cursor")
            self.assertEqual(workspace.layout_backend, "tmux")
            self.assertEqual(workspace.defaults.shell, "system-default")
            self.assertEqual(len(workspace.slots), 1)
            self.assertEqual(workspace.slots[0].name, "dev")
            self.assertEqual(workspace.slots[0].runtime, "tmux")
            self.assertEqual([window.name for window in workspace.slots[0].windows], ["planner", "server"])
            self.assertIsNone(workspace.slots[0].windows[0].shell)
            self.assertEqual(workspace.slots[0].windows[1].shell, "zsh")

    def test_workspace_to_dict_serializes_canonical_terms(self):
        """Normalized configs should serialize with canonical public terminology."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 2
                project: "test"
                root: "."
                openWith: "warp"
                layoutBackend: "tmux"
                defaults:
                  shell: "system-default"
                tabs:
                  - name: "dev"
                    panes:
                      - name: "planner"
                        agent: "codex"
                      - name: "server"
                        command: "pnpm dev"
                        shell: "zsh"
                """,
            )

            serialized = load_workspace(config_path).to_dict()

            self.assertEqual(serialized["openWith"], "warp")
            self.assertEqual(serialized["layoutBackend"], "tmux")
            self.assertEqual(serialized["defaults"], {"shell": "system-default"})
            self.assertNotIn("default_opener", serialized)
            self.assertNotIn("slots", serialized)
            self.assertEqual([pane["name"] for pane in serialized["tabs"][0]["panes"]], ["planner", "server"])
            self.assertNotIn("runtime", serialized["tabs"][0]["panes"][0])
            self.assertNotIn("windows", serialized["tabs"][0]["panes"][0])
            self.assertEqual(serialized["tabs"][0]["panes"][1]["shell"], "zsh")

    def test_workspace_to_dict_preserves_legacy_single_window_terminal_slot(self):
        """Legacy slot-level command fields should not disappear during v2 serialization."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "test"
                root: "."
                slots:
                  - name: "shell"
                    title: "Main shell"
                    runtime: "terminal"
                    command: "zsh"
                """,
            )

            serialized = load_workspace(config_path).to_dict()

            self.assertEqual(serialized["tabs"][0]["name"], "shell")
            self.assertEqual(serialized["tabs"][0]["panes"], [{"name": "Main shell", "command": "zsh"}])

    def test_workspace_to_dict_preserves_legacy_single_window_tmux_slot(self):
        """Legacy tmux slots without windows should keep their launch fields as one pane."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "test"
                root: "."
                slots:
                  - name: "agent"
                    runtime: "tmux"
                    agent: "codex"
                    session: "019dd56d-0700-7bb3-a9c0-83eb2b033b0e"
                """,
            )

            serialized = load_workspace(config_path).to_dict()

            tab = serialized["tabs"][0]
            self.assertEqual(tab["name"], "agent")
            self.assertEqual(tab["layoutBackend"], "tmux")
            self.assertEqual(
                tab["panes"],
                [{
                    "name": "agent",
                    "agent": "codex",
                    "session": "019dd56d-0700-7bb3-a9c0-83eb2b033b0e",
                }],
            )

    def test_workspace_to_dict_preserves_mixed_public_tab_shape(self):
        """A mixed direct/tmux public tab should not reserialize as two tabs."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 2
                project: "test"
                root: "."
                tabs:
                  - name: "dev"
                    layout: "horizontal"
                    panes:
                      - name: "ui"
                        command: "npm run dev"
                      - name: "agents"
                        layoutBackend: "tmux"
                        windows:
                          - name: "planner"
                            agent: "codex"
                          - name: "review"
                            agent: "claude"
                  - name: "docs"
                    panes:
                      - name: "writer"
                        agent: "gemini"
                """,
            )

            serialized = load_workspace(config_path).to_dict()

            self.assertEqual([tab["name"] for tab in serialized["tabs"]], ["dev", "docs"])
            self.assertEqual([pane["name"] for pane in serialized["tabs"][0]["panes"]], ["ui", "agents"])
            self.assertEqual(serialized["tabs"][0]["panes"][1]["layoutBackend"], "tmux")
            self.assertEqual(
                [window["name"] for window in serialized["tabs"][0]["panes"][1]["windows"]],
                ["planner", "review"],
            )

    def test_workspace_to_dict_preserves_interleaved_mixed_public_tab_order(self):
        """Direct panes around a tmux group should keep their visual canvas order."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 2
                project: "test"
                root: "."
                tabs:
                  - name: "dev"
                    panes:
                      - name: "frontend"
                        command: "npm run dev"
                      - name: "agents"
                        layoutBackend: "tmux"
                        windows:
                          - name: "planner"
                            agent: "codex"
                      - name: "docs"
                        command: "npm run docs"
                """,
            )

            serialized = load_workspace(config_path).to_dict()

            panes = serialized["tabs"][0]["panes"]
            self.assertEqual([pane["name"] for pane in panes], ["frontend", "agents", "docs"])
            self.assertEqual(panes[1]["layoutBackend"], "tmux")
            self.assertEqual(panes[1]["windows"][0]["name"], "planner")

    def test_load_workspace_keeps_mixed_tab_direct_panes_as_individual_visual_panes(self):
        """Mixed tabs should expose each direct pane as a separate split-group member."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 2
                project: "test"
                root: "."
                tabs:
                  - name: "dev"
                    panes:
                      - name: "frontend"
                        command: "npm run dev"
                      - name: "backend"
                        command: "python api.py"
                      - name: "agents"
                        layoutBackend: "tmux"
                        windows:
                          - name: "planner"
                            agent: "codex"
                """,
            )

            workspace = load_workspace(config_path)
            serialized = workspace.to_dict()

            self.assertEqual(
                [(slot.name, slot.runtime, slot.split_group, [window.name for window in slot.windows]) for slot in workspace.slots],
                [
                    ("dev", "terminal", "dev", ["frontend"]),
                    ("dev-backend", "terminal", "dev", ["backend"]),
                    ("dev-agents", "tmux", "dev", ["planner"]),
                ],
            )
            self.assertEqual([pane["name"] for pane in serialized["tabs"][0]["panes"]], ["frontend", "backend", "agents"])

    def test_workspace_to_dict_preserves_single_tmux_group_pane(self):
        """A tmux group pane should not be flattened into tab-level tmux panes."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 2
                project: "test"
                root: "."
                tabs:
                  - name: "dev"
                    panes:
                      - name: "agents"
                        layoutBackend: "tmux"
                        windows:
                          - name: "planner"
                            agent: "codex"
                          - name: "review"
                            agent: "claude"
                """,
            )

            serialized = load_workspace(config_path).to_dict()

            self.assertEqual([tab["name"] for tab in serialized["tabs"]], ["dev"])
            self.assertEqual(len(serialized["tabs"][0]["panes"]), 1)
            pane = serialized["tabs"][0]["panes"][0]
            self.assertEqual(pane["name"], "agents")
            self.assertEqual(pane["layoutBackend"], "tmux")
            self.assertEqual([window["name"] for window in pane["windows"]], ["planner", "review"])

    def test_workspace_to_dict_preserves_multiple_tmux_group_panes(self):
        """Multiple tmux group panes in one tab should remain separate panes."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 2
                project: "test"
                root: "."
                tabs:
                  - name: "dev"
                    panes:
                      - name: "agents-a"
                        layoutBackend: "tmux"
                        windows:
                          - name: "planner"
                            agent: "codex"
                      - name: "agents-b"
                        layoutBackend: "tmux"
                        windows:
                          - name: "review"
                            agent: "claude"
                """,
            )

            serialized = load_workspace(config_path).to_dict()

            panes = serialized["tabs"][0]["panes"]
            self.assertEqual([pane["name"] for pane in panes], ["agents-a", "agents-b"])
            self.assertEqual([pane["layoutBackend"] for pane in panes], ["tmux", "tmux"])
            self.assertEqual([pane["windows"][0]["name"] for pane in panes], ["planner", "review"])

    def test_load_workspace_normalizes_legacy_open_with_ids(self):
        """Older Web UI opener ids should normalize to registered opener ids."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 2
                project: "test"
                root: "."
                openWith: "terminal"
                tabs:
                  - name: "dev"
                    panes:
                      - name: "main"
                        command: "zsh"
                """,
            )

            workspace = load_workspace(config_path)

            self.assertEqual(workspace.default_opener, "terminal-app")
            self.assertEqual(workspace.to_dict()["openWith"], "terminal-app")

            self._write(
                config_path,
                """
                version: 2
                project: "test"
                root: "."
                openWith: "iterm"
                tabs:
                  - name: "dev"
                    panes:
                      - name: "main"
                        command: "zsh"
                """,
            )

            workspace = load_workspace(config_path)

            self.assertEqual(workspace.default_opener, "iterm2")
            self.assertEqual(workspace.to_dict()["openWith"], "iterm2")

    def test_load_workspace_migrates_legacy_session_id_to_session_intent(self):
        """Legacy session_id in config should load as explicit session intent."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 2
                project: "test"
                root: "."

                tabs:
                  - name: "dev"
                    panes:
                      - name: "planner"
                        agent: "codex"
                        session_id: "legacy-session"
                """,
            )

            workspace = load_workspace(config_path)

            self.assertEqual(workspace.slots[0].windows[0].session, "legacy-session")

    def test_load_workspace_raises_on_missing_file(self):
        """Test that load_workspace raises FileNotFoundError for missing config."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "nonexistent.yaml"

            with self.assertRaises(FileNotFoundError):
                load_workspace(config_path)

    def test_load_workspace_rejects_toml_config(self):
        """Workspace config is YAML-only for the first release."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch.toml"
            self._write(config_path, 'version = 1\nproject = "demo"\nroot = "."')

            with self.assertRaises(ValueError):
                load_workspace(config_path)

    def test_resolve_config_path_defaults_to_project_config_directory(self):
        """New workspaces should keep cc-branch files under .cc-branch/."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            self.assertEqual(resolve_config_path(root), root / ".cc-branch/config.yaml")

    def test_named_config_selection_uses_configs_directory_and_named_state(self):
        """Bare config names should map to isolated config/state files."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            config_path = resolve_config_selection(root, "review")

            self.assertEqual(config_path, root / ".cc-branch/configs/review.yaml")
            self.assertEqual(resolve_state_path(root, config_path), root / ".cc-branch/states/review.yaml")
            self.assertEqual(project_dir_for_config(config_path), root)

    def test_config_options_list_default_and_named_configs(self):
        """The UI needs a stable list of selectable configs for a project."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root / ".cc-branch/config.yaml", "version: 1\nproject: default\nroot: .")
            self._write(root / ".cc-branch/configs/review.yaml", "version: 1\nproject: review\nroot: .")
            self._write(root / ".cc-branch/state.yaml", "version: 1")
            self._write(root / ".cc-branch/agents.yaml", "agents: {}")

            options = config_options(root, selected_config_path=root / ".cc-branch/configs/review.yaml")

            paths = [option["path"] for option in options]
            self.assertEqual(paths, [str(root / ".cc-branch/config.yaml"), str(root / ".cc-branch/configs/review.yaml")])
            self.assertTrue(options[0]["is_default"])
            self.assertFalse(options[1]["is_default"])
            self.assertFalse(options[0]["selected"])
            self.assertTrue(options[1]["selected"])
            self.assertEqual(options[1]["state_path"], str(root / ".cc-branch/states/review.yaml"))

    def test_init_workspace_creates_default_config(self):
        """Test that init_workspace creates a valid default configuration."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, state_path = init_workspace(root, force=False, bootstrap_sessions=False)

            self.assertTrue(config_path.exists())
            self.assertTrue(state_path.exists())
            self.assertEqual(config_path, root / ".cc-branch/config.yaml")
            self.assertEqual(state_path, root / ".cc-branch/state.yaml")

            # Verify the config is valid
            workspace = load_workspace(config_path)
            self.assertEqual(workspace.version, 2)
            self.assertTrue(hasattr(workspace, "project"))
            self.assertNotIn("agents:", config_path.read_text(encoding="utf-8"))

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
            config_path = root / ".cc-branch/config.yaml"
            config_path.parent.mkdir()
            config_path.write_text("old content")

            new_config_path, _ = init_workspace(root, force=True, bootstrap_sessions=False)

            self.assertEqual(config_path, new_config_path)
            self.assertNotEqual(config_path.read_text(), "old content")

    def test_load_workspace_parses_display_config(self):
        """Test that load_workspace correctly parses display configuration."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
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
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "test"
                root: "."

                slots:
                  - name: "dev"
                    runtime: "terminal"
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
