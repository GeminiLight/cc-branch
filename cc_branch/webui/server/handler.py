"""HTTP handler and server startup for the Web UI."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from ...application.results import ActionResult
from ...config import (
    project_dir_for_config,
    resolve_config_selection,
    resolve_state_path,
)
from . import api
from .auth import (
    auth_cookie_header,
    check_auth,
    cors_origin,
    is_loopback_host,
    origin_is_allowed,
    query_token_is_valid,
    request_origin_allowed,
)
from .static import canonical_static_path, read_static_bytes, read_static_file
from .terminal import _cli_command  # noqa: F401  # public patch point for action tests

_CLIENT_DISCONNECT_ERRORS = (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)


class WebUIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for cc-branch Web UI."""

    def __init__(
        self,
        config_path: Path,
        state_path: Path,
        *args: Any,
        token: str | None = None,
        **kwargs: Any,
    ):
        self.config_path = config_path
        self.state_path = state_path
        self._token = token
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default request logging."""
        pass

    def _send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data).encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self._set_cors()
            self.end_headers()
            self.wfile.write(payload)
        except _CLIENT_DISCONNECT_ERRORS:
            return

    def _send_action_result(self, result: ActionResult, *, message: str | None = None) -> bool:
        if not result.ok:
            self._send_json({
                "success": False,
                "error": result.message,
                "code": result.code,
                "changed_targets": list(result.changed_targets),
                "warnings": list(result.warnings),
            }, 400)
            return False
        self._send_json({
            "success": True,
            "code": result.code,
            "message": message or result.message,
            "changed_targets": list(result.changed_targets),
            "warnings": list(result.warnings),
        })
        return True

    def _serve_text(
        self,
        content: str,
        content_type: str = "text/html",
        extra_headers: dict[str, str] | None = None,
        status: int = 200,
    ) -> None:
        payload = content.encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            for name, value in (extra_headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)
        except _CLIENT_DISCONNECT_ERRORS:
            return

    def _serve_static(self, filename: str) -> None:
        try:
            content = read_static_bytes(filename)
        except FileNotFoundError:
            self.send_error(404)
            return
        except OSError:
            self.send_error(500)
            return

        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        try:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "public, max-age=31536000, immutable" if filename.startswith("assets/") else "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except _CLIENT_DISCONNECT_ERRORS:
            return

    def _cors_origin(self) -> str:
        return cors_origin(
            origin=self.headers.get("Origin"),
            host_header=self.headers.get("Host"),
            client_host=self.client_address[0],
            client_port=self.client_address[1],
            token=self._token,
        )

    @staticmethod
    def _is_loopback_host(host: str | None) -> bool:
        return is_loopback_host(host)

    def _origin_is_allowed(self, origin: str) -> bool:
        return origin_is_allowed(origin, host_header=self.headers.get("Host"), token=self._token) or bool(self._token and self._check_auth())

    def _request_origin_allowed(self) -> bool:
        return request_origin_allowed(
            self.headers.get("Origin"),
            host_header=self.headers.get("Host"),
            token=self._token,
        )

    def _set_cors(self) -> None:
        origin = self.headers.get("Origin")
        if origin and not self._origin_is_allowed(origin):
            return
        self.send_header("Access-Control-Allow-Origin", origin or self._cors_origin())
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _check_auth(self) -> bool:
        return check_auth(
            self._token,
            authorization=self.headers.get("Authorization", ""),
            cookie_header=self.headers.get("Cookie", ""),
        )

    def _require_auth(self) -> bool:
        if self._check_auth():
            return True
        self._send_json({"error": "Unauthorized"}, 401)
        return False

    def _query_token_is_valid(self) -> bool:
        return query_token_is_valid(self._token, self._get_query())

    def _auth_cookie_header(self) -> str:
        return auth_cookie_header(self._token)

    def _get_query(self) -> dict[str, list[str]]:
        """Parse query string from the current request path."""
        parsed = urlparse(self.path)
        return parse_qs(parsed.query)

    def _get_project_path(self) -> Path | None:
        """Return overridden project directory from query string, or None."""
        query = self._get_query()
        paths = query.get("project_path", [])
        if paths and paths[0]:
            return Path(paths[0]).expanduser()
        return None

    def _get_config_selection(self) -> str | None:
        """Return selected config from query string, or None."""
        query = self._get_query()
        paths = query.get("config_path", [])
        if paths and paths[0]:
            return paths[0]
        return None

    def _resolve_paths(self) -> tuple[Path, Path]:
        """Return (config_path, state_path) for the current request."""
        project_dir = self._get_project_path()
        config_selection = self._get_config_selection()
        if project_dir or config_selection:
            base_project = project_dir or project_dir_for_config(self.config_path)
            config_path = resolve_config_selection(
                base_project,
                config_selection,
                restrict_to_project=True,
            )
            return config_path, resolve_state_path(project_dir_for_config(config_path), config_path)
        return self.config_path, self.state_path

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._serve_index()
        elif (
            path.startswith("/static/")
            or path.startswith("/assets/")
            or path in {"/favicon.png", "/favicon.svg", "/icons.svg"}
        ):
            filename = canonical_static_path(self.path)
            if filename is None:
                self.send_error(403)
                return
            self._serve_static(filename)
        elif path == "/api/status":
            if self._require_auth():
                api.api_status(self)
        elif path == "/api/config":
            if self._require_auth():
                api.api_config(self)
        elif path == "/api/configs":
            if self._require_auth():
                api.api_configs(self)
        elif path == "/api/doctor":
            if self._require_auth():
                api.api_doctor(self)
        elif path == "/api/profiles":
            if self._require_auth():
                api.api_profiles(self)
        elif path == "/api/openers":
            if self._require_auth():
                api.api_openers(self)
        elif path == "/api/agents":
            if self._require_auth():
                api.api_agents(self)
        elif path == "/api/agents/global":
            if self._require_auth():
                api.api_global_agents(self)
        elif path == "/api/agent-sessions" and self._require_auth():
            api.api_agent_sessions(self)
        elif path == "/api/info":
            if self._require_auth():
                api.api_info(self)
        elif path == "/api/project/probe":
            if self._require_auth():
                api.api_project_probe(self)
        elif path == "/api/projects":
            if self._require_auth():
                api.api_projects(self)
        else:
            self.send_error(404)

    def _serve_index(self) -> None:
        try:
            if self._token and not self._check_auth():
                if self._query_token_is_valid():
                    self.send_response(303)
                    self.send_header("Location", "/")
                    self.send_header("Set-Cookie", self._auth_cookie_header())
                    self.send_header("Referrer-Policy", "no-referrer")
                    self.end_headers()
                    return
                self._serve_text("Unauthorized", "text/plain; charset=utf-8", status=401)
                return
            html = read_static_file("index.html")
            self._serve_text(html, "text/html; charset=utf-8", {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        except Exception:
            self.send_error(500)

    def _route_post(self, path: str) -> None:
        """Route POST requests ignoring query string."""
        if path == "/api/action":
            if self._require_auth():
                api.api_action(self)
        elif path == "/api/init":
            if self._require_auth():
                api.api_init(self)
        elif path == "/api/config":
            if self._require_auth():
                api.api_save_config(self)
        elif path == "/api/configs/create":
            if self._require_auth():
                api.api_configs_create(self)
        elif path == "/api/configs/rename":
            if self._require_auth():
                api.api_configs_rename(self)
        elif path == "/api/configs/delete":
            if self._require_auth():
                api.api_configs_delete(self)
        elif path == "/api/agents/global":
            if self._require_auth():
                api.api_save_global_agents(self)
        elif path == "/api/project/pick-directory":
            if self._require_auth():
                api.api_project_pick_directory(self)
        elif path == "/api/projects/add":
            if self._require_auth():
                api.api_projects_add(self)
        elif path == "/api/projects/remove":
            if self._require_auth():
                api.api_projects_remove(self)
        elif path == "/api/projects/activate":
            if self._require_auth():
                api.api_projects_activate(self)
        elif path == "/api/projects/current":
            if self._require_auth():
                api.api_projects_current(self)
        elif path == "/api/projects/config":
            if self._require_auth():
                api.api_projects_config(self)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if not self._request_origin_allowed():
            self._send_json({"error": "Forbidden origin"}, 403)
            return
        parsed = urlparse(self.path)
        self._route_post(parsed.path)

    def do_OPTIONS(self) -> None:
        if not self._request_origin_allowed():
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(200)
        self._set_cors()
        self.end_headers()
def start_server(
    config_path: Path,
    state_path: Path,
    host: str = "127.0.0.1",
    port: int = 8080,
    token: str | None = None,
) -> None:
    """Start the web UI server."""
    from functools import partial
    handler = partial(WebUIHandler, config_path, state_path, token=token)
    server = HTTPServer((host, port), handler)
    print(f"Starting cc-branch Web UI at http://{host}:{port}")
    if token:
        print("Authentication enabled (token required for Web UI and API access)")
        print(f"Open once with: http://{host}:{port}/?token={token}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.shutdown()
