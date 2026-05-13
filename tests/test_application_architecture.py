import tempfile
import textwrap
import unittest
from pathlib import Path

from cc_branch.application.diagnostics import get_doctor_payload
from cc_branch.application.state_store import StateStore
from cc_branch.application.workspace_actions import (
    execute_workspace_action,
    launch_workspace,
    open_workspace,
    restart_workspace,
    stop_workspace,
    sync_workspace,
)
from cc_branch.application.workspace_status import build_workspace_status, get_workspace_status
from cc_branch.backends import get_backend, set_backend
from cc_branch.config import load_workspace
from cc_branch.models import AppliedWindowResult, WindowState, WorkspaceState
from cc_branch.planner import plan_workspace
from cc_branch.runtime_capabilities import (
    is_external_process_runtime,
    is_managed_runtime,
    runtime_capabilities,
    supports_attach,
    supports_background_start,
    supports_dashboard,
    supports_stop,
    supports_windows,
)
from cc_branch.runtime_sync import build_runtime_sync_report
from cc_branch.state import load_state


class FakeBackend:
    def __init__(self, windows_by_session: dict[str, set[str]]) -> None:
        self.windows_by_session = windows_by_session

    def available(self) -> bool:
        return True

    def has_session(self, name: str) -> bool:
        return name in self.windows_by_session

    def has_window(self, session: str, window: str) -> bool:
        return window in self.windows_by_session.get(session, set())

    def list_windows(self, session: str) -> set[str]:
        return set(self.windows_by_session.get(session, set()))

    def send_keys(self, target: str, keys: str) -> None:
        raise AssertionError("not used")

    def create_session(self, name, cwd=None, window_name=None, command=None) -> None:
        raise AssertionError("not used")

    def create_window(self, session: str, name: str, cwd=None) -> None:
        raise AssertionError("not used")

    def kill_session(self, name: str) -> None:
        raise AssertionError("not used")

    def kill_window(self, target: str) -> None:
        raise AssertionError("not used")

    def attach_session(self, target: str) -> None:
        raise AssertionError("not used")

    def split_window(self, target: str, command: list[str]) -> None:
        raise AssertionError("not used")

    def select_layout(self, target: str, layout: str) -> None:
        raise AssertionError("not used")


