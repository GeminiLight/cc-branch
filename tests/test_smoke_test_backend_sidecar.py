from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "smoke-test-backend-sidecar.py"
SPEC = importlib.util.spec_from_file_location("smoke_test_backend_sidecar", SCRIPT_PATH)
assert SPEC and SPEC.loader
smoke_test_backend_sidecar = importlib.util.module_from_spec(SPEC)
sys.modules["smoke_test_backend_sidecar"] = smoke_test_backend_sidecar
SPEC.loader.exec_module(smoke_test_backend_sidecar)
isolated_backend_env = smoke_test_backend_sidecar.isolated_backend_env


class SmokeTestBackendSidecarTests(unittest.TestCase):
    def test_local_urlopen_disables_proxy_environment_for_loopback_checks(self):
        opener = mock.Mock()
        response = mock.Mock()
        opener.open.return_value = response
        proxy_handler = mock.Mock()

        with mock.patch.object(
            smoke_test_backend_sidecar,
            "ProxyHandler",
            return_value=proxy_handler,
        ) as proxy_handler_cls, mock.patch.object(
            smoke_test_backend_sidecar,
            "build_opener",
            return_value=opener,
        ) as build_opener:
            result = smoke_test_backend_sidecar.local_urlopen(
                "http://127.0.0.1:5192/api/info",
                timeout=1,
            )

        proxy_handler_cls.assert_called_once_with({})
        build_opener.assert_called_once_with(proxy_handler)
        opener.open.assert_called_once_with("http://127.0.0.1:5192/api/info", timeout=1)
        self.assertIs(result, response)

    def test_isolated_backend_env_overrides_all_user_data_roots(self):
        home = Path("/tmp/cc-branch-backend-home")
        env = isolated_backend_env(
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
        self.assertEqual(env["CC_BRANCH_BACKEND_SOURCE"], "bundled-sidecar")

    def test_isolated_backend_env_can_mark_desktop_metadata(self):
        env = isolated_backend_env(
            Path("/tmp/cc-branch-backend-home"),
            {},
            desktop_version="v1.0.2",
            desktop_platform="darwin",
            desktop_arch="aarch64",
        )

        self.assertEqual(env["CC_BRANCH_DESKTOP_VERSION"], "1.0.2")
        self.assertEqual(env["CC_BRANCH_DESKTOP_PLATFORM"], "darwin")
        self.assertEqual(env["CC_BRANCH_DESKTOP_ARCH"], "aarch64")

    def test_isolated_backend_env_clears_user_web_token(self):
        env = isolated_backend_env(
            Path("/tmp/cc-branch-backend-home"),
            {"CC_BRANCH_WEB_TOKEN": "user-token"},
        )

        self.assertEqual(env["CC_BRANCH_WEB_TOKEN"], "")

    def test_isolated_backend_env_removes_python_runtime_pollution(self):
        env = isolated_backend_env(
            Path("/tmp/cc-branch-backend-home"),
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

    def test_assert_backend_source_requires_bundled_sidecar_marker(self):
        with self.assertRaisesRegex(RuntimeError, "bundled-sidecar"):
            smoke_test_backend_sidecar.assert_backend_source({"backend_source": "cli"})

    def test_assert_backend_source_accepts_bundled_sidecar_marker(self):
        smoke_test_backend_sidecar.assert_backend_source({"backend_source": "bundled-sidecar"})

    def test_build_smoke_result_exposes_backend_source(self):
        result = smoke_test_backend_sidecar.build_smoke_result(
            port=5192,
            executable=Path("/tmp/cc-branch-backend"),
            backend_source="bundled-sidecar",
            desktop_metadata={
                "desktop_version": "1.0.2",
                "desktop_platform": "linux",
                "desktop_arch": "x86_64",
            },
            first_run={"project_status": "needs_init"},
        )

        self.assertEqual(result["backend_source"], "bundled-sidecar")
        self.assertEqual(result["desktop_version"], "1.0.2")
        self.assertEqual(result["desktop_platform"], "linux")
        self.assertEqual(result["desktop_arch"], "x86_64")

    def test_assert_desktop_metadata_rejects_wrong_version(self):
        with self.assertRaisesRegex(RuntimeError, "desktop_version"):
            smoke_test_backend_sidecar.assert_desktop_metadata(
                {
                    "desktop_version": "1.0.1",
                    "desktop_platform": "linux",
                    "desktop_arch": "x86_64",
                },
                expected_version="v1.0.2",
                expected_platform="linux",
                expected_arch="x86_64",
            )

    def test_assert_desktop_metadata_accepts_expected_values(self):
        metadata = smoke_test_backend_sidecar.assert_desktop_metadata(
            {
                "desktop_version": "1.0.2",
                "desktop_platform": "linux",
                "desktop_arch": "x86_64",
            },
            expected_version="v1.0.2",
            expected_platform="linux",
            expected_arch="x86_64",
        )

        self.assertEqual(metadata["desktop_version"], "1.0.2")

    def test_first_run_api_check_initializes_project_and_reaches_ready(self):
        requests: list[tuple[str, str, dict | None]] = []
        initialized = False

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            workspace = Path(tmp) / "project"
            config_path = workspace / ".cc-branch" / "config.yaml"
            state_path = workspace / ".cc-branch" / "state.yaml"
            home.mkdir()
            workspace.mkdir()

            def fake_request_json(
                port: int,
                path: str,
                *,
                method: str = "GET",
                body: dict | None = None,
            ) -> dict:
                nonlocal initialized
                requests.append((method, path, body))
                if path == "/api/projects":
                    return {"projects": [], "storage_path": str(home / ".cc-branch" / "app" / "projects.yaml")}
                if path.startswith("/api/project/probe"):
                    return {"status": "needs_init", "path_exists": True}
                if path == "/api/projects/add":
                    return {
                        "active_project_id": "project-1",
                        "projects": [{"id": "project-1", "path": body["path"]}],
                    }
                if path.startswith("/api/status"):
                    return {
                        "status": "ready" if initialized else "needs_init",
                        "config_path": str(config_path),
                    }
                if path.startswith("/api/init"):
                    config_path.parent.mkdir(parents=True, exist_ok=True)
                    config_path.write_text("workspace:\n  name: Smoke Project\n", encoding="utf-8")
                    state_path.write_text("version: 1\nwindows: {}\n", encoding="utf-8")
                    initialized = True
                    return {
                        "success": True,
                        "config_path": str(config_path),
                        "state_path": str(state_path),
                    }
                raise AssertionError(f"Unexpected request: {method} {path}")

            with mock.patch.object(
                smoke_test_backend_sidecar,
                "request_json",
                side_effect=fake_request_json,
            ):
                result = smoke_test_backend_sidecar.assert_first_run_api_ready(
                    5192,
                    workspace,
                    config_path,
                    state_path,
                    home,
                )

        paths = [path for _method, path, _body in requests]
        self.assertTrue(any(path.startswith("/api/init") for path in paths))
        self.assertGreaterEqual(sum(1 for path in paths if path.startswith("/api/status")), 2)
        self.assertEqual(result["project_status"], "needs_init")
        self.assertEqual(result["ready_status"], "ready")
        self.assertTrue(result["initialized"])


if __name__ == "__main__":
    unittest.main()
