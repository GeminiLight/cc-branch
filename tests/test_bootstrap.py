"""Tests for first-run bootstrap functionality."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cc_branch.agent_registry import get_builtin_agent_names
from cc_branch.bootstrap import (
    AgentStatus,
    EnvironmentReport,
    bootstrap_sessions,
    check_environment,
    generate_starter_config,
    summarize_config,
)
from cc_branch.config import init_workspace
from cc_branch.models import WorkspaceConfig, WorkspaceState
from cc_branch.profiles import (
    PROFILES,
    get_available_profiles,
    get_profile_description,
)


class TestEnvironmentCheck(unittest.TestCase):
    """Test environment checking functionality."""

    def test_check_environment_all_available(self):
        """Test environment check when all components are available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            with patch("cc_branch.bootstrap.which") as mock_which:
                # Mock all tools as available
                mock_which.side_effect = lambda cmd: f"/usr/bin/{cmd}"

                report = check_environment(target_dir)

                self.assertTrue(report.tmux_available)
                self.assertIsNotNone(report.tmux_path)
                self.assertEqual(len(report.agents), len(get_builtin_agent_names()))
                self.assertFalse(report.config_exists)
                self.assertFalse(report.state_exists)
                self.assertTrue(report.has_write_permission)
                self.assertTrue(report.can_proceed)
                self.assertFalse(report.has_blockers)

    def test_check_environment_tmux_missing(self):
        """Test environment check when tmux is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            with patch("cc_branch.bootstrap.which") as mock_which:
                # Mock tmux as missing, others available
                def which_mock(cmd):
                    if cmd == "tmux":
                        return None
                    return f"/usr/bin/{cmd}"

                mock_which.side_effect = which_mock

                report = check_environment(target_dir)

                self.assertFalse(report.tmux_available)
                self.assertIsNone(report.tmux_path)
                self.assertTrue(report.has_blockers)

    def test_check_environment_no_agents(self):
        """Test environment check when no agent CLIs are available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            with patch("cc_branch.bootstrap.which") as mock_which:
                # Mock tmux available, all agents missing
                def which_mock(cmd):
                    if cmd == "tmux":
                        return "/usr/bin/tmux"
                    return None

                mock_which.side_effect = which_mock

                report = check_environment(target_dir)

                self.assertTrue(report.tmux_available)
                self.assertEqual(len(report.available_agents), 0)
                all_missing = all(a.status == "missing" for a in report.agents)
                self.assertTrue(all_missing)

    def test_check_environment_partial_agents(self):
        """Test environment check when some agents are available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            with patch("cc_branch.bootstrap.which") as mock_which:
                # Mock tmux and claude available, others missing
                def which_mock(cmd):
                    if cmd in ["tmux", "claude"]:
                        return f"/usr/bin/{cmd}"
                    return None

                mock_which.side_effect = which_mock

                report = check_environment(target_dir)

                self.assertTrue(report.tmux_available)
                self.assertIn("claude", report.available_agents)
                self.assertEqual(len(report.available_agents), 1)

    def test_check_environment_config_exists(self):
        """Test environment check when config already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            config_path = target_dir / ".cc-branch.yaml"
            config_path.write_text("version: 1\n")

            with patch("cc_branch.bootstrap.which") as mock_which:
                mock_which.return_value = "/usr/bin/tmux"

                report = check_environment(target_dir)

                self.assertTrue(report.config_exists)
                self.assertFalse(report.state_exists)

    def test_check_environment_no_write_permission(self):
        """Test environment check when directory is not writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            with patch("cc_branch.bootstrap.which") as mock_which:
                mock_which.return_value = "/usr/bin/tmux"

                with patch("os.access") as mock_access:
                    mock_access.return_value = False

                    report = check_environment(target_dir)

                    self.assertFalse(report.has_write_permission)
                    self.assertFalse(report.can_proceed)
                    self.assertTrue(report.has_blockers)


class TestProfileTemplates(unittest.TestCase):
    """Test profile template functionality."""

    def test_get_available_profiles(self):
        """Test getting list of available profiles."""
        profiles = get_available_profiles()
        self.assertIsInstance(profiles, list)
        self.assertIn("solo-dev", profiles)
        self.assertIn("ai-pair", profiles)
        self.assertIn("minimal", profiles)

    def test_get_profile_description(self):
        """Test getting profile description."""
        desc = get_profile_description("solo-dev")
        self.assertIsInstance(desc, str)
        self.assertGreater(len(desc), 0)

    def test_get_profile_description_unknown(self):
        """Test getting description for unknown profile raises error."""
        with self.assertRaises(ValueError):
            get_profile_description("nonexistent")

    def test_profile_structure(self):
        """Test that all profiles have required structure."""
        for _name, profile in PROFILES.items():
            self.assertIn("description", profile)
            self.assertIn("slots", profile)
            self.assertIsInstance(profile["slots"], list)
            self.assertGreater(len(profile["slots"]), 0)


class TestConfigGeneration(unittest.TestCase):
    """Test config generation functionality."""

    def test_generate_config_with_all_agents(self):
        """Test config generation when all agents are available."""
        config = generate_starter_config(
            "test-project",
            ["codex", "claude", "gemini"],
            "solo-dev"
        )

        self.assertIn("version: 1", config)
        self.assertIn('project: "test-project"', config)
        self.assertNotIn("agents:", config)
        self.assertIn('agent: "codex"', config)
        self.assertIn('agent: "claude"', config)
        self.assertIn("planner", config)
        self.assertIn("builder", config)
        self.assertIn("review", config)

    def test_summarize_config_counts_referenced_agents_without_agent_definitions(self):
        """Init summaries should count used agents, not only explicit overrides."""
        config = generate_starter_config(
            "test-project",
            ["codex", "claude", "gemini"],
            "solo-dev"
        )

        summary = summarize_config(config)

        self.assertEqual(summary.agents, 2)

    def test_generate_config_with_one_agent(self):
        """Test config generation when only one agent is available."""
        config = generate_starter_config(
            "test-project",
            ["claude"],
            "solo-dev"
        )

        self.assertNotIn("agents:", config)
        self.assertIn('agent: "claude"', config)
        self.assertIn("planner", config)  # Should still have windows

    def test_generate_config_with_no_agents(self):
        """Test config generation when no agents are available."""
        config = generate_starter_config(
            "test-project",
            [],
            "solo-dev"
        )

        self.assertIn("version: 1", config)
        self.assertNotIn("agents:", config)
        self.assertIn("shell", config)  # Should have shell fallback

    def test_generate_config_unknown_profile(self):
        """Test config generation with unknown profile raises error."""
        with self.assertRaises(ValueError):
            generate_starter_config("test-project", ["claude"], "nonexistent")

    def test_generate_config_minimal_profile(self):
        """Test config generation with minimal profile."""
        config = generate_starter_config(
            "test-project",
            ["claude"],
            "minimal"
        )

        self.assertNotIn("agents:", config)
        self.assertIn('agent: "claude"', config)
        self.assertIn("main", config)
        self.assertIn("agent", config)

    def test_generate_config_ai_pair_profile(self):
        """Test config generation with ai-pair profile."""
        config = generate_starter_config(
            "test-project",
            ["codex", "claude"],
            "ai-pair"
        )

        self.assertIn("coder", config)
        self.assertIn("reviewer", config)
        self.assertIn("implement", config)
        self.assertIn("review", config)

    def test_generate_config_uses_platform_default_shell(self):
        """Generated shell slots should use the platform-aware default shell."""
        with patch("cc_branch.profiles.default_shell_command", return_value="pwsh"):
            config = generate_starter_config("test-project", [], "solo-dev")

        self.assertIn('command: "pwsh"', config)


class TestSessionBootstrap(unittest.TestCase):
    """Test session bootstrapping functionality."""

    def test_bootstrap_sessions_generates_uuids(self):
        """Test that bootstrap generates valid UUIDs."""
        workspace = WorkspaceConfig.from_dict({
            "version": 1,
            "project": "test",
            "root": ".",
            "agents": {
                "claude": {
                    "command": "claude",
                    "create_mode": "generated_uuid",
                    "resume_mode": "flag",
                }
            },
            "slots": [
                {
                    "name": "dev",
                    "windows": [
                        {"name": "main", "agent": "claude"}
                    ]
                }
            ]
        })
        state = WorkspaceState.from_dict({"version": 1, "windows": {}})

        updated_state = bootstrap_sessions(workspace, state)

        self.assertTrue(hasattr(updated_state, "windows"))
        # Should have generated session IDs
        self.assertGreater(len(updated_state.windows), 0)

    def test_bootstrap_sessions_preserves_existing(self):
        """Test that bootstrap preserves existing session IDs."""
        workspace = WorkspaceConfig.from_dict({
            "version": 1,
            "project": "test",
            "root": ".",
            "agents": {
                "claude": {
                    "command": "claude",
                    "create_mode": "generated_uuid",
                    "resume_mode": "flag",
                }
            },
            "slots": [
                {
                    "name": "dev",
                    "windows": [
                        {"name": "main", "agent": "claude"}
                    ]
                }
            ]
        })
        existing_id = "existing-uuid-123"
        state = WorkspaceState.from_dict({
            "version": 1,
            "windows": {
                "dev.main": {
                    "session_id": existing_id,
                    "label": "test/dev/main",
                }
            }
        })

        updated_state = bootstrap_sessions(workspace, state)

        # Should preserve existing session ID
        self.assertEqual(
            updated_state.windows["dev.main"].session_id,
            existing_id
        )

    def test_bootstrap_sessions_empty_workspace(self):
        """Test bootstrap with workspace that has no agents."""
        workspace = WorkspaceConfig.from_dict({
            "version": 1,
            "project": "test",
            "root": ".",
            "agents": {},
            "slots": []
        })
        state = WorkspaceState.from_dict({"version": 1, "windows": {}})

        updated_state = bootstrap_sessions(workspace, state)

        # Should not crash, just return state
        self.assertTrue(hasattr(updated_state, "version"))


class TestInitWorkspace(unittest.TestCase):
    """Tests for config initialization helpers."""

    def test_init_workspace_uses_platform_default_shell(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            with patch("cc_branch.config.default_shell_command", return_value="pwsh"):
                config_path, _ = init_workspace(target_dir, force=False, bootstrap_sessions=False)

            content = config_path.read_text(encoding="utf-8")
            self.assertIn('command: "pwsh"', content)


class TestAgentStatus(unittest.TestCase):
    """Test AgentStatus dataclass."""

    def test_agent_status_creation(self):
        """Test creating AgentStatus instance."""
        status = AgentStatus(
            name="claude",
            command="claude",
            status="ok",
            path="/usr/bin/claude",
            install_hint="Install Claude"
        )

        self.assertEqual(status.name, "claude")
        self.assertEqual(status.status, "ok")
        self.assertIsNotNone(status.path)


class TestEnvironmentReport(unittest.TestCase):
    """Test EnvironmentReport dataclass."""

    def test_available_agents_property(self):
        """Test available_agents property filters correctly."""
        agents = [
            AgentStatus("claude", "claude", "ok", "/usr/bin/claude", "hint"),
            AgentStatus("codex", "codex", "missing", None, "hint"),
            AgentStatus("gemini", "gemini", "ok", "/usr/bin/gemini", "hint"),
        ]

        report = EnvironmentReport(
            tmux_available=True,
            tmux_path="/usr/bin/tmux",
            agents=agents,
            config_exists=False,
            state_exists=False,
            has_write_permission=True,
        )

        self.assertEqual(len(report.available_agents), 2)
        self.assertIn("claude", report.available_agents)
        self.assertIn("gemini", report.available_agents)
        self.assertNotIn("codex", report.available_agents)

    def test_can_proceed_property(self):
        """Test can_proceed property."""
        report = EnvironmentReport(
            tmux_available=True,
            tmux_path="/usr/bin/tmux",
            agents=[],
            config_exists=False,
            state_exists=False,
            has_write_permission=True,
        )
        self.assertTrue(report.can_proceed)

        report_no_write = EnvironmentReport(
            tmux_available=True,
            tmux_path="/usr/bin/tmux",
            agents=[],
            config_exists=False,
            state_exists=False,
            has_write_permission=False,
        )
        self.assertFalse(report_no_write.can_proceed)

    def test_has_blockers_property(self):
        """Test has_blockers property."""
        report_ok = EnvironmentReport(
            tmux_available=True,
            tmux_path="/usr/bin/tmux",
            agents=[],
            config_exists=False,
            state_exists=False,
            has_write_permission=True,
        )
        self.assertFalse(report_ok.has_blockers)

        report_no_tmux = EnvironmentReport(
            tmux_available=False,
            tmux_path=None,
            agents=[],
            config_exists=False,
            state_exists=False,
            has_write_permission=True,
        )
        self.assertTrue(report_no_tmux.has_blockers)

        report_no_write = EnvironmentReport(
            tmux_available=True,
            tmux_path="/usr/bin/tmux",
            agents=[],
            config_exists=False,
            state_exists=False,
            has_write_permission=False,
        )
        self.assertTrue(report_no_write.has_blockers)


if __name__ == "__main__":
    unittest.main()