class RuntimeBoundaryTests(unittest.TestCase):
    def test_cli_module_is_package_facade(self):
        import importlib

        import cc_branch.cli as cli

        self.assertTrue(hasattr(cli, "__path__"))
        for module_name in [
            "commands.doctor",
            "commands.init",
            "commands.open",
            "commands.serve",
            "commands.sessions",
            "commands.sync",
            "commands.workspace",
            "constants",
            "dispatch",
            "errors",
            "help",
            "output",
            "parser",
            "targets",
        ]:
            importlib.import_module(f"cc_branch.cli.{module_name}")

        self.assertTrue(callable(cli.main))
        self.assertTrue(callable(cli.build_parser))
        self.assertTrue(callable(cli.print_help))

        facade_path = Path(__file__).resolve().parents[1] / "cc_branch/cli/__init__.py"
        self.assertLess(len(facade_path.read_text(encoding="utf-8").splitlines()), 220)

    def test_models_module_is_package_facade(self):
        import importlib

        import cc_branch.models as models

        self.assertTrue(hasattr(models, "__path__"))
        for module_name in [
            "agents",
            "config",
            "diagnostics",
            "openers",
            "plan",
            "state",
        ]:
            importlib.import_module(f"cc_branch.models.{module_name}")

        self.assertTrue(callable(models.WorkspaceConfig.from_dict))
        self.assertTrue(callable(models.WorkspacePlan.from_dict))
        self.assertTrue(callable(models.WorkspaceState.from_dict))

    def test_doctor_module_is_package_facade(self):
        import importlib

        import cc_branch.doctor as doctor

        self.assertTrue(hasattr(doctor, "__path__"))
        for module_name in [
            "autofix",
            "checks",
            "messages",
            "rendering",
        ]:
            importlib.import_module(f"cc_branch.doctor.{module_name}")

        self.assertTrue(callable(doctor.collect_doctor_report))
        self.assertTrue(callable(doctor.render_doctor_report))
        self.assertTrue(callable(doctor.auto_fix_issues))

    def test_planner_module_is_package_facade(self):
        import importlib

        import cc_branch.planner as planner

        self.assertTrue(hasattr(planner, "__path__"))
        for module_name in [
            "commands",
            "naming",
            "paths",
            "slots",
            "workspace",
        ]:
            importlib.import_module(f"cc_branch.planner.{module_name}")

        self.assertTrue(callable(planner.plan_workspace))
        self.assertTrue(callable(planner.format_plan))
        self.assertTrue(callable(planner.session_key))

    def test_bootstrap_module_is_package_facade(self):
        import importlib

        import cc_branch.bootstrap as bootstrap

        self.assertTrue(hasattr(bootstrap, "__path__"))
        for module_name in [
            "environment",
            "files",
            "generation",
            "models",
            "sessions",
        ]:
            importlib.import_module(f"cc_branch.bootstrap.{module_name}")

        self.assertTrue(callable(bootstrap.check_environment))
        self.assertTrue(callable(bootstrap.initialize_workspace_files))
        self.assertTrue(callable(bootstrap.bootstrap_sessions))

    def test_agent_registry_module_is_package_facade(self):
        import importlib

        import cc_branch.agent_registry as agent_registry

        self.assertTrue(hasattr(agent_registry, "__path__"))
        for module_name in [
            "builtins",
            "io",
            "loader",
            "models",
            "paths",
        ]:
            importlib.import_module(f"cc_branch.agent_registry.{module_name}")

        self.assertTrue(callable(agent_registry.load_agent_registry))
        self.assertTrue(callable(agent_registry.get_builtin_agent_names))
        self.assertTrue(callable(agent_registry.AgentDefinition))

    def test_adapters_module_is_package_facade(self):
        import importlib

        import cc_branch.adapters as adapters

        self.assertTrue(hasattr(adapters, "__path__"))
        for module_name in [
            "base",
            "none",
            "resume",
            "selection",
        ]:
            importlib.import_module(f"cc_branch.adapters.{module_name}")

        self.assertTrue(callable(adapters.get_adapter))
        self.assertTrue(callable(adapters.AgentAdapter))

    def test_profiles_module_is_package_facade(self):
        import importlib

        import cc_branch.profiles as profiles

        self.assertTrue(hasattr(profiles, "__path__"))
        for module_name in [
            "definitions",
            "queries",
            "rendering",
        ]:
            importlib.import_module(f"cc_branch.profiles.{module_name}")

        self.assertTrue(callable(profiles.get_profile_config))
        self.assertTrue(callable(profiles.get_available_profiles))
        self.assertIn("development", profiles.PROFILES)

    def test_config_module_is_package_facade(self):
        import importlib

        import cc_branch.config as config

        self.assertTrue(hasattr(config, "__path__"))
        for module_name in [
            "initialization",
            "loading",
            "normalization",
            "paths",
        ]:
            importlib.import_module(f"cc_branch.config.{module_name}")

        self.assertTrue(callable(config.load_workspace))
        self.assertTrue(callable(config.load_workspace_from_text))
        self.assertTrue(callable(config.init_workspace))
        self.assertTrue(callable(config.resolve_state_path))

    def test_new_workspace_paths_live_under_project_metadata_directory(self):
        from cc_branch.config import resolve_config_path, resolve_state_path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            self.assertEqual(resolve_config_path(root), root / ".cc-branch/config.yaml")
            self.assertEqual(resolve_state_path(root), root / ".cc-branch/state.yaml")

    def test_repository_module_is_package_facade(self):
        import importlib

        import cc_branch.repository as repository

        self.assertTrue(hasattr(repository, "__path__"))
        for module_name in [
            "codec",
            "state_repository",
            "validation",
        ]:
            importlib.import_module(f"cc_branch.repository.{module_name}")

        self.assertTrue(callable(repository.StateRepository))

    def test_config_validation_module_is_package_facade(self):
        import importlib

        import cc_branch.application.config_validation as config_validation

        self.assertTrue(hasattr(config_validation, "__path__"))
        for module_name in [
            "collector",
            "constants",
            "issues",
            "sections",
            "validators",
        ]:
            importlib.import_module(f"cc_branch.application.config_validation.{module_name}")

        self.assertTrue(callable(config_validation.collect_config_issues))

    def test_config_workflows_module_is_package_facade(self):
        import importlib

        import cc_branch.application.config_workflows as config_workflows

        self.assertTrue(hasattr(config_workflows, "__path__"))
        for module_name in [
            "initialization",
            "options",
            "read",
            "save",
            "versioning",
        ]:
            importlib.import_module(f"cc_branch.application.config_workflows.{module_name}")

        self.assertTrue(callable(config_workflows.read_workspace_config))
        self.assertTrue(callable(config_workflows.save_workspace_config))
        self.assertTrue(callable(config_workflows.initialize_workspace))

    def test_slot_runtime_capabilities_are_explicit(self):
        tmux = runtime_capabilities("tmux")
        terminal = runtime_capabilities("terminal")

        self.assertTrue(tmux.managed)
        self.assertTrue(tmux.reusable)
        self.assertTrue(tmux.supports_windows)
        self.assertTrue(tmux.supports_background_start)
        self.assertTrue(tmux.supports_attach)
        self.assertTrue(tmux.supports_stop)
        self.assertTrue(tmux.supports_dashboard)

        self.assertFalse(terminal.managed)
        self.assertTrue(terminal.external_process)
        self.assertFalse(terminal.reusable)
        self.assertFalse(terminal.supports_windows)
        self.assertFalse(terminal.supports_background_start)
        self.assertFalse(terminal.supports_attach)
        self.assertFalse(terminal.supports_stop)
        self.assertFalse(terminal.supports_dashboard)

        self.assertTrue(is_managed_runtime("tmux"))
        self.assertTrue(is_external_process_runtime("terminal"))
        self.assertTrue(supports_windows("tmux"))
        self.assertTrue(supports_background_start("tmux"))
        self.assertTrue(supports_attach("tmux"))
        self.assertTrue(supports_stop("tmux"))
        self.assertTrue(supports_dashboard("tmux"))

    def test_runtime_execution_module_is_package_facade(self):
        import importlib

        import cc_branch.runtime.execution as execution

        self.assertTrue(hasattr(execution, "__path__"))
        for module_name in [
            "backend_ops",
            "dashboard",
            "lifecycle",
            "status",
            "targets",
            "windows",
        ]:
            importlib.import_module(f"cc_branch.runtime.execution.{module_name}")

        self.assertTrue(callable(execution.apply_workspace))
        self.assertTrue(callable(execution.ensure_slot))
        self.assertTrue(callable(execution.format_status))

    def test_runtime_sync_module_is_package_facade(self):
        import importlib

        import cc_branch.runtime.sync as sync

        self.assertTrue(hasattr(sync, "__path__"))
        for module_name in [
            "fingerprints",
            "inspection",
            "models",
            "report",
            "state",
            "targets",
        ]:
            importlib.import_module(f"cc_branch.runtime.sync.{module_name}")

        self.assertTrue(callable(sync.build_runtime_sync_report))
        self.assertTrue(callable(sync.record_applied_results))
        self.assertTrue(callable(sync.extra_window_targets))

    def test_shell_command_is_separate_from_slot_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "scratch"
                    runtime: "terminal"
                    command: "pwsh"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            slot = plan.slots[0]
            self.assertEqual(slot.runtime, "terminal")
            self.assertTrue(is_external_process_runtime(slot.runtime))
            self.assertEqual(slot.windows[0].launch_command, "pwsh")

    def test_workspace_actions_module_is_package_facade(self):
        import importlib

        import cc_branch.application.workspace_actions as workspace_actions

        self.assertTrue(hasattr(workspace_actions, "__path__"))
        for module_name in [
            "command_specs",
            "executor",
            "lifecycle",
            "open",
            "persistence",
            "sync",
            "targets",
        ]:
            importlib.import_module(f"cc_branch.application.workspace_actions.{module_name}")

        self.assertTrue(callable(workspace_actions.execute_workspace_action))
        self.assertTrue(callable(workspace_actions.open_workspace))

    def test_workspace_actions_expose_explicit_use_case_objects(self):
        from cc_branch.application.workspace_actions.command_specs import WorkspaceCommandSpecs
        from cc_branch.application.workspace_actions.executor import WorkspaceActionExecutor
        from cc_branch.application.workspace_actions.lifecycle import WorkspaceLifecycleActions
        from cc_branch.application.workspace_actions.open import WorkspaceOpenActions
        from cc_branch.application.workspace_actions.sync import WorkspaceSyncActions
        from cc_branch.application.workspace_actions.targets import WorkspaceTargetResolver

        for use_case in [
            WorkspaceActionExecutor,
            WorkspaceCommandSpecs,
            WorkspaceLifecycleActions,
            WorkspaceOpenActions,
            WorkspaceSyncActions,
            WorkspaceTargetResolver,
        ]:
            self.assertTrue(use_case.__doc__)

    def test_workspace_command_specs_carry_tab_split_group(self):
        from types import SimpleNamespace

        from cc_branch.application.workspace_actions.command_specs import WorkspaceCommandSpecs

        dev = SimpleNamespace(
            name="dev",
            cwd="/tmp/demo",
            windows=[
                SimpleNamespace(name="frontend", cwd="/tmp/demo", launch_command="npm run dev"),
                SimpleNamespace(name="backend", cwd="/tmp/demo", launch_command="python api.py"),
            ],
        )
        docs = SimpleNamespace(
            name="docs",
            cwd="/tmp/demo",
            windows=[
                SimpleNamespace(name="writer", cwd="/tmp/demo", launch_command="codex"),
            ],
        )

        specs = WorkspaceCommandSpecs().terminal_command_specs([dev, docs])

        self.assertEqual([spec.title for spec in specs], ["dev:frontend", "dev:backend", "docs:writer"])
        self.assertEqual([spec.split_group for spec in specs], ["dev", "dev", "docs"])

    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def test_runtime_sync_uses_backend_for_runtime_inspection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "planner"
                        command: "echo planner"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            previous_backend = get_backend()
            set_backend(FakeBackend({"demo-dev": {"planner", "extra"}}))
            try:
                report = build_runtime_sync_report(workspace, plan, state)
            finally:
                set_backend(previous_backend)

            slot = report.slots[0]
            self.assertEqual(slot.windows[0].runtime_status, "present")
            self.assertEqual(slot.windows[0].sync_status, "untracked")
            self.assertEqual([window.name for window in slot.extra_windows], ["extra"])

    def test_workspace_status_builder_returns_shared_status_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "planner"
                        command: "echo planner"
                """,
            )

            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)
            previous_backend = get_backend()
            set_backend(FakeBackend({"demo-dev": {"planner"}}))
            def fail_session_check(_session: str) -> bool:
                raise AssertionError("status should reuse sync inspection instead of checking sessions again")

            def fail_window_check(_session: str, _window: str) -> bool:
                raise AssertionError("status should reuse sync inspection instead of checking windows again")

            try:
                status = build_workspace_status(
                    workspace,
                    plan,
                    state,
                    config_path=root / ".cc-branch/config.yaml",
                    state_path=root / ".cc-branch/state.yaml",
                    session_exists=fail_session_check,
                    window_exists=fail_window_check,
                )
            finally:
                set_backend(previous_backend)

            self.assertEqual(status["status"], "ready")
            self.assertEqual(status["project"], "demo")
            self.assertEqual(status["config_path"], str(root / ".cc-branch/config.yaml"))
            self.assertEqual(status["slots"][0]["status"], "running")
            self.assertEqual(status["slots"][0]["windows"][0]["status"], "running")
            self.assertEqual(status["slots"][0]["windows"][0]["sync_status"], "untracked")

    def test_workspace_status_query_owns_setup_and_invalid_config_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_config = root / "missing" / ".cc-branch/config.yaml"
            missing_result = get_workspace_status(
                missing_config,
                root / "missing" / ".cc-branch/state.yaml",
            )

            self.assertTrue(missing_result.ok)
            self.assertEqual(missing_result.code, "workspace_missing")
            self.assertEqual(missing_result.payload["status"], "missing")
            self.assertEqual(missing_result.payload["slots"], [])

            invalid_config = root / ".cc-branch/config.yaml"
            invalid_config.parent.mkdir(parents=True)
            invalid_config.write_text("version: [\n", encoding="utf-8")
            invalid_result = get_workspace_status(invalid_config, root / ".cc-branch/state.yaml")

            self.assertFalse(invalid_result.ok)
            self.assertEqual(invalid_result.code, "invalid_config")
            self.assertEqual(invalid_result.payload["status"], "invalid_config")
            self.assertIn("error", invalid_result.payload)

    def test_doctor_payload_query_owns_setup_and_ready_report_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_config = root / "missing" / ".cc-branch/config.yaml"
            missing_result = get_doctor_payload(
                missing_config,
                root / "missing" / ".cc-branch/state.yaml",
            )

            self.assertTrue(missing_result.ok)
            self.assertEqual(missing_result.code, "workspace_missing")
            self.assertEqual(missing_result.payload["status"], "missing")
            self.assertIn("Project directory does not exist", missing_result.payload["report"])

            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "planner"
                        command: "echo planner"
                """,
            )
            ready_result = get_doctor_payload(root / ".cc-branch/config.yaml", root / ".cc-branch/state.yaml")

            self.assertTrue(ready_result.ok)
            self.assertEqual(ready_result.code, "doctor_ready")
            self.assertEqual(ready_result.payload["status"], "ready")
            self.assertIsInstance(ready_result.payload["report"], dict)
            self.assertIsInstance(ready_result.payload["text"], str)


