"""Tests for the cc-branch Web UI."""

from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from importlib.resources import files
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from cc_branch.webui.server import (
    WebUIHandler,
    _cli_command,
    _open_terminal,
    _slot_exists,
)


class SlotHelpersTests(unittest.TestCase):
    """Tests for slot helper functions."""

    def test_slot_exists_returns_bool(self):
        """_slot_exists should return a boolean."""
        # Testing with a session that likely doesn't exist
        result = _slot_exists("nonexistent-session-12345")
        self.assertIsInstance(result, bool)
        self.assertFalse(result)


class TerminalOpenTests(unittest.TestCase):
    """Tests for local terminal launch helpers."""

    def test_windows_cli_command_uses_powershell_call_operator_for_paths(self):
        """PowerShell needs & before quoted executable paths."""
        from unittest.mock import patch

        with (
            patch("cc_branch.webui.server.sys.platform", "win32"),
            patch("cc_branch.webui.server.sys.argv", ["C:/Program Files/cc-branch/cc-branch.exe"]),
            patch("cc_branch.webui.server.Path.exists", return_value=True),
            patch("cc_branch.webui.server.Path.resolve", return_value="C:/Program Files/cc-branch/cc-branch.exe"),
        ):
            command = _cli_command()

        self.assertEqual(command, "& 'C:/Program Files/cc-branch/cc-branch.exe'")

    def test_windows_cli_command_escapes_single_quotes(self):
        """PowerShell command paths with apostrophes should remain executable."""
        from unittest.mock import patch

        with (
            patch("cc_branch.webui.server.sys.platform", "win32"),
            patch("cc_branch.webui.server.sys.argv", ["C:/Users/O'Neil/bin/cc-branch.exe"]),
            patch("cc_branch.webui.server.Path.exists", return_value=True),
            patch("cc_branch.webui.server.Path.resolve", return_value="C:/Users/O'Neil/bin/cc-branch.exe"),
        ):
            command = _cli_command()

        self.assertEqual(command, "& 'C:/Users/O''Neil/bin/cc-branch.exe'")

    def test_macos_terminal_open_reports_osascript_failure(self):
        """macOS Terminal automation failures should surface to the Web UI."""
        from unittest.mock import Mock, patch

        failed = Mock(returncode=1, stderr="Not authorized to send Apple events")
        with (
            patch("cc_branch.openers.sys.platform", "darwin"),
            patch("cc_branch.openers.shutil.which", return_value="/usr/bin/osascript"),
            patch("cc_branch.openers.subprocess.run", return_value=failed),
        ):
            with self.assertRaisesRegex(RuntimeError, "Cannot open Terminal"):
                _open_terminal(Path("/tmp"), "cc-branch dashboard")

    def test_open_terminal_preserves_quoted_cli_path_for_dashboard(self):
        """Legacy helper should not split executable paths on spaces."""
        from unittest.mock import patch

        with patch("cc_branch.webui.server.open_with") as open_with:
            _open_terminal(Path("/tmp"), "'/tmp/cc branch' dashboard")

        self.assertEqual(open_with.call_args.args[0], "auto-terminal")
        self.assertEqual(open_with.call_args.kwargs["cli"], "'/tmp/cc branch'")
        self.assertEqual(open_with.call_args.kwargs["intent"].kind, "workspace_dashboard")

    def test_open_terminal_parses_quoted_attach_target(self):
        """Legacy helper should pass a raw target, not a pre-quoted shell fragment."""
        from unittest.mock import patch

        with patch("cc_branch.webui.server.open_with") as open_with:
            _open_terminal(Path("/tmp"), "'/tmp/cc branch' attach 'dev window'")

        self.assertEqual(open_with.call_args.kwargs["cli"], "'/tmp/cc branch'")
        self.assertEqual(open_with.call_args.kwargs["intent"].kind, "attach_target")
        self.assertEqual(open_with.call_args.kwargs["intent"].target, "dev window")


