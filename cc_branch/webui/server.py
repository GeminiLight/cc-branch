"""Web UI server for cc-branch.

A lightweight HTTP server providing a dashboard for visualizing
and managing cc-branch workspaces. Uses Python's built-in http.server
for zero additional dependencies.

Security notes:
- Static files are served from the ``static/`` package directory.
- API endpoints that mutate state require a bearer token when one is configured.
- CORS defaults to the request origin rather than ``*``.
"""

from __future__ import annotations

import ipaddress
import json
import mimetypes
import os
import secrets
import shlex
import shutil
import subprocess
import sys
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from ..bootstrap import check_environment, initialize_workspace_files
from ..config import load_workspace, resolve_config_path
from ..doctor import build_doctor_report
from ..openers import OpenerError, OpenIntent, _powershell_single_quote, list_openers, open_with
from ..planner import plan_workspace
from ..profiles import get_available_profiles, get_profile_description
from ..runtime import apply_workspace, ensure_slot, restart_workspace, stop_workspace
from ..state import load_state
from ..targets import parse_target


def _slot_exists(session_name: str) -> bool:
    """Check if a tmux session exists."""
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
            check=False,
            timeout=2,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _stop_slot(session_name: str) -> bool:
    """Stop a tmux session."""
    try:
        result = subprocess.run(
            ["tmux", "kill-session", "-t", session_name],
            capture_output=True,
            check=False,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _open_terminal(cwd: Path, command: str) -> None:
    """Open a system terminal and run a cc-branch command in *cwd*."""
    if command.endswith(" dashboard"):
        cli = command[: -len(" dashboard")]
        intent = OpenIntent(kind="workspace_dashboard")
    elif " attach " in command:
        cli, target_fragment = command.rsplit(" attach ", 1)
        try:
            target = shlex.split(target_fragment)[0]
        except (IndexError, ValueError):
            target = target_fragment
        intent = OpenIntent(kind="attach_target", target=target)
    else:
        # Backward-compatible helper for tests and older internal callers.
        from ..openers import _open_system_terminal

        _open_system_terminal(cwd, command)
        return
    open_with("auto-terminal", cwd=cwd, cli=cli, intent=intent)


def _cli_command() -> str:
    """Return a shell-safe cc-branch command for a new terminal process."""
    invoked = Path(sys.argv[0]).expanduser()
    if invoked.exists():
        resolved = str(invoked.resolve())
        if _uses_powershell_commands():
            return f"& {_powershell_single_quote(resolved)}"
        return shlex.quote(resolved)
    discovered = shutil.which("cc-branch")
    if discovered:
        if _uses_powershell_commands():
            return f"& {_powershell_single_quote(discovered)}"
        return shlex.quote(discovered)
    return "cc-branch"


def _uses_powershell_commands() -> bool:
    return os.name == "nt" or sys.platform.startswith("win")


def _read_static_file(filename: str) -> str:
    """Read a text static file bundled with the package."""
    from importlib.resources import files

    static_dir = files("cc_branch.webui.static")
    return (static_dir / filename).read_text(encoding="utf-8")


def _read_static_bytes(filename: str) -> bytes:
    """Read a static file bundled with the package as bytes."""
    from importlib.resources import files

    static_dir = files("cc_branch.webui.static")
    return (static_dir / filename).read_bytes()


def _canonical_static_path(request_path: str) -> str | None:
    """Return a safe canonical path for a static file request."""
    path = urlparse(request_path).path
    if path.startswith("/static/"):
        filename = path[8:]
    elif path.startswith("/assets/"):
        filename = "assets/" + path[8:]
    elif path in {"/favicon.png", "/favicon.svg", "/icons.svg"}:
        filename = path[1:]
    else:
        return None

    # Normalize to collapse redundant separators and catch traversal attempts.
    import os
    normalized = os.path.normpath(filename)
    if normalized.startswith("..") or normalized.startswith("/") or ".." in normalized.split(os.sep):
        return None

    return normalized


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

    def _send_json(self, data: dict, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._set_cors()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _serve_text(
        self,
        content: str,
        content_type: str = "text/html",
        extra_headers: dict[str, str] | None = None,
        status: int = 200,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(content.encode())

    def _serve_static(self, filename: str) -> None:
        try:
            content = _read_static_bytes(filename)
            content_type, _ = mimetypes.guess_type(filename)
            if content_type is None:
                content_type = "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404)
        except OSError:
            self.send_error(500)

    def _cors_origin(self) -> str:
        origin = self.headers.get("Origin")
        if origin and self._origin_is_allowed(origin):
            return origin
        host = self.headers.get("Host")
        if host:
            return f"http://{host}"
        return f"http://{self.client_address[0]}:{self.client_address[1]}"

    @staticmethod
    def _is_loopback_host(host: str | None) -> bool:
        if not host:
            return False
        normalized = host.strip().strip("[]").lower()
        if normalized == "localhost":
            return True
        try:
            return ipaddress.ip_address(normalized).is_loopback
        except ValueError:
            return False

    def _origin_is_allowed(self, origin: str) -> bool:
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False

        host_header = self.headers.get("Host")
        host_name = urlparse(f"http://{host_header}").hostname if host_header else None
        if self._is_loopback_host(parsed.hostname):
            return True

        # Token-protected public binds can be used from their own browser
        # origin. Tokenless local servers must not trust Host alone because DNS
        # rebinding can make an arbitrary site appear same-host.
        return bool(
            self._token
            and host_name
            and parsed.hostname.lower() == host_name.lower()
        )

    def _request_origin_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        return not origin or self._origin_is_allowed(origin)

    def _set_cors(self) -> None:
        origin = self.headers.get("Origin")
        if origin and not self._origin_is_allowed(origin):
            return
        self.send_header("Access-Control-Allow-Origin", self._cors_origin())
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _check_auth(self) -> bool:
        if not self._token:
            return True
        auth = self.headers.get("Authorization", "")
        if secrets.compare_digest(auth, f"Bearer {self._token}"):
            return True

        cookie = SimpleCookie()
        cookie.load(self.headers.get("Cookie", ""))
        token_cookie = cookie.get("cc_branch_token")
        if token_cookie is None:
            return False
        return secrets.compare_digest(token_cookie.value, self._token)

    def _require_auth(self) -> bool:
        if self._check_auth():
            return True
        self._send_json({"error": "Unauthorized"}, 401)
        return False

    def _query_token_is_valid(self) -> bool:
        if not self._token:
            return False
        query = self._get_query()
        tokens = query.get("token", [])
        return bool(tokens) and secrets.compare_digest(tokens[0], self._token)

    def _auth_cookie_header(self) -> str:
        """Build a safe Set-Cookie header for browser-originated Web UI actions."""
        cookie = SimpleCookie()
        cookie["cc_branch_token"] = self._token or ""
        cookie["cc_branch_token"]["path"] = "/"
        cookie["cc_branch_token"]["httponly"] = True
        cookie["cc_branch_token"]["samesite"] = "Strict"
        return cookie.output(header="").strip()

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

    def _resolve_paths(self) -> tuple[Path, Path]:
        """Return (config_path, state_path) for the current request."""
        project_dir = self._get_project_path()
        if project_dir:
            return resolve_config_path(project_dir), project_dir / ".cc-branch.state.toml"
        return self.config_path, self.state_path

    @staticmethod
    def _setup_payload(
        status: str,
        config_path: Path,
        state_path: Path,
        *,
        error: str | None = None,
    ) -> dict:
        """Return structured project setup state for config-less requests."""
        project_dir = config_path.parent
        payload = {
            "status": status,
            "project_path": str(project_dir),
            "config_path": str(config_path),
            "state_path": str(state_path),
            "project_name": project_dir.name or "project",
            "slots": [],
        }
        if error:
            payload["error"] = error
        return payload

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
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
                html = _read_static_file("index.html")
                headers = {"Referrer-Policy": "no-referrer"}
                self._serve_text(html, "text/html; charset=utf-8", headers)
            except Exception:
                self.send_error(500)
        elif (
            path.startswith("/static/")
            or path.startswith("/assets/")
            or path in {"/favicon.png", "/favicon.svg", "/icons.svg"}
        ):
            filename = _canonical_static_path(self.path)
            if filename is None:
                self.send_error(403)
                return
            self._serve_static(filename)
        elif path == "/api/status":
            if not self._require_auth():
                return
            self._api_status()
        elif path == "/api/config":
            if not self._require_auth():
                return
            self._api_config()
        elif path == "/api/doctor":
            if not self._require_auth():
                return
            self._api_doctor()
        elif path == "/api/profiles":
            if not self._require_auth():
                return
            self._api_profiles()
        elif path == "/api/openers":
            if not self._require_auth():
                return
            self._api_openers()
        elif path == "/api/info":
            if not self._require_auth():
                return
            self._api_info()
        elif path == "/api/project/probe":
            if not self._require_auth():
                return
            self._api_project_probe()
        else:
            self.send_error(404)

    def _route_post(self, path: str) -> None:
        """Route POST requests ignoring query string."""
        if path == "/api/action":
            self._api_action()
        elif path == "/api/init":
            self._api_init()
        elif path == "/api/config":
            self._api_save_config()
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

    def _api_status(self) -> None:
        try:
            config_path, state_path = self._resolve_paths()
            if not config_path.parent.exists():
                self._send_json(self._setup_payload("missing", config_path, state_path))
                return
            if not config_path.exists():
                self._send_json(self._setup_payload("needs_init", config_path, state_path))
                return

            workspace = load_workspace(config_path)
            state = load_state(state_path)
            plan = plan_workspace(workspace, state, False)

            slots: list[dict] = []
            for slot in plan.slots:
                session_name = slot.tmux_session
                is_running = _slot_exists(session_name)

                windows: list[dict] = []
                for wp in slot.windows:
                    windows.append({
                        "name": wp.name,
                        "agent": wp.agent,
                        "command": wp.launch_command,
                        "session_id": wp.resolved_session_id,
                        "label": wp.resolved_label,
                        "cwd": wp.cwd,
                    })

                slots.append({
                    "name": slot.name,
                    "backend": slot.backend,
                    "status": "running" if is_running else "stopped",
                    "session_name": session_name,
                    "windows": windows,
                })

            self.send_response(200)
            self._set_cors()
            self.end_headers()
            self.wfile.write(
                json.dumps({
                    "status": "ready",
                    "project": workspace.project,
                    "config_path": str(config_path),
                    "state_path": str(state_path),
                    "slots": slots,
                }).encode()
            )
        except Exception as e:
            try:
                config_path, state_path = self._resolve_paths()
                if config_path.exists():
                    self._send_json(
                        self._setup_payload(
                            "invalid_config",
                            config_path,
                            state_path,
                            error=str(e),
                        )
                    )
                    return
            except Exception:
                pass
            self._send_json({"error": str(e)}, 500)

    def _api_config(self) -> None:
        try:
            config_path, state_path = self._resolve_paths()
            if not config_path.parent.exists():
                self._send_json({
                    "status": "missing",
                    "content": "",
                    "path": str(config_path),
                    "project_path": str(config_path.parent),
                    "state_path": str(state_path),
                })
                return
            if not config_path.exists():
                self._send_json({
                    "status": "needs_init",
                    "content": "",
                    "path": str(config_path),
                    "project_path": str(config_path.parent),
                    "state_path": str(state_path),
                })
                return

            content = config_path.read_text()
            self.send_response(200)
            self._set_cors()
            self.end_headers()
            self.wfile.write(
                json.dumps({"status": "ready", "content": content, "path": str(config_path)}).encode()
            )
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _api_doctor(self) -> None:
        try:
            config_path, state_path = self._resolve_paths()
            if not config_path.parent.exists():
                self._send_json({
                    "status": "missing",
                    "report": f"Project directory does not exist: {config_path.parent}",
                })
                return
            if not config_path.exists():
                self._send_json({
                    "status": "needs_init",
                    "report": (
                        "No workspace config found. "
                        "Create one from a starter profile or open the YAML editor."
                    ),
                })
                return

            workspace = load_workspace(config_path)
            state = load_state(state_path)
            plan = plan_workspace(workspace, state, False)
            report = build_doctor_report(workspace, plan)
            self.send_response(200)
            self._set_cors()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ready", "report": report}).encode())
        except Exception as e:
            self._send_json({"status": "invalid_config", "report": str(e), "error": str(e)})

    def _api_profiles(self) -> None:
        try:
            profiles = [
                {"id": p, "description": get_profile_description(p)}
                for p in get_available_profiles()
            ]
            self.send_response(200)
            self._set_cors()
            self.end_headers()
            self.wfile.write(json.dumps({"profiles": profiles}).encode())
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _api_openers(self) -> None:
        try:
            self._send_json(list_openers())
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _api_info(self) -> None:
        try:
            self._send_json({
                "port": 8080,
                "config_path": str(self.config_path),
                "state_path": str(self.state_path),
            })
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _api_project_probe(self) -> None:
        try:
            project_dir = self._get_project_path()
            if project_dir is None:
                project_dir = self.config_path.parent

            path_exists = project_dir.exists() and project_dir.is_dir()
            config_path = resolve_config_path(project_dir)
            state_path = project_dir / ".cc-branch.state.toml"
            config_exists = path_exists and config_path.exists()
            state_exists = path_exists and state_path.exists()

            status = "missing"
            project_name = project_dir.name or "project"
            slot_count = 0
            if path_exists and not config_exists:
                status = "needs_init"
            elif config_exists:
                try:
                    workspace = load_workspace(config_path)
                    project_name = workspace.project or project_name
                    slot_count = len(workspace.slots)
                    status = "ready"
                except Exception:
                    status = "invalid_config"

            self._send_json({
                "path": str(project_dir),
                "path_exists": path_exists,
                "config_exists": config_exists,
                "state_exists": state_exists,
                "project_name": project_name,
                "slots": slot_count,
                "status": status,
            })
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _api_init(self) -> None:
        if not self._require_auth():
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            data = json.loads(body) if body else {}

            profile = data.get("profile", "solo-dev")
            bootstrap_sessions = data.get("bootstrap_sessions", True)
            config_path, _ = self._resolve_paths()
            cwd = config_path.parent

            env = check_environment(cwd)
            result = initialize_workspace_files(
                cwd,
                profile=profile,
                available_agents=env.available_agents,
                bootstrap_sessions_requested=bootstrap_sessions,
            )

            self._send_json({
                "success": True,
                "config_path": str(result.config_path),
                "state_path": str(result.state_path),
                "summary": {
                    "slots": result.config_summary.slots,
                    "windows": result.config_summary.windows,
                    "agents": result.config_summary.agents,
                },
                "agents_detected": env.available_agents,
                "gitignore_created": result.gitignore_created,
                "gitignore_updated": result.gitignore_updated,
            })
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _api_save_config(self) -> None:
        if not self._require_auth():
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            data = json.loads(body) if body else {}

            content = data.get("content")
            if content is None:
                self._send_json({"error": "Missing 'content' field"}, 400)
                return

            config_path, _ = self._resolve_paths()
            config_path.write_text(content, encoding="utf-8")
            self._send_json({"success": True, "path": str(config_path)})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _api_action(self) -> None:
        if not self._require_auth():
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            data = json.loads(body) if body else {}

            action = data.get("action")
            target = data.get("target")
            opener = data.get("opener") or "auto-terminal"
            intent_name = data.get("intent")

            config_path, state_path = self._resolve_paths()
            workspace = load_workspace(config_path)
            state = load_state(state_path)
            plan = plan_workspace(workspace, state, False)
            public_target = self._normalize_action_target(plan, target)

            if action == "stop":
                stop_workspace(workspace, plan, public_target)
                label = public_target or "workspace"
                self._send_json({"success": True, "message": f"Stopped {label}"})
            elif action == "restart":
                restart_workspace(workspace, plan, public_target, detach=True)
                label = public_target or "workspace"
                self._send_json({"success": True, "message": f"Restarted {label}"})
            elif action == "launch":
                if public_target:
                    slot = plan.get_slot(public_target)
                    if slot is None:
                        self._send_json({"error": f"Cannot launch target: {public_target}"}, 400)
                        return
                    ensure_slot(slot)
                    self._send_json({"success": True, "message": f"Launched {public_target}"})
                else:
                    apply_workspace(plan, detach=True)
                    self._send_json({"success": True, "message": "Launched workspace"})
            elif action == "open":
                cwd = config_path.parent
                cli = _cli_command()
                intent = self._resolve_open_intent(intent_name, public_target)
                if intent.kind == "attach_target" and public_target:
                    slot = self._resolve_attach_slot(plan, public_target)
                    if slot is None:
                        self._send_json({"error": f"Cannot open target: {public_target}"}, 400)
                        return
                    ensure_slot(slot)
                open_with(opener_id=opener, cwd=cwd, cli=cli, intent=intent)
                if intent.kind == "project_folder":
                    from ..openers import opener_label

                    self._send_json({"success": True, "message": f"Opened project in {opener_label(opener)}"})
                elif public_target:
                    self._send_json({"success": True, "message": f"Opened {public_target} in terminal"})
                else:
                    self._send_json({"success": True, "message": "Opened workspace dashboard in terminal"})
            else:
                self._send_json({"error": "Unknown or invalid action"}, 400)
        except OpenerError as e:
            self._send_json({"error": str(e)}, 400)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    @staticmethod
    def _resolve_open_intent(intent_name: str | None, public_target: str | None) -> OpenIntent:
        if intent_name is None:
            return OpenIntent(kind="attach_target", target=public_target) if public_target else OpenIntent(kind="workspace_dashboard")
        if intent_name == "project_folder":
            return OpenIntent(kind="project_folder")
        if intent_name == "workspace_dashboard":
            return OpenIntent(kind="workspace_dashboard")
        if intent_name == "attach_target":
            return OpenIntent(kind="attach_target", target=public_target)
        raise OpenerError(f"Unknown open intent: {intent_name}")

    @staticmethod
    def _resolve_attach_slot(plan, target: str):
        parsed = parse_target(target)
        slot = plan.get_slot(parsed.slot)
        if slot is None:
            return None
        if parsed.window is not None and all(window.name != parsed.window for window in slot.windows):
            return None
        return slot

    @staticmethod
    def _normalize_action_target(plan, target: str | None) -> str | None:
        """Accept public targets plus older tmux session names from previous UIs."""
        if not target:
            return None
        for slot in plan.slots:
            if target == slot.tmux_session:
                return slot.name
        return target


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