class StateStoreBoundaryTests(unittest.TestCase):
    def test_state_store_update_loads_mutates_and_saves_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / ".cc-branch/state.yaml"
            store = StateStore(state_path)

            def add_window(state: WorkspaceState) -> WorkspaceState:
                state.windows["dev.planner"] = WindowState(
                    session_id="session-1",
                    slot="dev",
                    window="planner",
                )
                return state

            updated = store.update(add_window)
            loaded = store.load()

            self.assertEqual(updated.windows["dev.planner"].session_id, "session-1")
            self.assertEqual(loaded.windows["dev.planner"].session_id, "session-1")


class ArchitectureRuleTests(unittest.TestCase):
    def _webui_server_text(self, repo_root: Path) -> str:
        return "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((repo_root / "cc_branch" / "webui" / "server").glob("*.py"))
        )

    def _cli_text(self, repo_root: Path) -> str:
        return "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((repo_root / "cc_branch" / "cli").rglob("*.py"))
        )

    def test_tmux_subprocess_calls_are_isolated_to_backend_module(self):
        repo_root = Path(__file__).resolve().parents[1]
        offenders: list[str] = []
        for path in (repo_root / "cc_branch").rglob("*.py"):
            relative = path.relative_to(repo_root)
            if relative.as_posix() in {
                "cc_branch/backends.py",
                "cc_branch/runtime/backends.py",
            }:
                continue
            text = path.read_text(encoding="utf-8")
            if 'subprocess.run(["tmux"' in text:
                offenders.append(relative.as_posix())

        self.assertEqual(offenders, [])

    def test_presentation_layers_do_not_own_sync_planning_or_state_writes(self):
        repo_root = Path(__file__).resolve().parents[1]
        forbidden_tokens = (
            "build_runtime_sync_report",
            "reconcilable_targets",
            "save_state",
        )
        offenders: list[str] = []
        sources = {
            "cc_branch/cli": self._cli_text(repo_root),
            "cc_branch/webui/server": self._webui_server_text(repo_root),
        }
        for relative, text in sources.items():
            for token in forbidden_tokens:
                if token in text:
                    offenders.append(f"{relative}:{token}")

        self.assertEqual(offenders, [])

    def test_presentation_layers_do_not_call_runtime_restart_directly(self):
        repo_root = Path(__file__).resolve().parents[1]
        offenders: list[str] = []
        sources = {
            "cc_branch/cli": self._cli_text(repo_root),
            "cc_branch/webui/server": self._webui_server_text(repo_root),
        }
        for relative, text in sources.items():
            if "restart_workspace(" in text:
                offenders.append(relative)

        self.assertEqual(offenders, [])

    def test_cli_does_not_own_open_opener_side_effects(self):
        repo_root = Path(__file__).resolve().parents[1]
        text = self._cli_text(repo_root)
        forbidden_tokens = (
            "open_with(",
            "open_workspace_file(",
            "open_command_layout(",
            "opener_supports(",
        )
        offenders = [token for token in forbidden_tokens if token in text]

        self.assertEqual(offenders, [])

    def test_webui_open_routes_through_application_use_case(self):
        repo_root = Path(__file__).resolve().parents[1]
        text = self._webui_server_text(repo_root)

        self.assertIn("execute_workspace_action(", text)

    def test_webui_server_module_is_package_facade(self):
        import importlib

        import cc_branch.webui.server as server

        self.assertTrue(hasattr(server, "__path__"))
        for module_name in ["api", "auth", "handler", "static", "terminal"]:
            importlib.import_module(f"cc_branch.webui.server.{module_name}")

        self.assertTrue(callable(server.start_server))
        self.assertTrue(server.WebUIHandler.__name__.endswith("Handler"))

        handler_path = Path(__file__).resolve().parents[1] / "cc_branch/webui/server/handler.py"
        self.assertLess(len(handler_path.read_text(encoding="utf-8").splitlines()), 360)

    def test_webui_does_not_keep_local_opener_target_workflow(self):
        repo_root = Path(__file__).resolve().parents[1]
        text = self._webui_server_text(repo_root)

        self.assertNotIn("def _open_target_with_opener", text)

    def test_webui_does_not_own_config_or_metadata_workflows(self):
        repo_root = Path(__file__).resolve().parents[1]
        text = self._webui_server_text(repo_root)
        forbidden_tokens = (
            "content = config_path.read_text",
            "status = \"missing\"",
            "load_workspace_from_text",
            "def _write_text_atomic",
            "def _file_version_payload",
            "Config changed on disk since it was opened.",
            "current_content = config_path.read_text",
            "check_environment(",
            "initialize_workspace_files(",
            "get_available_profiles(",
            "get_profile_description(",
            "list_openers(",
            "load_agent_registry(",
        )
        offenders = [token for token in forbidden_tokens if token in text]

        self.assertEqual(offenders, [])

    def test_webui_status_and_doctor_route_through_application_queries(self):
        repo_root = Path(__file__).resolve().parents[1]
        text = self._webui_server_text(repo_root)

        self.assertIn("get_workspace_status(", text)
        self.assertIn("get_doctor_payload(", text)

        forbidden_tokens = (
            "def _setup_payload",
            "build_workspace_status(",
            "get_doctor_report(",
            "render_report(",
        )
        offenders = [token for token in forbidden_tokens if token in text]

        self.assertEqual(offenders, [])

    def test_cli_does_not_own_runtime_mutation_workflows(self):
        repo_root = Path(__file__).resolve().parents[1]
        text = self._cli_text(repo_root)
        forbidden_tokens = (
            "apply_workspace(",
            "ensure_slot(",
            "open_dashboard(",
            "attach_slot(",
            "record_applied_results(",
        )
        offenders = [token for token in forbidden_tokens if token in text]

        self.assertEqual(offenders, [])

    def test_cli_doctor_uses_application_diagnostics(self):
        repo_root = Path(__file__).resolve().parents[1]
        text = self._cli_text(repo_root)

        self.assertIn("get_doctor_report(", text)
        self.assertIn("render_report(", text)
        self.assertNotIn("build_doctor_report", text)

    def test_cli_init_uses_application_config_workflows(self):
        repo_root = Path(__file__).resolve().parents[1]
        text = self._cli_text(repo_root)
        forbidden_tokens = (
            "check_environment(",
            "initialize_workspace_files(",
            "init_workspace(",
        )
        offenders = [token for token in forbidden_tokens if token in text]

        self.assertEqual(offenders, [])

    def test_application_layer_does_not_import_presentation_frameworks(self):
        repo_root = Path(__file__).resolve().parents[1]
        forbidden_tokens = ("import argparse", "BaseHTTPRequestHandler", "from rich", "import rich")
        offenders: list[str] = []

        for path in (repo_root / "cc_branch" / "application").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for token in forbidden_tokens:
                if token in text:
                    offenders.append(f"{path.relative_to(repo_root)}:{token}")

        self.assertEqual(offenders, [])

    def test_webui_does_not_own_action_loading_or_target_resolution(self):
        repo_root = Path(__file__).resolve().parents[1]
        text = self._webui_server_text(repo_root)

        self.assertIn("execute_workspace_action(", text)
        forbidden_tokens = (
            "load_workspace(",
            "load_state(",
            "plan_workspace(",
            "def _resolve_open_intent",
            "def _resolve_attach_target",
            "def _normalize_action_target",
        )
        offenders = [token for token in forbidden_tokens if token in text]

        self.assertEqual(offenders, [])