class WebUIHandlerTests(unittest.TestCase):
    """Tests for WebUIHandler API endpoints."""

    def setUp(self):
        """Create a temporary workspace for testing."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmpdir.name)
        self.config_path = self.cwd / ".cc-branch.yaml"
        self.state_path = self.cwd / ".cc-branch.state.toml"

        config_content = """version: 1
project: "test-project"
root: "."

agents:
  claude:
    command: "claude"
    create_mode: "generated_uuid"
    create_template: "claude --session-id {session_id}"
    resume_mode: "flag"
    resume_template: "-r {session_id}"
    label_template: "{project}/{slot}/{window}"

slots:
  - name: "dev"
    backend: "tmux"
    cwd: "."
    windows:
      - name: "coder"
        agent: "claude"
      - name: "terminal"
        command: "zsh"
"""
        self.config_path.write_text(config_content)
        self.state_path.write_text('version = 1\n')

    def tearDown(self):
        """Clean up temporary workspace."""
        self.tmpdir.cleanup()

    def _start_test_server(self, port: int = 0, token: str | None = None) -> tuple:
        """Start a test server and return (server, port)."""
        from functools import partial
        from http.server import HTTPServer

        handler = partial(WebUIHandler, self.config_path, self.state_path, token=token)
        server = HTTPServer(("127.0.0.1", port), handler)
        if port == 0:
            port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.1)  # Let server start
        return server, port

    def _stop_test_server(self, server) -> None:
        server.shutdown()
        server.server_close()

    def test_api_status_returns_json(self):
        """Test /api/status returns valid JSON with expected structure."""
        server, port = self._start_test_server()
        try:
            with urlopen(f"http://127.0.0.1:{port}/api/status", timeout=2) as response:
                self.assertEqual(response.status, 200)
                data = json.loads(response.read().decode())

                self.assertIn("project", data)
                self.assertIn("config_path", data)
                self.assertIn("state_path", data)
                self.assertIn("slots", data)

                self.assertEqual(data["project"], "test-project")
                self.assertIsInstance(data["slots"], list)
                self.assertEqual(len(data["slots"]), 1)

                slot = data["slots"][0]
                self.assertEqual(slot["name"], "dev")
                self.assertEqual(slot["backend"], "tmux")
                self.assertIn("status", slot)
                self.assertIn("session_name", slot)
                self.assertIn("windows", slot)

                windows = slot["windows"]
                self.assertEqual(len(windows), 2)
                self.assertEqual(windows[0]["name"], "coder")
                self.assertEqual(windows[0]["agent"], "claude")
                self.assertEqual(windows[1]["name"], "terminal")
                self.assertEqual(windows[1]["command"], "zsh")
        finally:
            self._stop_test_server(server)

    def test_cross_origin_api_does_not_reflect_untrusted_origin(self):
        """Local APIs should not grant browser access to arbitrary websites."""
        server, port = self._start_test_server()
        try:
            request = Request(
                f"http://127.0.0.1:{port}/api/status",
                headers={"Origin": "https://evil.example"},
                method="GET",
            )
            with urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertIsNone(response.headers.get("Access-Control-Allow-Origin"))
        finally:
            self._stop_test_server(server)

    def test_cross_origin_mutating_api_is_rejected_without_token(self):
        """A malicious webpage must not be able to mutate a tokenless local server."""
        from urllib.error import HTTPError

        server, port = self._start_test_server()
        try:
            request = Request(
                f"http://127.0.0.1:{port}/api/action",
                data=json.dumps({"action": "stop", "target": "dev"}).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Origin": "https://evil.example",
                },
                method="POST",
            )
            with self.assertRaises(HTTPError) as ctx:
                urlopen(request, timeout=2)

            self.assertEqual(ctx.exception.code, 403)
            self.assertIsNone(ctx.exception.headers.get("Access-Control-Allow-Origin"))
        finally:
            self._stop_test_server(server)

    def test_tokenless_server_rejects_dns_rebinding_style_origin(self):
        """Matching Host and Origin is not enough without token protection."""
        from urllib.error import HTTPError

        server, port = self._start_test_server()
        try:
            request = Request(
                f"http://127.0.0.1:{port}/api/action",
                data=json.dumps({"action": "stop", "target": "dev"}).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Host": "evil.example",
                    "Origin": "https://evil.example",
                },
                method="POST",
            )
            with self.assertRaises(HTTPError) as ctx:
                urlopen(request, timeout=2)

            self.assertEqual(ctx.exception.code, 403)
        finally:
            self._stop_test_server(server)

    def test_loopback_dev_origin_is_allowed_for_api(self):
        """Localhost dev frontends can still call the local Web UI API."""
        server, port = self._start_test_server()
        try:
            request = Request(
                f"http://127.0.0.1:{port}/api/status",
                headers={"Origin": "http://localhost:5173"},
                method="GET",
            )
            with urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(
                    response.headers.get("Access-Control-Allow-Origin"),
                    "http://localhost:5173",
                )
        finally:
            self._stop_test_server(server)

    def test_token_protected_same_host_origin_is_allowed(self):
        """Public token-protected deployments can serve their own browser origin."""
        server, port = self._start_test_server(token="secret-token")
        try:
            request = Request(
                f"http://127.0.0.1:{port}/api/config",
                headers={
                    "Cookie": "cc_branch_token=secret-token",
                    "Host": "cc-branch.example",
                    "Origin": "https://cc-branch.example",
                },
                method="GET",
            )
            with urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(
                    response.headers.get("Access-Control-Allow-Origin"),
                    "https://cc-branch.example",
                )
        finally:
            self._stop_test_server(server)

    def test_api_status_accepts_project_path_query(self):
        """Test /api/status routes correctly when project_path is provided."""
        alt_dir = self.cwd / "alt"
        alt_dir.mkdir()
        alt_config = alt_dir / ".cc-branch.yaml"
        alt_state = alt_dir / ".cc-branch.state.toml"
        alt_config.write_text(
            self.config_path.read_text(encoding="utf-8").replace(
                'project: "test-project"', 'project: "alt-project"'
            ),
            encoding="utf-8",
        )
        alt_state.write_text("version = 1\n", encoding="utf-8")

        server, port = self._start_test_server()
        try:
            project_path = quote(str(alt_dir))
            with urlopen(
                f"http://127.0.0.1:{port}/api/status?project_path={project_path}",
                timeout=2,
            ) as response:
                self.assertEqual(response.status, 200)
                data = json.loads(response.read().decode())
                self.assertEqual(data["project"], "alt-project")
                self.assertEqual(data["config_path"], str(alt_config))
                self.assertEqual(data["state_path"], str(alt_state))
        finally:
            self._stop_test_server(server)

    def test_api_openers_returns_registered_openers(self):
        """The Web UI should expose available local openers."""
        from unittest.mock import patch

        server, port = self._start_test_server()
        try:
            with patch("cc_branch.openers.shutil.which", return_value="/usr/local/bin/code"):
                with urlopen(f"http://127.0.0.1:{port}/api/openers", timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    data = json.loads(response.read().decode())

                self.assertEqual(data["default"], "auto-terminal")
                opener_ids = {opener["id"] for opener in data["openers"]}
                self.assertIn("auto-terminal", opener_ids)
                self.assertIn("vscode", opener_ids)
                self.assertIn("cursor", opener_ids)
        finally:
            self._stop_test_server(server)

    def test_api_config_returns_content(self):
        """Test /api/config returns config file content."""
        server, port = self._start_test_server()
        try:
            with urlopen(f"http://127.0.0.1:{port}/api/config", timeout=2) as response:
                self.assertEqual(response.status, 200)
                data = json.loads(response.read().decode())

                self.assertIn("content", data)
                self.assertIn("path", data)
                self.assertIn("test-project", data["content"])
        finally:
            self._stop_test_server(server)

    def test_api_doctor_returns_report(self):
        """Test /api/doctor returns doctor report."""
        server, port = self._start_test_server()
        try:
            with urlopen(f"http://127.0.0.1:{port}/api/doctor", timeout=2) as response:
                self.assertEqual(response.status, 200)
                data = json.loads(response.read().decode())

                self.assertIn("report", data)
                self.assertIn("doctor", data["report"])
        finally:
            self._stop_test_server(server)

    def test_api_project_probe_reports_missing_config(self):
        """Project probe should distinguish an existing directory without config."""
        alt_dir = self.cwd / "needs-init"
        alt_dir.mkdir()

        server, port = self._start_test_server()
        try:
            project_path = quote(str(alt_dir))
            with urlopen(
                f"http://127.0.0.1:{port}/api/project/probe?project_path={project_path}",
                timeout=2,
            ) as response:
                self.assertEqual(response.status, 200)
                data = json.loads(response.read().decode())
                self.assertTrue(data["path_exists"])
                self.assertFalse(data["config_exists"])
                self.assertEqual(data["status"], "needs_init")
                self.assertEqual(data["project_name"], "needs-init")
        finally:
            self._stop_test_server(server)

    def test_action_stop_accepts_public_slot_target(self):
        """Stop actions should accept public slot targets, not only tmux names."""
        from unittest.mock import patch

        server, port = self._start_test_server()
        try:
            with patch("cc_branch.webui.server.stop_workspace") as stop_workspace:
                request = Request(
                    f"http://127.0.0.1:{port}/api/action",
                    data=json.dumps({"action": "stop", "target": "dev"}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    data = json.loads(response.read().decode())
                    self.assertTrue(data["success"])
                    self.assertEqual(data["message"], "Stopped dev")

                self.assertEqual(stop_workspace.call_args.args[2], "dev")
        finally:
            self._stop_test_server(server)

    def test_action_open_workspace_opens_terminal_dashboard(self):
        """Open action should launch the tmux dashboard in a system terminal."""
        from unittest.mock import patch

        server, port = self._start_test_server()
        try:
            with (
                patch("cc_branch.webui.server._cli_command", return_value="cc-branch"),
                patch("cc_branch.webui.server.open_with") as open_with,
            ):
                request = Request(
                    f"http://127.0.0.1:{port}/api/action",
                    data=json.dumps({"action": "open"}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    data = json.loads(response.read().decode())
                    self.assertTrue(data["success"])
                    self.assertEqual(data["message"], "Opened workspace dashboard in terminal")

                self.assertEqual(open_with.call_args.kwargs["opener_id"], "auto-terminal")
                self.assertEqual(open_with.call_args.kwargs["intent"].kind, "workspace_dashboard")
        finally:
            self._stop_test_server(server)

    def test_action_open_slot_starts_slot_and_opens_terminal(self):
        """Open target should ensure the slot exists before attaching in a terminal."""
        from unittest.mock import patch

        server, port = self._start_test_server()
        try:
            with (
                patch("cc_branch.webui.server._cli_command", return_value="cc-branch"),
                patch("cc_branch.webui.server.ensure_slot") as ensure_slot,
                patch("cc_branch.webui.server.open_with") as open_with,
            ):
                request = Request(
                    f"http://127.0.0.1:{port}/api/action",
                    data=json.dumps({"action": "open", "target": "dev"}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    data = json.loads(response.read().decode())
                    self.assertTrue(data["success"])
                    self.assertEqual(data["message"], "Opened dev in terminal")

                self.assertEqual(ensure_slot.call_args.args[0].name, "dev")
                self.assertEqual(open_with.call_args.kwargs["opener_id"], "auto-terminal")
                self.assertEqual(open_with.call_args.kwargs["intent"].kind, "attach_target")
                self.assertEqual(open_with.call_args.kwargs["intent"].target, "dev")
        finally:
            self._stop_test_server(server)

    def test_action_open_window_starts_slot_and_opens_terminal(self):
        """Open window target should attach directly to that slot window."""
        from unittest.mock import patch

        server, port = self._start_test_server()
        try:
            with (
                patch("cc_branch.webui.server._cli_command", return_value="cc-branch"),
                patch("cc_branch.webui.server.ensure_slot") as ensure_slot,
                patch("cc_branch.webui.server.open_with") as open_with,
            ):
                request = Request(
                    f"http://127.0.0.1:{port}/api/action",
                    data=json.dumps({"action": "open", "target": "dev:coder"}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    data = json.loads(response.read().decode())
                    self.assertTrue(data["success"])
                    self.assertEqual(data["message"], "Opened dev:coder in terminal")

                self.assertEqual(ensure_slot.call_args.args[0].name, "dev")
                self.assertEqual(open_with.call_args.kwargs["opener_id"], "auto-terminal")
                self.assertEqual(open_with.call_args.kwargs["intent"].kind, "attach_target")
                self.assertEqual(open_with.call_args.kwargs["intent"].target, "dev:coder")
        finally:
            self._stop_test_server(server)

    def test_action_open_rejects_unknown_window_before_opening_terminal(self):
        """Bad window targets should fail in the browser instead of a new terminal."""
        from unittest.mock import patch
        from urllib.error import HTTPError

        server, port = self._start_test_server()
        try:
            with (
                patch("cc_branch.webui.server.ensure_slot") as ensure_slot,
                patch("cc_branch.webui.server.open_with") as open_with,
            ):
                request = Request(
                    f"http://127.0.0.1:{port}/api/action",
                    data=json.dumps({"action": "open", "target": "dev:not-real"}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(HTTPError) as cm:
                    urlopen(request, timeout=2)

                self.assertEqual(cm.exception.code, 400)
                data = json.loads(cm.exception.read().decode())
                self.assertIn("Cannot open target: dev:not-real", data["error"])
                ensure_slot.assert_not_called()
                open_with.assert_not_called()
        finally:
            self._stop_test_server(server)

    def test_action_open_project_with_vscode_uses_project_folder_intent(self):
        """Editor openers should be allowed for explicit project-folder opens."""
        from unittest.mock import patch

        server, port = self._start_test_server()
        try:
            with patch("cc_branch.webui.server.open_with") as open_with:
                request = Request(
                    f"http://127.0.0.1:{port}/api/action",
                    data=json.dumps({
                        "action": "open",
                        "opener": "vscode",
                        "intent": "project_folder",
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    data = json.loads(response.read().decode())
                    self.assertTrue(data["success"])
                    self.assertEqual(data["message"], "Opened project in VS Code")

                self.assertEqual(open_with.call_args.kwargs["opener_id"], "vscode")
                self.assertEqual(open_with.call_args.kwargs["intent"].kind, "project_folder")
        finally:
            self._stop_test_server(server)

    def test_action_open_rejects_editor_attach_intent(self):
        """Editor openers should not silently downgrade attach requests."""
        from unittest.mock import patch
        from urllib.error import HTTPError

        from cc_branch.openers import OpenerError

        server, port = self._start_test_server()
        try:
            with patch("cc_branch.webui.server.open_with", side_effect=OpenerError("Opener vscode does not support attach_target")):
                request = Request(
                    f"http://127.0.0.1:{port}/api/action",
                    data=json.dumps({
                        "action": "open",
                        "target": "dev",
                        "opener": "vscode",
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(HTTPError) as cm:
                    urlopen(request, timeout=2)

                self.assertEqual(cm.exception.code, 400)
                data = json.loads(cm.exception.read().decode())
                self.assertIn("does not support attach_target", data["error"])
        finally:
            self._stop_test_server(server)

    def test_root_returns_html(self):
        """Test / returns HTML dashboard."""
        server, port = self._start_test_server()
        try:
            with urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
                self.assertEqual(response.status, 200)
                content_type = response.headers.get("Content-Type", "")
                self.assertIn("text/html", content_type)

                body = response.read().decode()
                self.assertIn("CC Branch", body)
                self.assertIn("Dashboard", body)
                self.assertIn('<div id="root">', body)
                self.assertIn("<script", body)
        finally:
            self._stop_test_server(server)

    def test_static_binary_file_served_without_text_decoding(self):
        """Test binary static assets are served exactly as bytes."""
        expected = (files("cc_branch.webui.static") / "favicon.png").read_bytes()
        server, port = self._start_test_server()
        try:
            with urlopen(f"http://127.0.0.1:{port}/favicon.png", timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get("Content-Type"), "image/png")
                self.assertEqual(response.read(), expected)
        finally:
            self._stop_test_server(server)

    def test_root_requires_auth_when_token_enabled(self):
        """Root page must not hand out auth cookies to arbitrary visitors."""
        from urllib.error import HTTPError

        server, port = self._start_test_server(token="secret-token")
        try:
            with self.assertRaises(HTTPError) as ctx:
                urlopen(f"http://127.0.0.1:{port}/", timeout=2)
            self.assertEqual(ctx.exception.code, 401)
        finally:
            self._stop_test_server(server)

    def test_root_token_query_seeds_auth_cookie(self):
        """A matching one-time URL token should establish the browser cookie."""
        import http.cookiejar
        from urllib.request import HTTPCookieProcessor, build_opener

        server, port = self._start_test_server(token="secret-token")
        try:
            cookie_jar = http.cookiejar.CookieJar()
            opener = build_opener(HTTPCookieProcessor(cookie_jar))
            with opener.open(f"http://127.0.0.1:{port}/?token=secret-token", timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.geturl(), f"http://127.0.0.1:{port}/")
                self.assertIn("CC Branch", response.read().decode())

            cookies = {cookie.name: cookie.value for cookie in cookie_jar}
            self.assertEqual(cookies["cc_branch_token"], "secret-token")
        finally:
            self._stop_test_server(server)

    def test_mutating_api_requires_auth_when_token_enabled(self):
        """POST endpoints should reject unauthenticated writes when token is set."""
        from urllib.error import HTTPError

        server, port = self._start_test_server(token="secret-token")
        try:
            request = Request(
                f"http://127.0.0.1:{port}/api/action",
                data=json.dumps({"action": "stop", "target": "dev"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(HTTPError) as ctx:
                urlopen(request, timeout=2)
            self.assertEqual(ctx.exception.code, 401)
        finally:
            self._stop_test_server(server)

    def test_get_api_requires_auth_when_token_enabled(self):
        """Publicly hosted token-protected servers must not leak read APIs."""
        from urllib.error import HTTPError

        server, port = self._start_test_server(token="secret-token")
        try:
            with self.assertRaises(HTTPError) as ctx:
                urlopen(f"http://127.0.0.1:{port}/api/config", timeout=2)
            self.assertEqual(ctx.exception.code, 401)
        finally:
            self._stop_test_server(server)

    def test_get_api_accepts_cookie_token(self):
        """The root page seeded cookie should authenticate browser GET APIs."""
        server, port = self._start_test_server(token="secret-token")
        try:
            request = Request(
                f"http://127.0.0.1:{port}/api/config",
                headers={"Cookie": "cc_branch_token=secret-token"},
                method="GET",
            )
            with urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 200)
                data = json.loads(response.read().decode())
                self.assertIn("test-project", data["content"])
        finally:
            self._stop_test_server(server)

    def test_mutating_api_accepts_bearer_token(self):
        """API clients can authenticate mutating requests with Authorization."""
        from urllib.error import HTTPError

        server, port = self._start_test_server(token="secret-token")
        try:
            request = Request(
                f"http://127.0.0.1:{port}/api/action",
                data=json.dumps({"action": "unknown"}).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer secret-token",
                },
                method="POST",
            )
            with self.assertRaises(HTTPError) as ctx:
                urlopen(request, timeout=2)
            self.assertEqual(ctx.exception.code, 400)
        finally:
            self._stop_test_server(server)

    def test_mutating_api_accepts_cookie_token(self):
        """Browser Web UI actions can authenticate with the seeded same-origin cookie."""
        from urllib.error import HTTPError

        server, port = self._start_test_server(token="secret-token")
        try:
            request = Request(
                f"http://127.0.0.1:{port}/api/action",
                data=json.dumps({"action": "unknown"}).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Cookie": "cc_branch_token=secret-token",
                },
                method="POST",
            )
            with self.assertRaises(HTTPError) as ctx:
                urlopen(request, timeout=2)
            self.assertEqual(ctx.exception.code, 400)
        finally:
            self._stop_test_server(server)

    def test_404_for_unknown_paths(self):
        """Test unknown paths return 404."""
        from urllib.error import HTTPError

        server, port = self._start_test_server()
        try:
            with self.assertRaises(HTTPError):
                urlopen(f"http://127.0.0.1:{port}/unknown", timeout=2)
        finally:
            self._stop_test_server(server)

    def test_api_status_with_missing_config(self):
        """Missing config should return setup state instead of a 500."""
        missing_config = self.cwd / "missing.yaml"
        missing_state = self.cwd / "missing.toml"

        from functools import partial
        from http.server import HTTPServer

        handler = partial(WebUIHandler, missing_config, missing_state)
        server = HTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.1)

        try:
            with urlopen(f"http://127.0.0.1:{port}/api/status", timeout=2) as response:
                self.assertEqual(response.status, 200)
                data = json.loads(response.read().decode())

            self.assertEqual(data["status"], "needs_init")
            self.assertEqual(data["project_path"], str(self.cwd))
            self.assertEqual(data["config_path"], str(missing_config))
            self.assertEqual(data["state_path"], str(missing_state))
            self.assertEqual(data["project_name"], self.cwd.name)
            self.assertEqual(data["slots"], [])
        finally:
            server.shutdown()
            server.server_close()

    def test_api_config_with_missing_config_returns_empty_draft(self):
        """Missing config should still allow the UI to open an editor target."""
        missing_config = self.cwd / "missing.yaml"
        missing_state = self.cwd / "missing.toml"

        from functools import partial
        from http.server import HTTPServer

        handler = partial(WebUIHandler, missing_config, missing_state)
        server = HTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.1)

        try:
            with urlopen(f"http://127.0.0.1:{port}/api/config", timeout=2) as response:
                self.assertEqual(response.status, 200)
                data = json.loads(response.read().decode())

            self.assertEqual(data["status"], "needs_init")
            self.assertEqual(data["content"], "")
            self.assertEqual(data["path"], str(missing_config))
        finally:
            server.shutdown()
            server.server_close()

    def test_api_doctor_with_missing_config_returns_setup_guidance(self):
        """Missing config should render setup guidance, not a backend error."""
        missing_config = self.cwd / "missing.yaml"
        missing_state = self.cwd / "missing.toml"

        from functools import partial
        from http.server import HTTPServer

        handler = partial(WebUIHandler, missing_config, missing_state)
        server = HTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.1)

        try:
            with urlopen(f"http://127.0.0.1:{port}/api/doctor", timeout=2) as response:
                self.assertEqual(response.status, 200)
                data = json.loads(response.read().decode())

            self.assertEqual(data["status"], "needs_init")
            self.assertIn("No workspace config found", data["report"])
        finally:
            server.shutdown()
            server.server_close()


class CLIIntegrationTests(unittest.TestCase):
    """Tests for CLI integration of serve command."""

    def test_serve_command_in_parser(self):
        """Test that serve command is registered in argument parser."""
        from cc_branch.cli import build_parser

        parser = build_parser()
        # Parse with --help for serve to ensure it's registered
        args = parser.parse_args(["serve", "--port", "9999"])
        self.assertEqual(args.command, "serve")
        self.assertEqual(args.port, 9999)
        self.assertEqual(args.host, "127.0.0.1")

    def test_start_command_in_parser(self):
        """Start should be the primary workspace launch command."""
        from cc_branch.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["start", "--detach"])
        self.assertEqual(args.command, "start")
        self.assertTrue(args.detach)

    def test_serve_command_custom_host(self):
        """Test serve command accepts custom host."""
        from cc_branch.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["serve", "--host", "0.0.0.0", "--port", "8080"])
        self.assertEqual(args.host, "0.0.0.0")
        self.assertEqual(args.port, 8080)

    def test_serve_command_accepts_token(self):
        """Test serve command accepts an auth token."""
        from cc_branch.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["serve", "--token", "secret-token"])
        self.assertEqual(args.token, "secret-token")

    def test_loopback_host_detection(self):
        """Public bind addresses should be distinguishable from local-only hosts."""
        from cc_branch.cli import _is_loopback_host

        self.assertTrue(_is_loopback_host("127.0.0.1"))
        self.assertTrue(_is_loopback_host("localhost"))
        self.assertTrue(_is_loopback_host("::1"))
        self.assertFalse(_is_loopback_host("0.0.0.0"))

    def test_serve_rejects_public_host_without_token(self):
        """Serving on a public bind address should require authentication."""
        from unittest.mock import patch

        from cc_branch.cli import main

        with patch("cc_branch.cli.WorkspaceContext") as context_cls, patch(
            "cc_branch.webui.server.start_server"
        ) as start_server:
            context = context_cls.return_value
            context.config_path = Path("/tmp/.cc-branch.yaml")
            context.state_path = Path("/tmp/.cc-branch.state.toml")
            context.state = object()
            context.load.return_value = (object(), object())

            result = main(["serve", "--host", "0.0.0.0"])

        self.assertEqual(result, 1)
        start_server.assert_not_called()

    def test_serve_passes_token_to_server(self):
        """Serve should pass the CLI token through to the Web UI server."""
        from unittest.mock import patch

        from cc_branch.cli import main

        with patch("cc_branch.cli.WorkspaceContext") as context_cls, patch(
            "cc_branch.webui.server.start_server"
        ) as start_server:
            context = context_cls.return_value
            context.config_path = Path("/tmp/.cc-branch.yaml")
            context.state_path = Path("/tmp/.cc-branch.state.toml")
            context.state = object()
            context.load.return_value = (object(), object())

            result = main(["serve", "--host", "0.0.0.0", "--token", "secret-token"])

        self.assertEqual(result, 0)
        start_server.assert_called_once_with(
            Path("/tmp/.cc-branch.yaml"),
            Path("/tmp/.cc-branch.state.toml"),
            host="0.0.0.0",
            port=8080,
            token="secret-token",
        )


class PackagingMetadataTests(unittest.TestCase):
    """Tests for packaging metadata needed by the Web UI."""

    def test_webui_assets_are_packaged(self):
        """Nested Vite assets must be included in wheels and source distributions."""
        root = Path(__file__).resolve().parents[1]
        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
        manifest = (root / "MANIFEST.in").read_text(encoding="utf-8")

        self.assertIn("webui/static/assets/*", pyproject)
        self.assertIn("agents.yaml", pyproject)
        self.assertIn("include cc_branch/agents.yaml", manifest)
        self.assertIn("recursive-include cc_branch/webui/static *", manifest)
        self.assertIn("prune cc_branch/webui/static/__pycache__", manifest)
        self.assertIn("global-exclude *.py[cod]", manifest)


if __name__ == "__main__":
    unittest.main()
