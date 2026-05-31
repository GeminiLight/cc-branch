from __future__ import annotations

import tempfile
import time
import unittest
import importlib.util
from unittest import mock
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "smoke-test-desktop-app.py"
SPEC = importlib.util.spec_from_file_location("smoke_test_desktop_app", SCRIPT_PATH)
assert SPEC and SPEC.loader
smoke_test_desktop_app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke_test_desktop_app)
app_executable_from_bundle = smoke_test_desktop_app.app_executable_from_bundle
parse_backend_port = smoke_test_desktop_app.parse_backend_port
parse_backend_port_arg = smoke_test_desktop_app.parse_backend_port_arg
wait_for_backend_port = smoke_test_desktop_app.wait_for_backend_port
start_stdout_reader = smoke_test_desktop_app.start_stdout_reader
isolated_desktop_env = smoke_test_desktop_app.isolated_desktop_env
verify_desktop_app = smoke_test_desktop_app.verify_desktop_app
sidecar_executable_from_app_executable = smoke_test_desktop_app.sidecar_executable_from_app_executable
discover_backend_port_from_process_table = smoke_test_desktop_app.discover_backend_port_from_process_table


class SmokeTestDesktopAppTests(unittest.TestCase):
    def test_local_urlopen_disables_proxy_environment_for_loopback_checks(self):
        opener = mock.Mock()
        response = mock.Mock()
        opener.open.return_value = response
        proxy_handler = mock.Mock()

        with mock.patch.object(
            smoke_test_desktop_app,
            "ProxyHandler",
            return_value=proxy_handler,
        ) as proxy_handler_cls, mock.patch.object(
            smoke_test_desktop_app,
            "build_opener",
            return_value=opener,
        ) as build_opener:
            result = smoke_test_desktop_app.local_urlopen(
                "http://127.0.0.1:18123/api/info",
                timeout=1,
            )

        proxy_handler_cls.assert_called_once_with({})
        build_opener.assert_called_once_with(proxy_handler)
        opener.open.assert_called_once_with("http://127.0.0.1:18123/api/info", timeout=1)
        self.assertIs(result, response)

    def test_parse_backend_port_reads_tauri_startup_log(self):
        self.assertEqual(
            parse_backend_port("[tauri] Bundled backend sidecar started on port 18097"),
            18097,
        )

    def test_parse_backend_port_ignores_other_logs(self):
        self.assertIsNone(parse_backend_port("[cc-branch-backend] serving"))

    def test_parse_backend_port_rejects_invalid_ports(self):
        with self.assertRaisesRegex(ValueError, "Invalid backend port"):
            parse_backend_port("[tauri] Bundled backend sidecar started on port 70000")

    def test_parse_backend_port_arg_reads_sidecar_command(self):
        self.assertEqual(
            parse_backend_port_arg("/tmp/cc-branch-backend --host 127.0.0.1 --port 18123 --config /tmp/cfg"),
            18123,
        )
        self.assertEqual(
            parse_backend_port_arg("/tmp/cc-branch-backend --port=18124 --config /tmp/cfg"),
            18124,
        )

    def test_discover_backend_port_from_process_table_filters_to_smoke_home(self):
        home = Path("/tmp/home").resolve()
        process_list = "\n".join(
            [
                "/tmp/cc-branch-backend --port 11111 --config /tmp/other/.cc-branch/config.yaml",
                f"/tmp/cc-branch-backend --host 127.0.0.1 --port 18123 --config {home}/.cc-branch/config.yaml",
            ]
        )

        with mock.patch.object(smoke_test_desktop_app.os, "name", "posix"), \
             mock.patch.object(smoke_test_desktop_app.subprocess, "run") as run:
            run.return_value = mock.Mock(stdout=process_list)
            port = discover_backend_port_from_process_table(home)

        self.assertEqual(port, 18123)
        run.assert_called_once()

    def test_isolated_desktop_env_clears_user_web_token(self):
        env = isolated_desktop_env(
            Path("/tmp/cc-branch-desktop-home"),
            {"CC_BRANCH_WEB_TOKEN": "user-token"},
        )

        self.assertEqual(env["CC_BRANCH_WEB_TOKEN"], "")

    def test_isolated_desktop_env_removes_backend_runtime_pollution(self):
        env = isolated_desktop_env(
            Path("/tmp/cc-branch-desktop-home"),
            {
                "PYTHONHOME": "/bad/python",
                "PYTHONPATH": "/bad/path",
                "VIRTUAL_ENV": "/bad/venv",
                "CONDA_PREFIX": "/bad/conda",
                "LD_LIBRARY_PATH": "/bad/libs",
                "DYLD_LIBRARY_PATH": "/bad/dylibs",
                "PATH": "/usr/bin",
            },
        )

        for name in (
            "PYTHONHOME",
            "PYTHONPATH",
            "VIRTUAL_ENV",
            "CONDA_PREFIX",
            "LD_LIBRARY_PATH",
            "DYLD_LIBRARY_PATH",
        ):
            self.assertNotIn(name, env)
        self.assertEqual(env["PATH"], "/usr/bin")

    def test_app_executable_from_bundle_prefers_cc_branch_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "CC Branch.app"
            executable = bundle / "Contents" / "MacOS" / "cc-branch"
            executable.parent.mkdir(parents=True)
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o755)

            self.assertEqual(app_executable_from_bundle(bundle), executable.resolve())

    def test_sidecar_executable_from_app_executable_finds_platform_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "cc-branch.exe"
            sidecar = Path(tmp) / "cc-branch-backend.exe"
            app.write_text("", encoding="utf-8")
            sidecar.write_text("", encoding="utf-8")

            self.assertEqual(sidecar_executable_from_app_executable(app), sidecar.resolve())

    def test_wait_for_backend_port_does_not_depend_on_unix_select(self):
        class Stdout:
            def __init__(self):
                self.lines = ["[tauri] Bundled backend sidecar started on port 18123\n", ""]

            def readline(self):
                return self.lines.pop(0)

        process = mock.Mock()
        process.stdout = Stdout()
        process.poll.return_value = None

        self.assertFalse(hasattr(smoke_test_desktop_app, "select"))
        port, logs = wait_for_backend_port(process, timeout=1)

        self.assertEqual(port, 18123)
        self.assertEqual(logs, ["[tauri] Bundled backend sidecar started on port 18123"])

    def test_start_stdout_reader_stops_on_non_string_mock_stdout(self):
        process = mock.Mock()
        process.stdout.readline.return_value = mock.Mock()

        logs = start_stdout_reader(process)
        time.sleep(0.05)

        self.assertEqual(logs, [])
        self.assertLessEqual(process.stdout.readline.call_count, 1)

    def test_isolated_desktop_env_overrides_all_user_data_roots(self):
        home = Path("/tmp/cc-branch-home")
        env = isolated_desktop_env(
            home,
            {
                "HOME": "/real/home",
                "USERPROFILE": "C:/Users/Real",
                "APPDATA": "C:/Users/Real/AppData/Roaming",
                "LOCALAPPDATA": "C:/Users/Real/AppData/Local",
                "XDG_CONFIG_HOME": "/real/config",
                "XDG_DATA_HOME": "/real/data",
            },
        )

        self.assertEqual(env["HOME"], str(home))
        self.assertEqual(env["USERPROFILE"], str(home))
        self.assertEqual(env["APPDATA"], str(home / "AppData" / "Roaming"))
        self.assertEqual(env["LOCALAPPDATA"], str(home / "AppData" / "Local"))
        self.assertEqual(env["XDG_CONFIG_HOME"], str(home / ".config"))
        self.assertEqual(env["XDG_DATA_HOME"], str(home / ".local" / "share"))

    def test_verify_desktop_app_checks_first_run_project_flow(self):
        requests: list[tuple[str, str, dict | None]] = []
        captured: dict[str, object] = {}

        def fake_request_json(port: int, path: str, *, method: str = "GET", body: dict | None = None) -> dict:
            requests.append((method, path, body))
            home = captured["home"]
            assert isinstance(home, Path)
            workspace = home / "first-run-project"
            if path == "/api/info":
                return {
                    "port": port,
                    "backend_source": "bundled-sidecar",
                    "desktop_version": "1.0.2",
                    "desktop_platform": "darwin",
                    "desktop_arch": "aarch64",
                    "config_path": str(home / ".cc-branch" / "app" / "backend-workspace" / ".cc-branch" / "config.yaml"),
                    "state_path": str(home / ".cc-branch" / "app" / "backend-workspace" / ".cc-branch" / "state.yaml"),
                }
            if path == "/api/projects":
                return {"projects": [], "storage_path": str(home / ".cc-branch" / "app" / "projects.json")}
            if path.startswith("/api/project/probe"):
                return {"status": "needs_init", "path_exists": True}
            if path == "/api/projects/add":
                return {
                    "active_project_id": "project-1",
                    "projects": [{"id": "project-1", "path": body["path"]}],
                }
            if path.startswith("/api/status"):
                status = "ready" if captured.get("initialized") else "needs_init"
                return {
                    "status": status,
                    "config_path": str(workspace / ".cc-branch" / "config.yaml"),
                }
            if path.startswith("/api/init"):
                config_path = workspace / ".cc-branch" / "config.yaml"
                state_path = workspace / ".cc-branch" / "state.yaml"
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_path.write_text("workspace:\n  name: Smoke Project\n", encoding="utf-8")
                state_path.write_text("sessions: {}\n", encoding="utf-8")
                captured["initialized"] = True
                return {
                    "success": True,
                    "config_path": str(config_path),
                    "state_path": str(state_path),
                }
            raise AssertionError(f"Unexpected request: {method} {path}")

        def fake_popen(*args, **kwargs):
            captured["env"] = kwargs["env"]
            captured["home"] = Path(kwargs["env"]["HOME"])
            workspace = captured["home"] / "first-run-project"
            workspace.mkdir(parents=True)
            return process

        process = mock.Mock()
        process.stdout = mock.Mock()
        process.terminate.return_value = None
        process.wait.return_value = 0

        with mock.patch.object(smoke_test_desktop_app.subprocess, "Popen", side_effect=fake_popen), \
             mock.patch.object(smoke_test_desktop_app, "wait_for_backend_port", return_value=(18123, ["ready"])), \
             mock.patch.object(smoke_test_desktop_app, "request_json", side_effect=fake_request_json):
            result = verify_desktop_app(Path("/tmp/cc-branch"), timeout=1)

        paths = [path for _, path, _ in requests]
        self.assertEqual(captured["env"]["CC_BRANCH_DESKTOP_PORT"], str(result["port"]))
        self.assertEqual(captured["env"]["CC_BRANCH_DESKTOP_ALLOW_FIXED_PORT"], "1")
        self.assertEqual(result["port_mode"], "fixed")
        self.assertEqual(captured["env"]["APPDATA"], str(captured["home"] / "AppData" / "Roaming"))
        self.assertEqual(captured["env"]["LOCALAPPDATA"], str(captured["home"] / "AppData" / "Local"))
        self.assertEqual(captured["env"]["XDG_CONFIG_HOME"], str(captured["home"] / ".config"))
        self.assertEqual(captured["env"]["XDG_DATA_HOME"], str(captured["home"] / ".local" / "share"))
        self.assertEqual(result["backend_source"], "bundled-sidecar")
        self.assertEqual(result["desktop_version"], "1.0.2")
        self.assertEqual(result["desktop_platform"], "darwin")
        self.assertEqual(result["desktop_arch"], "aarch64")
        self.assertIn("first_run", result)
        self.assertEqual(result["first_run"]["project_status"], "needs_init")
        self.assertIn("/api/projects", paths)
        self.assertTrue(any(path.startswith("/api/project/probe") for path in paths))
        self.assertIn("/api/projects/add", paths)
        self.assertGreaterEqual(sum(1 for path in paths if path.startswith("/api/status")), 2)
        self.assertTrue(any(path.startswith("/api/init") for path in paths))
        self.assertTrue(result["first_run"]["initialized"])
        self.assertEqual(result["first_run"]["ready_status"], "ready")

    def test_verify_desktop_app_polls_fixed_port_without_stdout_startup_log(self):
        requests: list[tuple[int, str]] = []
        captured: dict[str, Path | dict[str, str]] = {}

        def fake_request_json(port: int, path: str, *, method: str = "GET", body: dict | None = None) -> dict:
            requests.append((port, path))
            home = captured["home"]
            assert isinstance(home, Path)
            workspace = home / "first-run-project"
            if path == "/api/info":
                return {
                    "port": port,
                    "backend_source": "bundled-sidecar",
                    "desktop_version": "1.0.2",
                    "desktop_platform": "linux",
                    "desktop_arch": "x86_64",
                    "config_path": str(home / ".cc-branch" / "app" / "backend-workspace" / ".cc-branch" / "config.yaml"),
                    "state_path": str(home / ".cc-branch" / "app" / "backend-workspace" / ".cc-branch" / "state.yaml"),
                }
            if path == "/api/projects":
                return {"projects": [], "storage_path": str(home / ".cc-branch" / "app" / "projects.json")}
            if path.startswith("/api/project/probe"):
                return {"status": "needs_init", "path_exists": True}
            if path == "/api/projects/add":
                return {
                    "active_project_id": "project-1",
                    "projects": [{"id": "project-1", "path": body["path"]}],
                }
            if path.startswith("/api/status"):
                status = "ready" if captured.get("initialized") else "needs_init"
                return {
                    "status": status,
                    "config_path": str(workspace / ".cc-branch" / "config.yaml"),
                }
            if path.startswith("/api/init"):
                config_path = workspace / ".cc-branch" / "config.yaml"
                state_path = workspace / ".cc-branch" / "state.yaml"
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_path.write_text("workspace:\n  name: Smoke Project\n", encoding="utf-8")
                state_path.write_text("sessions: {}\n", encoding="utf-8")
                captured["initialized"] = True
                return {
                    "success": True,
                    "config_path": str(config_path),
                    "state_path": str(state_path),
                }
            raise AssertionError(f"Unexpected request: {method} {path}")

        def fake_popen(*args, **kwargs):
            captured["env"] = kwargs["env"]
            captured["home"] = Path(kwargs["env"]["HOME"])
            return process

        process = mock.Mock()
        process.terminate.return_value = None
        process.wait.return_value = 0

        with mock.patch.object(smoke_test_desktop_app.subprocess, "Popen", side_effect=fake_popen), \
             mock.patch.object(smoke_test_desktop_app, "wait_for_backend_port", side_effect=AssertionError("stdout port log should not be required")), \
             mock.patch.object(smoke_test_desktop_app, "request_json", side_effect=fake_request_json):
            result = verify_desktop_app(Path("/tmp/cc-branch"), timeout=1)

        env = captured["env"]
        assert isinstance(env, dict)
        self.assertEqual(env["CC_BRANCH_DESKTOP_PORT"], str(result["port"]))
        self.assertEqual(env["CC_BRANCH_DESKTOP_ALLOW_FIXED_PORT"], "1")
        self.assertEqual(result["port_mode"], "fixed")
        self.assertTrue(all(port == result["port"] for port, _ in requests))

    def test_verify_desktop_app_can_follow_user_auto_selected_port(self):
        requests: list[tuple[int, str]] = []
        captured: dict[str, Path | dict[str, str]] = {}

        def fake_request_json(port: int, path: str, *, method: str = "GET", body: dict | None = None) -> dict:
            requests.append((port, path))
            home = captured["home"]
            assert isinstance(home, Path)
            workspace = home / "first-run-project"
            if path == "/api/info":
                return {
                    "port": port,
                    "backend_source": "bundled-sidecar",
                    "desktop_version": "1.0.2",
                    "desktop_platform": "darwin",
                    "desktop_arch": "aarch64",
                    "config_path": str(home / ".cc-branch" / "app" / "backend-workspace" / ".cc-branch" / "config.yaml"),
                    "state_path": str(home / ".cc-branch" / "app" / "backend-workspace" / ".cc-branch" / "state.yaml"),
                }
            if path == "/api/projects":
                return {"projects": [], "storage_path": str(home / ".cc-branch" / "app" / "projects.json")}
            if path.startswith("/api/project/probe"):
                return {"status": "needs_init", "path_exists": True}
            if path == "/api/projects/add":
                return {
                    "active_project_id": "project-1",
                    "projects": [{"id": "project-1", "path": body["path"]}],
                }
            if path.startswith("/api/status"):
                status = "ready" if captured.get("initialized") else "needs_init"
                return {
                    "status": status,
                    "config_path": str(workspace / ".cc-branch" / "config.yaml"),
                }
            if path.startswith("/api/init"):
                config_path = workspace / ".cc-branch" / "config.yaml"
                state_path = workspace / ".cc-branch" / "state.yaml"
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_path.write_text("workspace:\n  name: Smoke Project\n", encoding="utf-8")
                state_path.write_text("sessions: {}\n", encoding="utf-8")
                captured["initialized"] = True
                return {
                    "success": True,
                    "config_path": str(config_path),
                    "state_path": str(state_path),
                }
            raise AssertionError(f"Unexpected request: {method} {path}")

        def fake_popen(*args, **kwargs):
            captured["env"] = kwargs["env"]
            captured["home"] = Path(kwargs["env"]["HOME"])
            return process

        process = mock.Mock()
        process.terminate.return_value = None
        process.wait.return_value = 0

        with mock.patch.object(smoke_test_desktop_app.subprocess, "Popen", side_effect=fake_popen), \
             mock.patch.object(smoke_test_desktop_app, "wait_for_backend_port", return_value=(19123, ["[tauri] Bundled backend sidecar started on port 19123"])) as wait_for_port, \
             mock.patch.object(smoke_test_desktop_app, "request_json", side_effect=fake_request_json):
            result = verify_desktop_app(Path("/tmp/cc-branch"), timeout=1, use_auto_port=True)

        env = captured["env"]
        assert isinstance(env, dict)
        self.assertNotIn("CC_BRANCH_DESKTOP_PORT", env)
        self.assertNotIn("CC_BRANCH_DESKTOP_ALLOW_FIXED_PORT", env)
        self.assertEqual(result["port"], 19123)
        self.assertEqual(result["port_mode"], "auto")
        self.assertTrue(all(port == 19123 for port, _ in requests))
        self.assertIn("Bundled backend sidecar started", result["startup_log"][0])
        wait_for_port.assert_called_once_with(process, 1, discovery_root=captured["home"])

    def test_verify_desktop_app_requires_desktop_metadata(self):
        captured: dict[str, Path | dict[str, str]] = {}

        def fake_request_json(port: int, path: str, *, method: str = "GET", body: dict | None = None) -> dict:
            home = captured["home"]
            assert isinstance(home, Path)
            if path == "/api/info":
                return {
                    "port": port,
                    "backend_source": "bundled-sidecar",
                    "config_path": str(home / ".cc-branch" / "app" / "backend-workspace" / ".cc-branch" / "config.yaml"),
                    "state_path": str(home / ".cc-branch" / "app" / "backend-workspace" / ".cc-branch" / "state.yaml"),
                }
            raise AssertionError(f"Unexpected request: {method} {path}")

        def fake_popen(*args, **kwargs):
            captured["env"] = kwargs["env"]
            captured["home"] = Path(kwargs["env"]["HOME"])
            return process

        process = mock.Mock()
        process.terminate.return_value = None
        process.wait.return_value = 0

        with mock.patch.object(smoke_test_desktop_app.subprocess, "Popen", side_effect=fake_popen), \
             mock.patch.object(smoke_test_desktop_app, "request_json", side_effect=fake_request_json):
            with self.assertRaisesRegex(RuntimeError, "desktop_version"):
                verify_desktop_app(Path("/tmp/cc-branch"), timeout=1)

    def test_verify_desktop_app_rejects_wrong_desktop_metadata(self):
        captured: dict[str, Path | dict[str, str]] = {}

        def fake_request_json(port: int, path: str, *, method: str = "GET", body: dict | None = None) -> dict:
            home = captured["home"]
            assert isinstance(home, Path)
            if path == "/api/info":
                return {
                    "port": port,
                    "backend_source": "bundled-sidecar",
                    "desktop_version": "1.0.1",
                    "desktop_platform": "darwin",
                    "desktop_arch": "aarch64",
                    "config_path": str(home / ".cc-branch" / "app" / "backend-workspace" / ".cc-branch" / "config.yaml"),
                    "state_path": str(home / ".cc-branch" / "app" / "backend-workspace" / ".cc-branch" / "state.yaml"),
                }
            raise AssertionError(f"Unexpected request: {method} {path}")

        def fake_popen(*args, **kwargs):
            captured["env"] = kwargs["env"]
            captured["home"] = Path(kwargs["env"]["HOME"])
            return process

        process = mock.Mock()
        process.terminate.return_value = None
        process.wait.return_value = 0

        with mock.patch.object(smoke_test_desktop_app.subprocess, "Popen", side_effect=fake_popen), \
             mock.patch.object(smoke_test_desktop_app, "request_json", side_effect=fake_request_json):
            with self.assertRaisesRegex(RuntimeError, "desktop_version"):
                verify_desktop_app(
                    Path("/tmp/cc-branch"),
                    timeout=1,
                    expected_version="1.0.2",
                    expected_platform="darwin",
                    expected_arch="aarch64",
                )

    def test_verify_desktop_app_rejects_python_fallback_backend(self):
        captured: dict[str, Path | dict[str, str]] = {}

        def fake_request_json(port: int, path: str, *, method: str = "GET", body: dict | None = None) -> dict:
            home = captured["home"]
            assert isinstance(home, Path)
            if path == "/api/info":
                return {
                    "port": port,
                    "backend_source": "python-fallback",
                    "config_path": str(home / ".cc-branch" / "app" / "backend-workspace" / ".cc-branch" / "config.yaml"),
                    "state_path": str(home / ".cc-branch" / "app" / "backend-workspace" / ".cc-branch" / "state.yaml"),
                }
            raise AssertionError(f"Unexpected request after fallback detection: {method} {path}")

        def fake_popen(*args, **kwargs):
            captured["env"] = kwargs["env"]
            captured["home"] = Path(kwargs["env"]["HOME"])
            return process

        process = mock.Mock()
        process.terminate.return_value = None
        process.wait.return_value = 0

        with mock.patch.object(smoke_test_desktop_app.subprocess, "Popen", side_effect=fake_popen), \
             mock.patch.object(smoke_test_desktop_app, "request_json", side_effect=fake_request_json):
            with self.assertRaisesRegex(RuntimeError, "bundled backend sidecar"):
                verify_desktop_app(Path("/tmp/cc-branch"), timeout=1)

    def test_verify_desktop_startup_failure_requires_expected_error_without_backend(self):
        process = mock.Mock()
        process.stdout.readline.side_effect = [
            "[tauri] Bundled backend unavailable: Bundled backend sidecar is not available\n",
            "[tauri] Python fallback is disabled in release builds; reinstall this desktop release or download a fresh installer.\n",
            "",
        ]
        process.poll.return_value = None
        process.terminate.return_value = None
        process.wait.return_value = 0

        with mock.patch.object(smoke_test_desktop_app.subprocess, "Popen", return_value=process), \
             mock.patch.object(smoke_test_desktop_app, "request_json", side_effect=OSError("connection refused")):
            result = smoke_test_desktop_app.verify_desktop_startup_failure(
                Path("/tmp/cc-branch"),
                timeout=1,
                expected_error="Python fallback is disabled in release builds",
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["backend_ready"], False)
        self.assertIn("Python fallback is disabled in release builds", "\n".join(result["startup_log"]))

    def test_verify_desktop_startup_failure_recovery_restores_sidecar_and_relaunches(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            executable = tmp_path / "cc-branch"
            recovery_sidecar = tmp_path / "original-sidecar"
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            recovery_sidecar.write_text("#!/bin/sh\n", encoding="utf-8")
            recovery_sidecar.chmod(0o755)

            with mock.patch.object(
                smoke_test_desktop_app,
                "verify_desktop_startup_failure",
                return_value={"ok": True, "backend_ready": False},
            ) as failure, mock.patch.object(
                smoke_test_desktop_app,
                "verify_desktop_app",
                return_value={"ok": True, "backend_source": "bundled-sidecar", "port_mode": "auto"},
            ) as recovery:
                result = smoke_test_desktop_app.verify_desktop_startup_failure_recovery(
                    executable,
                    recovery_sidecar=recovery_sidecar,
                    timeout=5,
                    expected_error="Python fallback is disabled in release builds",
                    expected_version="v1.0.2",
                    expected_platform="linux",
                    expected_arch="x86_64",
                )

                restored_sidecar = executable.with_name("cc-branch-backend")
                self.assertTrue(result["ok"])
                self.assertEqual(result["failure"]["backend_ready"], False)
                self.assertEqual(result["recovery"]["backend_source"], "bundled-sidecar")
                self.assertEqual(result["recovery"]["port_mode"], "auto")
                self.assertTrue(restored_sidecar.exists())
                failure.assert_called_once_with(
                    executable,
                    timeout=5,
                    expected_error="Python fallback is disabled in release builds",
                )
                recovery.assert_called_once_with(
                    executable,
                    timeout=5,
                    expected_version="v1.0.2",
                    expected_platform="linux",
                    expected_arch="x86_64",
                    use_auto_port=True,
                )

    def test_wait_for_startup_error_rejects_unexpected_backend_startup(self):
        process = mock.Mock()
        process.stdout.readline.side_effect = [
            "[tauri] Bundled backend sidecar started on port 18123\n",
            "",
        ]
        process.poll.return_value = None

        with self.assertRaisesRegex(RuntimeError, "unexpectedly reported bundled backend startup"):
            smoke_test_desktop_app.wait_for_startup_error(
                process,
                timeout=1,
                expected_error="Unexpected backend",
            )

    def test_verify_desktop_rejects_stale_backend_on_same_port(self):
        popen_calls: list[tuple[tuple, dict]] = []

        stale_process = mock.Mock()
        stale_process.poll.return_value = None
        stale_process.terminate.return_value = None
        stale_process.wait.return_value = 0
        desktop_process = mock.Mock()
        desktop_process.poll.return_value = None
        desktop_process.terminate.return_value = None
        desktop_process.wait.return_value = 0

        def fake_popen(*args, **kwargs):
            popen_calls.append((args, kwargs))
            return stale_process if len(popen_calls) == 1 else desktop_process

        def fake_wait_for_backend_info(port, process, timeout, logs=None):
            command = popen_calls[0][0][0]
            config_path = command[command.index("--config") + 1]
            state_path = command[command.index("--state") + 1]
            return {
                "port": port,
                "backend_source": "bundled-sidecar",
                "config_path": config_path,
                "state_path": state_path,
            }

        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "cc-branch"
            sidecar = Path(tmp) / "cc-branch-backend"
            app.write_text("", encoding="utf-8")
            sidecar.write_text("", encoding="utf-8")
            app.chmod(0o755)
            sidecar.chmod(0o755)

            with mock.patch.object(smoke_test_desktop_app.subprocess, "Popen", side_effect=fake_popen), \
                 mock.patch.object(smoke_test_desktop_app, "wait_for_backend_info", side_effect=fake_wait_for_backend_info), \
                 mock.patch.object(smoke_test_desktop_app, "pick_unused_localhost_port", return_value=18123), \
                 mock.patch.object(smoke_test_desktop_app, "wait_for_startup_error", return_value=[
                     "[tauri] Bundled backend unavailable: Unexpected backend config path on 127.0.0.1:18123",
                 ]):
                result = smoke_test_desktop_app.verify_desktop_rejects_stale_backend(
                    app,
                    sidecar_executable=sidecar,
                    timeout=1,
                )

        self.assertTrue(result["ok"])
        self.assertEqual(result["port"], 18123)
        self.assertEqual(result["stale_backend_source"], "bundled-sidecar")
        self.assertIn("Unexpected backend config path", "\n".join(result["startup_log"]))
        self.assertEqual(popen_calls[0][0][0][0], str(sidecar.resolve()))
        self.assertEqual(popen_calls[1][0][0][0], str(app.resolve()))
        self.assertEqual(popen_calls[0][1]["env"]["CC_BRANCH_BACKEND_SOURCE"], "bundled-sidecar")
        self.assertEqual(popen_calls[1][1]["env"]["CC_BRANCH_DESKTOP_PORT"], "18123")
        self.assertEqual(popen_calls[1][1]["env"]["CC_BRANCH_DESKTOP_ALLOW_FIXED_PORT"], "1")

    def test_verify_desktop_rejects_old_stale_backend_without_source_marker(self):
        popen_calls: list[tuple[tuple, dict]] = []

        stale_process = mock.Mock()
        stale_process.poll.return_value = None
        stale_process.terminate.return_value = None
        stale_process.wait.return_value = 0
        desktop_process = mock.Mock()
        desktop_process.poll.return_value = None
        desktop_process.terminate.return_value = None
        desktop_process.wait.return_value = 0

        def fake_popen(*args, **kwargs):
            popen_calls.append((args, kwargs))
            return stale_process if len(popen_calls) == 1 else desktop_process

        def fake_wait_for_backend_info(port, process, timeout, logs=None):
            command = popen_calls[0][0][0]
            return {
                "port": port,
                "config_path": command[command.index("--config") + 1],
                "state_path": command[command.index("--state") + 1],
            }

        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "cc-branch"
            sidecar = Path(tmp) / "cc-branch-backend"
            app.write_text("", encoding="utf-8")
            sidecar.write_text("", encoding="utf-8")

            with mock.patch.object(smoke_test_desktop_app.subprocess, "Popen", side_effect=fake_popen), \
                 mock.patch.object(smoke_test_desktop_app, "wait_for_backend_info", side_effect=fake_wait_for_backend_info), \
                 mock.patch.object(smoke_test_desktop_app, "pick_unused_localhost_port", return_value=18123), \
                 mock.patch.object(smoke_test_desktop_app, "wait_for_startup_error", return_value=[
                     "[tauri] Bundled backend unavailable: Unexpected backend source on 127.0.0.1:18123",
                 ]):
                result = smoke_test_desktop_app.verify_desktop_rejects_stale_backend(
                    app,
                    sidecar_executable=sidecar,
                    timeout=1,
                    expected_error="Unexpected backend",
                )

        self.assertTrue(result["ok"])
        self.assertEqual(result["stale_backend_source"], "unknown")

    def test_main_stale_backend_mode_defaults_to_path_mismatch_error(self):
        captured: dict[str, object] = {}

        def fake_verify(executable: Path, *, sidecar_executable: Path, timeout: float, expected_error: str) -> dict:
            captured["expected_error"] = expected_error
            return {"ok": True}

        with mock.patch.object(smoke_test_desktop_app, "app_executable_from_bundle", return_value=Path("/tmp/cc-branch")), \
             mock.patch.object(smoke_test_desktop_app, "sidecar_executable_from_app_executable", return_value=Path("/tmp/cc-branch-backend")), \
             mock.patch.object(smoke_test_desktop_app, "verify_desktop_rejects_stale_backend", side_effect=fake_verify), \
             mock.patch.object(smoke_test_desktop_app, "print"):
            smoke_test_desktop_app.main(["/tmp/cc-branch", "--expect-stale-backend-rejection"])

        self.assertEqual(captured["expected_error"], "Unexpected backend")


if __name__ == "__main__":
    unittest.main()