class ConfigWorkflowTests(unittest.TestCase):
    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def test_save_workspace_config_rejects_stale_base_without_writing(self):
        from cc_branch.application.config_workflows import save_workspace_config

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            state_path = root / ".cc-branch/state.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "dev"
                    command: "zsh"
                """,
            )
            stale_hash = "sha256:not-current"

            result = save_workspace_config(
                config_path,
                state_path,
                config_path.read_text(encoding="utf-8").replace("demo", "changed"),
                base_content_hash=stale_hash,
            )

            self.assertFalse(result.ok)
            self.assertEqual(result.code, "config_conflict")
            self.assertEqual(config_path.read_text(encoding="utf-8").splitlines()[1], 'project: "demo"')
            self.assertIn("current_content", result.payload)
            self.assertIn("content_hash", result.payload)

    def test_save_workspace_config_validates_before_writing(self):
        from cc_branch.application.config_workflows import save_workspace_config

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            state_path = root / ".cc-branch/state.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "dev"
                    command: "zsh"
                """,
            )
            before = config_path.read_text(encoding="utf-8")

            result = save_workspace_config(
                config_path,
                state_path,
                "version: [not valid yaml",
            )

            self.assertFalse(result.ok)
            self.assertEqual(result.code, "invalid_config")
            self.assertEqual(config_path.read_text(encoding="utf-8"), before)

    def test_save_workspace_config_writes_valid_content_and_returns_version(self):
        from cc_branch.application.config_workflows import save_workspace_config

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            state_path = root / ".cc-branch/state.yaml"
            content = textwrap.dedent(
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "dev"
                    command: "zsh"
                """
            ).strip() + "\n"

            result = save_workspace_config(config_path, state_path, content)

            self.assertTrue(result.ok)
            self.assertEqual(result.code, "config_saved")
            self.assertEqual(config_path.read_text(encoding="utf-8"), content)
            self.assertEqual(result.payload["path"], str(config_path))
            self.assertIn("diagnostics", result.payload)
            self.assertIn("content_hash", result.payload)

    def test_save_workspace_config_accepts_canonical_public_fields_without_warnings(self):
        from cc_branch.application.config_workflows import (
            read_workspace_config,
            save_workspace_config,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            state_path = root / ".cc-branch/state.yaml"
            content = textwrap.dedent(
                """
                version: 2
                project: "demo"
                root: "."
                openWith: "auto-terminal"
                layoutBackend: "tmux"
                defaults:
                  shell: "system-default"

                tabs:
                  - name: "dev"
                    panes:
                      - name: "main"
                        command: "zsh"
                """
            ).strip() + "\n"

            result = save_workspace_config(config_path, state_path, content)
            read_result = read_workspace_config(config_path, state_path)

            self.assertTrue(result.ok)
            self.assertEqual(result.warnings, ())
            self.assertEqual(result.payload["issues"], [])
            self.assertTrue(read_result.ok)
            self.assertEqual(read_result.warnings, ())
            self.assertEqual(read_result.payload["issues"], [])

    def test_read_workspace_config_returns_missing_draft(self):
        from cc_branch.application.config_workflows import read_workspace_config

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = read_workspace_config(root / ".cc-branch/config.yaml", root / ".cc-branch/state.yaml")

            self.assertTrue(result.ok)
            self.assertEqual(result.code, "config_needs_init")
            self.assertEqual(result.payload["content"], "")
            self.assertFalse(result.payload["exists"])

    def test_read_workspace_config_returns_existing_content_with_version(self):
        from cc_branch.application.config_workflows import read_workspace_config

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "dev"
                    command: "zsh"
                """,
            )

            result = read_workspace_config(config_path, root / ".cc-branch/state.yaml")

            self.assertTrue(result.ok)
            self.assertEqual(result.code, "config_ready")
            self.assertTrue(result.payload["exists"])
            self.assertIn('project: "demo"', result.payload["content"])
            self.assertIn("content_hash", result.payload)

    def test_read_workspace_config_includes_validation_issues(self):
        from cc_branch.application.config_workflows import read_workspace_config

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "demo"
                unknown: true

                slots:
                  - name: "dev"
                    command: "zsh"
                """,
            )

            result = read_workspace_config(config_path, root / ".cc-branch/state.yaml")

            self.assertTrue(result.ok)
            self.assertEqual(result.payload["issues"][0]["issue_type"], "unknown_field")
            self.assertEqual(result.warnings, ("Unknown field 'unknown'",))

    def test_probe_project_reports_ready_workspace_summary(self):
        from cc_branch.application.config_workflows import probe_project

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "dev"
                    command: "zsh"
                """,
            )

            result = probe_project(root)

            self.assertTrue(result.ok)
            self.assertEqual(result.code, "project_probe")
            self.assertEqual(result.payload["status"], "ready")
            self.assertEqual(result.payload["project_name"], "demo")
            self.assertEqual(result.payload["slots"], 1)

    def test_initialize_workspace_returns_web_payload_shape(self):
        from unittest.mock import Mock, patch

        from cc_branch.application.config_workflows import initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = Mock(available_agents=["codex", "claude"])
            init_result = Mock(
                config_path=root / ".cc-branch/config.yaml",
                state_path=root / ".cc-branch/state.yaml",
                gitignore_created=True,
                gitignore_updated=False,
            )
            init_result.config_summary.slots = 2
            init_result.config_summary.windows = 3
            init_result.config_summary.agents = 2

            with (
                patch("cc_branch.application.config_workflows.check_environment", return_value=env) as check_environment,
                patch("cc_branch.application.config_workflows.initialize_workspace_files", return_value=init_result) as initialize_files,
            ):
                result = initialize_workspace(root, profile="development", bootstrap_sessions=True)

            self.assertTrue(result.ok)
            self.assertEqual(result.code, "workspace_initialized")
            self.assertEqual(result.payload["config_path"], str(root / ".cc-branch/config.yaml"))
            self.assertEqual(result.payload["summary"], {"slots": 2, "windows": 3, "agents": 2})
            self.assertEqual(result.payload["agents_detected"], ["codex", "claude"])
            check_environment.assert_called_once_with(root)
            initialize_files.assert_called_once_with(
                root,
                profile="development",
                available_agents=["codex", "claude"],
                bootstrap_sessions_requested=True,
            )

    def test_profile_options_return_serializable_payload(self):
        from unittest.mock import patch

        from cc_branch.application.config_workflows import profile_options

        with (
            patch("cc_branch.application.config_workflows.get_available_profiles", return_value=["development"]),
            patch("cc_branch.application.config_workflows.get_profile_description", return_value="Development profile"),
        ):
            result = profile_options()

        self.assertTrue(result.ok)
        self.assertEqual(result.payload, {"profiles": [{"id": "development", "description": "Development profile"}]})

    def test_opener_options_use_workspace_custom_openers_when_config_exists(self):
        from unittest.mock import patch

        from cc_branch.application.config_workflows import opener_options

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            self._write(
                config_path,
                """
                version: 1
                project: "demo"
                root: "."
                default_opener: "warp"

                openers:
                  warp:
                    label: "Warp"
                    kind: "terminal"
                    command: "warp"

                slots:
                  - name: "dev"
                    command: "zsh"
                """,
            )

            with patch("cc_branch.application.config_workflows.list_openers", return_value={"default": "warp", "openers": []}) as list_openers:
                result = opener_options(config_path)

            self.assertTrue(result.ok)
            self.assertEqual(result.payload["default"], "warp")
            self.assertEqual(list_openers.call_args.args[0], "warp")

    def test_agent_options_fall_back_to_registry_without_config(self):
        from unittest.mock import Mock, patch

        from cc_branch.application.config_workflows import agent_options

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent_spec = Mock()
            agent_spec.to_agent_spec.return_value.to_dict.return_value = {
                "command": "codex",
                "resume_mode": "flag",
            }
            with patch("cc_branch.application.config_workflows.load_agent_registry", return_value={"codex": agent_spec}):
                result = agent_options(root / ".cc-branch/config.yaml")

            self.assertTrue(result.ok)
            self.assertEqual(result.payload["agents"], [{"id": "codex", "command": "codex", "resume_mode": "flag"}])

    def test_collect_config_issues_warns_for_unknown_fields(self):
        from cc_branch.application.config_validation import collect_config_issues

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issues = collect_config_issues(
                textwrap.dedent(
                    """
                    version: 1
                    project: "demo"
                    unexpected_top: true

                    slots:
                      - name: "dev"
                        command: "zsh"
                        unexpected_slot: true
                    """
                ),
                root / ".cc-branch/config.yaml",
            )

            self.assertEqual([issue.issue_type for issue in issues], ["unknown_field", "unknown_field"])
            self.assertTrue(all(issue.severity == "warning" for issue in issues))
            self.assertEqual(issues[0].target, "config")
            self.assertEqual(issues[1].target, "slot:dev")

    def test_collect_config_issues_errors_for_invalid_enums(self):
        from cc_branch.application.config_validation import collect_config_issues

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issues = collect_config_issues(
                textwrap.dedent(
                    """
                    version: 1
                    project: "demo"

                    agents:
                      codex:
                        command: "codex"
                        resume_mode: "bad"

                    slots:
                      - name: "dev"
                        runtime: "docker"
                        command: "zsh"
                    """
                ),
                root / ".cc-branch/config.yaml",
            )

            errors = [issue for issue in issues if issue.severity == "error"]
            self.assertEqual([issue.issue_type for issue in errors], ["invalid_enum", "invalid_enum"])
            self.assertEqual(errors[0].target, "agent:codex")
            self.assertEqual(errors[1].target, "slot:dev")

    def test_collect_config_issues_uses_runtime_agent_adapter_enums(self):
        from cc_branch.application.config_validation import collect_config_issues

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            accepted = collect_config_issues(
                textwrap.dedent(
                    """
                    version: 2
                    project: "demo"

                    agents:
                      local:
                        command: "local-agent"
                        resume_mode: "internal"
                        resume_template: "/resume {session_id}"
                        label_mode: "internal"
                        rename_template: "/rename {label}"

                    tabs:
                      - name: "dev"
                        panes:
                          - name: "main"
                            agent: "local"
                    """
                ),
                root / ".cc-branch/config.yaml",
            )
            rejected = collect_config_issues(
                textwrap.dedent(
                    """
                    version: 2
                    project: "demo"

                    agents:
                      local:
                        command: "local-agent"
                        resume_mode: "command"
                        label_mode: "command"

                    tabs:
                      - name: "dev"
                        panes:
                          - name: "main"
                            agent: "local"
                    """
                ),
                root / ".cc-branch/config.yaml",
            )

            self.assertEqual(accepted, [])
            self.assertEqual(
                [(issue.target, issue.context["field"]) for issue in rejected],
                [("agent:local", "resume_mode"), ("agent:local", "label_mode")],
            )

    def test_save_workspace_config_rejects_structural_validation_errors(self):
        from cc_branch.application.config_workflows import save_workspace_config

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            state_path = root / ".cc-branch/state.yaml"

            result = save_workspace_config(
                config_path,
                state_path,
                textwrap.dedent(
                    """
                    version: 1
                    project: "demo"

                    slots:
                      - name: "dev"
                        runtime: "docker"
                        command: "zsh"
                    """
                ),
            )

            self.assertFalse(result.ok)
            self.assertEqual(result.code, "invalid_config")
            self.assertFalse(config_path.exists())
            self.assertEqual(result.payload["issues"][0]["issue_type"], "invalid_enum")

    def test_save_workspace_config_returns_validation_warnings_on_success(self):
        from cc_branch.application.config_workflows import save_workspace_config

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".cc-branch/config.yaml"
            state_path = root / ".cc-branch/state.yaml"

            result = save_workspace_config(
                config_path,
                state_path,
                textwrap.dedent(
                    """
                    version: 1
                    project: "demo"
                    unexpected_top: true

                    slots:
                      - name: "dev"
                        command: "zsh"
                    """
                ),
            )

            self.assertTrue(result.ok)
            self.assertEqual(result.warnings, ("Unknown field 'unexpected_top'",))
            self.assertEqual(result.payload["issues"][0]["severity"], "warning")

    def test_collect_config_issues_errors_for_non_string_scalars(self):
        from cc_branch.application.config_validation import collect_config_issues

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issues = collect_config_issues(
                textwrap.dedent(
                    """
                    version: 1
                    project: "demo"

                    agents:
                      codex:
                        command: ["codex"]

                    slots:
                      - name: 123
                        command: 456
                        windows:
                          - name: ["bad"]
                            agent: 789
                    """
                ),
                root / ".cc-branch/config.yaml",
            )

            errors = [issue for issue in issues if issue.issue_type == "invalid_type"]
            self.assertCountEqual(
                [(issue.target, issue.context["field"]) for issue in errors],
                [
                    ("agent:codex", "command"),
                    ("slot:slot[0]", "name"),
                    ("slot:slot[0]", "command"),
                    ("window:slot[0]:window[0]", "name"),
                    ("window:slot[0]:window[0]", "agent"),
                ],
            )

    def test_collect_config_issues_errors_for_duplicate_names_and_missing_launch_command(self):
        from cc_branch.application.config_validation import collect_config_issues

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issues = collect_config_issues(
                textwrap.dedent(
                    """
                    version: 1
                    project: "demo"

                    slots:
                      - name: "dev"
                        windows:
                          - name: "main"
                          - name: "main"
                            command: "zsh"
                      - name: "dev"
                        command: "bash"
                    """
                ),
                root / ".cc-branch/config.yaml",
            )

            errors = [issue for issue in issues if issue.severity == "error"]
            self.assertCountEqual(
                [(issue.issue_type, issue.target) for issue in errors],
                [
                    ("duplicate_slot", "slot:dev"),
                    ("duplicate_window", "window:dev:main"),
                    ("missing_launch_command", "window:dev:main"),
                ],
            )

    def test_collect_config_issues_accepts_v2_tabs_and_validates_panes(self):
        from cc_branch.application.config_validation import collect_config_issues

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issues = collect_config_issues(
                textwrap.dedent(
                    """
                    version: 2
                    project: "demo"

                    tabs:
                      - name: "dev"
                        panes:
                          - name: "ui"
                            agent: "codex"
                          - name: "tmux"
                            runtime: "tmux"
                            windows:
                              - name: "shell"
                                command: "zsh"
                    """
                ),
                root / ".cc-branch/config.yaml",
            )

            self.assertEqual(issues, [])

    def test_collect_config_issues_accepts_canonical_workspace_terms(self):
        from cc_branch.application.config_validation import collect_config_issues

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issues = collect_config_issues(
                textwrap.dedent(
                    """
                    version: 2
                    project: "demo"
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
                          - name: "server"
                            command: "pnpm dev"
                            shell: "zsh"
                    """
                ),
                root / ".cc-branch/config.yaml",
            )

            self.assertEqual(issues, [])

    def test_collect_config_issues_errors_for_invalid_env_keys(self):
        from cc_branch.application.config_validation import collect_config_issues

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issues = collect_config_issues(
                textwrap.dedent(
                    """
                    version: 1
                    project: "demo"

                    slots:
                      - name: "dev"
                        command: "zsh"
                        env:
                          BAD-KEY: "1"
                        windows:
                          - name: "main"
                            command: "zsh"
                            env:
                              ALSO.BAD: "2"
                    """
                ),
                root / ".cc-branch/config.yaml",
            )

            errors = [issue for issue in issues if issue.issue_type == "invalid_env_key"]
            self.assertCountEqual(
                [(issue.target, issue.context["key"]) for issue in errors],
                [("slot:dev", "BAD-KEY"), ("window:dev:main", "ALSO.BAD")],
            )

    def test_collect_config_issues_errors_for_invalid_container_shapes(self):
        from cc_branch.application.config_validation import collect_config_issues

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issues = collect_config_issues(
                textwrap.dedent(
                    """
                    version: 1
                    project: "demo"
                    root: "."
                    display: compact
                    agents: []
                    openers: []
                    slots:
                      - name: "dev"
                        windows: worker
                    """
                ),
                root / ".cc-branch/config.yaml",
            )

            shape_errors = {
                (issue.context["field"], issue.context["expected"])
                for issue in issues
                if issue.issue_type == "invalid_type"
            }

            self.assertIn(("display", "mapping"), shape_errors)
            self.assertIn(("agents", "mapping"), shape_errors)
            self.assertIn(("openers", "mapping"), shape_errors)
            self.assertIn(("windows", "list"), shape_errors)

            slot_shape_issues = collect_config_issues(
                textwrap.dedent(
                    """
                    version: 1
                    project: "demo"
                    root: "."
                    slots:
                      dev:
                        command: "zsh"
                    """
                ),
                root / ".cc-branch/config.yaml",
            )
            self.assertIn(
                ("slots", "list"),
                {
                    (issue.context["field"], issue.context["expected"])
                    for issue in slot_shape_issues
                    if issue.issue_type == "invalid_type"
                },
            )


class WorkspaceActionsTests(unittest.TestCase):
    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def _workspace_plan_state(self, root: Path):
        self._write(
            root / ".cc-branch/config.yaml",
            """
            version: 1
            project: "demo"
            root: "."

            slots:
              - name: "dev"
                runtime: "tmux"
                windows:
                  - name: "planner"
                    command: "echo planner"
            """,
        )
        workspace = load_workspace(root / ".cc-branch/config.yaml")
        state = load_state(root / ".cc-branch/state.yaml")
        plan = plan_workspace(workspace, state, bootstrap_missing=False)
        return workspace, plan, state

    def test_sync_workspace_dry_run_returns_reconcilable_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, plan, state = self._workspace_plan_state(root)
            previous_backend = get_backend()
            set_backend(FakeBackend({}))
            try:
                result = sync_workspace(
                    workspace,
                    plan,
                    state,
                    root / ".cc-branch/state.yaml",
                    apply_changes=False,
                )
            finally:
                set_backend(previous_backend)

            self.assertFalse(result.ok)
            self.assertEqual(result.code, "sync_pending")
            self.assertEqual(result.changed_targets, ("dev:planner",))
            self.assertEqual(result.payload["extra_targets"], ())

    def test_sync_workspace_applies_restarts_and_persists_state(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, plan, state = self._workspace_plan_state(root)
            previous_backend = get_backend()
            set_backend(FakeBackend({}))
            result_payload = [
                AppliedWindowResult(
                    slot="dev",
                    window="planner",
                    key="dev.planner",
                    runtime="tmux",
                    tmux_session="demo-dev",
                    action="recreated",
                )
            ]
            try:
                with patch(
                    "cc_branch.application.workspace_actions._restart_runtime_workspace",
                    return_value=result_payload,
                ) as restart_workspace:
                    result = sync_workspace(
                        workspace,
                        plan,
                        state,
                        root / ".cc-branch/state.yaml",
                        apply_changes=True,
                    )
            finally:
                set_backend(previous_backend)

            self.assertTrue(result.ok)
            self.assertEqual(result.code, "sync_applied")
            self.assertEqual(result.changed_targets, ("dev:planner",))
            restart_workspace.assert_called_once()
            updated = load_state(root / ".cc-branch/state.yaml")
            self.assertIn("dev.planner", updated.windows)
            self.assertEqual(updated.windows["dev.planner"].managed_runtime, "tmux")

    def test_sync_workspace_updates_latest_state_without_dropping_unrelated_entries(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, plan, stale_state = self._workspace_plan_state(root)
            state_path = root / ".cc-branch/state.yaml"
            StateStore(state_path).save(
                WorkspaceState(
                    windows={
                        "other.window": WindowState(
                            session_id="keep-me",
                            slot="other",
                            window="window",
                        )
                    }
                )
            )
            previous_backend = get_backend()
            set_backend(FakeBackend({}))
            result_payload = [
                AppliedWindowResult(
                    slot="dev",
                    window="planner",
                    key="dev.planner",
                    runtime="tmux",
                    tmux_session="demo-dev",
                    action="recreated",
                )
            ]
            try:
                with patch(
                    "cc_branch.application.workspace_actions._restart_runtime_workspace",
                    return_value=result_payload,
                ):
                    result = sync_workspace(
                        workspace,
                        plan,
                        stale_state,
                        state_path,
                        apply_changes=True,
                    )
            finally:
                set_backend(previous_backend)

            self.assertTrue(result.ok)
            updated = load_state(state_path)
            self.assertEqual(updated.windows["other.window"].session_id, "keep-me")
            self.assertIn("dev.planner", updated.windows)

    def test_stop_workspace_calls_runtime_for_tmux_target(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, plan, state = self._workspace_plan_state(root)

            with patch("cc_branch.application.workspace_actions._stop_runtime_workspace") as runtime_stop:
                result = stop_workspace(workspace, plan, state, root / ".cc-branch/state.yaml", target="dev")

            self.assertTrue(result.ok)
            self.assertEqual(result.code, "stop_applied")
            self.assertEqual(result.message, "Stopped dev")
            runtime_stop.assert_called_once_with(workspace, plan, "dev")

    def test_stop_workspace_rejects_unknown_target_before_runtime(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, plan, state = self._workspace_plan_state(root)

            with patch("cc_branch.application.workspace_actions._stop_runtime_workspace") as runtime_stop:
                result = stop_workspace(workspace, plan, state, root / ".cc-branch/state.yaml", target="missing")

            self.assertFalse(result.ok)
            self.assertEqual(result.code, "target_not_found")
            self.assertEqual(result.exit_code, 1)
            runtime_stop.assert_not_called()

    def test_stop_workspace_rejects_terminal_runtime_target_before_runtime(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "scratch"
                    runtime: "terminal"
                    command: "zsh"
                """,
            )
            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            with patch("cc_branch.application.workspace_actions._stop_runtime_workspace") as runtime_stop:
                result = stop_workspace(workspace, plan, state, root / ".cc-branch/state.yaml", target="scratch")

            self.assertFalse(result.ok)
            self.assertEqual(result.code, "terminal_runtime_external")
            self.assertIn("Terminal runtime is external", result.message)
            runtime_stop.assert_not_called()

    def test_restart_workspace_target_restarts_and_persists_state(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, plan, state = self._workspace_plan_state(root)
            result_payload = [
                AppliedWindowResult(
                    slot="dev",
                    window="planner",
                    key="dev.planner",
                    runtime="tmux",
                    tmux_session="demo-dev",
                    action="recreated",
                )
            ]

            with patch(
                "cc_branch.application.workspace_actions._restart_runtime_workspace",
                return_value=result_payload,
            ) as runtime_restart:
                result = restart_workspace(
                    workspace,
                    plan,
                    state,
                    root / ".cc-branch/state.yaml",
                    target="dev",
                    detach=True,
                )

            self.assertTrue(result.ok)
            self.assertEqual(result.code, "restart_applied")
            self.assertEqual(result.message, "Restarted dev")
            runtime_restart.assert_called_once_with(workspace, plan, "dev", detach=True)
            updated = load_state(root / ".cc-branch/state.yaml")
            self.assertIn("dev.planner", updated.windows)
            self.assertEqual(updated.windows["dev.planner"].managed_runtime, "tmux")

    def test_restart_workspace_rejects_background_terminal_only_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "scratch"
                    runtime: "terminal"
                    command: "zsh"
                """,
            )
            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            result = restart_workspace(workspace, plan, state, root / ".cc-branch/state.yaml")

            self.assertFalse(result.ok)
            self.assertEqual(result.code, "no_tmux_runtime")
            self.assertEqual(result.exit_code, 1)

    def test_restart_workspace_attaches_first_tmux_slot_when_not_detached(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, plan, state = self._workspace_plan_state(root)

            with (
                patch("cc_branch.application.workspace_actions._stop_runtime_workspace"),
                patch("cc_branch.application.workspace_actions.ensure_slot", return_value=[]),
                patch("cc_branch.application.workspace_actions.attach_slot") as attach_slot,
            ):
                result = restart_workspace(
                    workspace,
                    plan,
                    state,
                    root / ".cc-branch/state.yaml",
                    detach=False,
                )

            self.assertTrue(result.ok)
            attach_slot.assert_called_once_with(plan, "dev")

    def test_launch_workspace_target_starts_slot_and_persists_state(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, plan, state = self._workspace_plan_state(root)
            result_payload = [
                AppliedWindowResult(
                    slot="dev",
                    window="planner",
                    key="dev.planner",
                    runtime="tmux",
                    tmux_session="demo-dev",
                    action="created",
                )
            ]

            with patch(
                "cc_branch.application.workspace_actions.ensure_slot",
                return_value=result_payload,
            ) as ensure_slot:
                result = launch_workspace(workspace, plan, state, root / ".cc-branch/state.yaml", target="dev")

            self.assertTrue(result.ok)
            self.assertEqual(result.code, "launch_applied")
            self.assertEqual(result.message, "Launched dev")
            self.assertEqual(ensure_slot.call_args.args[0].name, "dev")
            updated = load_state(root / ".cc-branch/state.yaml")
            self.assertIn("dev.planner", updated.windows)

    def test_launch_workspace_rejects_background_terminal_only_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "scratch"
                    runtime: "terminal"
                    command: "zsh"
                """,
            )
            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            result = launch_workspace(workspace, plan, state, root / ".cc-branch/state.yaml")

            self.assertFalse(result.ok)
            self.assertEqual(result.code, "no_tmux_runtime")
            self.assertEqual(result.exit_code, 1)

    def test_execute_workspace_action_launches_terminal_only_workspace_in_selected_opener(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "scratch"
                    runtime: "terminal"
                    command: "zsh"
                """,
            )

            with (
                patch("cc_branch.application.workspace_actions.opener_supports", side_effect=lambda _opener, cap, _custom=None: cap == "run_command"),
                patch("cc_branch.application.workspace_actions.opener_label", return_value="Warp"),
                patch("cc_branch.application.workspace_actions.open_command_layout") as open_command_layout,
            ):
                result = execute_workspace_action(
                    root / ".cc-branch/config.yaml",
                    root / ".cc-branch/state.yaml",
                    action="launch",
                    opener="warp",
                    cli="cc-branch",
                )

            self.assertTrue(result.ok)
            self.assertEqual(result.code, "launch_applied")
            self.assertEqual(result.message, "Launched terminal slots in Warp")
            self.assertEqual(open_command_layout.call_args.args[0], "warp")
            specs = open_command_layout.call_args.args[1]
            self.assertEqual([(spec.title, spec.command) for spec in specs], [
                ("scratch:main", "zsh"),
            ])

    def test_editor_open_target_opens_workspace_file_with_tmux_state(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, plan, state = self._workspace_plan_state(root)
            result_payload = [
                AppliedWindowResult(
                    slot="dev",
                    window="planner",
                    key="dev.planner",
                    runtime="tmux",
                    tmux_session="demo-dev",
                    action="created",
                )
            ]

            with (
                patch("cc_branch.application.workspace_actions.opener_supports", side_effect=lambda _opener, cap, _custom=None: cap in {"open_project", "workspace_file"}),
                patch("cc_branch.application.workspace_actions.opener_label", return_value="VS Code"),
                patch("cc_branch.application.workspace_actions.ensure_slot", return_value=result_payload) as ensure_slot,
                patch("cc_branch.application.workspace_actions.open_workspace_file") as open_workspace_file,
                patch("cc_branch.application.workspace_actions.open_with") as open_with,
            ):
                result = open_workspace(
                    workspace,
                    plan,
                    state,
                    root / ".cc-branch/state.yaml",
                    cwd=root,
                    cli="cc-branch",
                    opener="vscode",
                    target="dev:planner",
                )

            self.assertTrue(result.ok)
            self.assertEqual(result.message, "Opened dev:planner in VS Code")
            ensure_slot.assert_called_once()
            open_with.assert_not_called()
            self.assertEqual(open_workspace_file.call_args.args[0], "vscode")
            specs = open_workspace_file.call_args.kwargs["commands"]
            self.assertEqual([(spec.title, spec.command) for spec in specs], [
                ("dev:planner", "cc-branch attach dev:planner"),
            ])
            updated = load_state(root / ".cc-branch/state.yaml")
            self.assertIn("dev.planner", updated.windows)

    def test_open_terminal_target_uses_command_layout_without_attach_terminal(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "scratch"
                    runtime: "terminal"
                    windows:
                      - name: "shell"
                        command: "zsh"
                """,
            )
            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            with (
                patch("cc_branch.application.workspace_actions.opener_supports", return_value=False),
                patch("cc_branch.application.workspace_actions.opener_label", return_value="Warp"),
                patch("cc_branch.application.workspace_actions.open_command_layout") as open_command_layout,
                patch("cc_branch.application.workspace_actions.open_with") as open_with,
            ):
                result = open_workspace(
                    workspace,
                    plan,
                    state,
                    root / ".cc-branch/state.yaml",
                    cwd=root,
                    cli="cc-branch",
                    opener="warp",
                    target="scratch:shell",
                )

            self.assertTrue(result.ok)
            self.assertEqual(result.message, "Opened scratch:shell in Warp")
            specs = open_command_layout.call_args.args[1]
            self.assertEqual([(spec.title, spec.command) for spec in specs], [
                ("scratch:shell", "zsh"),
            ])
            open_with.assert_not_called()

    def test_open_workspace_layout_opener_expands_tmux_windows(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "dev"
                    runtime: "tmux"
                    windows:
                      - name: "planner"
                        command: "echo planner"
                  - name: "scratch"
                    runtime: "terminal"
                    command: "zsh"
                """,
            )
            workspace = load_workspace(root / ".cc-branch/config.yaml")
            state = load_state(root / ".cc-branch/state.yaml")
            plan = plan_workspace(workspace, state, bootstrap_missing=False)

            with (
                patch("cc_branch.application.workspace_actions.opener_supports", side_effect=lambda _opener, cap, _custom=None: cap == "layout"),
                patch("cc_branch.application.workspace_actions.opener_label", return_value="Warp"),
                patch("cc_branch.application.workspace_actions.ensure_slot", return_value=[]),
                patch("cc_branch.application.workspace_actions.open_command_layout") as open_command_layout,
            ):
                result = open_workspace(
                    workspace,
                    plan,
                    state,
                    root / ".cc-branch/state.yaml",
                    cwd=root,
                    cli="cc-branch",
                    opener="warp",
                )

            self.assertTrue(result.ok)
            specs = open_command_layout.call_args.args[1]
            self.assertEqual([(spec.title, spec.command) for spec in specs], [
                ("dev:planner", "cc-branch attach dev:planner"),
                ("scratch:main", "zsh"),
            ])

    def test_execute_workspace_action_normalizes_legacy_session_targets(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, plan, state = self._workspace_plan_state(root)
            result_payload = [
                AppliedWindowResult(
                    slot="dev",
                    window="planner",
                    key="dev.planner",
                    runtime="tmux",
                    tmux_session="demo-dev",
                    action="created",
                )
            ]

            with patch(
                "cc_branch.application.workspace_actions.ensure_slot",
                return_value=result_payload,
            ) as ensure_slot:
                result = execute_workspace_action(
                    root / ".cc-branch/config.yaml",
                    root / ".cc-branch/state.yaml",
                    action="launch",
                    target="demo-dev",
                    opener="auto-terminal",
                    cli="cc-branch",
                )

            self.assertTrue(result.ok)
            self.assertEqual(result.message, "Launched dev")
            self.assertEqual(ensure_slot.call_args.args[0].name, "dev")

    def test_execute_workspace_action_opens_terminal_runtime_launch_targets(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root / ".cc-branch/config.yaml",
                """
                version: 1
                project: "demo"
                root: "."

                slots:
                  - name: "scratch"
                    runtime: "terminal"
                    command: "zsh"
                """,
            )

            with (
                patch("cc_branch.application.workspace_actions.opener_supports", return_value=False),
                patch("cc_branch.application.workspace_actions.opener_label", return_value="Warp"),
                patch("cc_branch.application.workspace_actions.open_command_layout") as open_command_layout,
            ):
                result = execute_workspace_action(
                    root / ".cc-branch/config.yaml",
                    root / ".cc-branch/state.yaml",
                    action="launch",
                    target="scratch",
                    opener="warp",
                    cli="cc-branch",
                )

            self.assertTrue(result.ok)
            self.assertEqual(result.message, "Opened scratch in Warp")
            specs = open_command_layout.call_args.args[1]
            self.assertEqual([(spec.title, spec.command) for spec in specs], [
                ("scratch:main", "zsh"),
            ])
