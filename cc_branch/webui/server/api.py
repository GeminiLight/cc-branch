"""Web UI API endpoint handlers.

Functions in this module receive the active ``WebUIHandler`` instance. Keeping
endpoint policy here lets ``handler.py`` stay focused on HTTP routing and
transport plumbing.
"""

from __future__ import annotations

import json

from ...application.config_workflows import (
    agent_options,
    initialize_workspace,
    opener_options,
    probe_project,
    profile_options,
    read_workspace_config,
    save_workspace_config,
)
from ...config import project_dir_for_config
from ...application.workspace_actions import execute_workspace_action
from ...application.workspace_status import get_workspace_status
from ...application.diagnostics import get_doctor_payload
from ...openers import OpenerError
from ...runtime.backends import get_backend
from .terminal import _slot_exists


def api_status(handler) -> None:
    try:
        config_path, state_path = handler._resolve_paths()
        result = get_workspace_status(
            config_path,
            state_path,
            session_exists=_slot_exists,
            window_exists=lambda session, window: get_backend().has_window(session, window),
        )
        handler._send_json(result.payload)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_config(handler) -> None:
    try:
        config_path, state_path = handler._resolve_paths()
        result = read_workspace_config(config_path, state_path)
        handler._send_json(result.payload)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_doctor(handler) -> None:
    try:
        config_path, state_path = handler._resolve_paths()
        result = get_doctor_payload(config_path, state_path)
        handler._send_json(result.payload)
    except Exception as error:
        handler._send_json({"status": "invalid_config", "report": str(error), "error": str(error)})


def api_profiles(handler) -> None:
    try:
        handler._send_json(profile_options().payload)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_openers(handler) -> None:
    try:
        config_path, _state_path = handler._resolve_paths()
        handler._send_json(opener_options(config_path).payload)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_agents(handler) -> None:
    try:
        config_path, _state_path = handler._resolve_paths()
        handler._send_json(agent_options(config_path).payload)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_info(handler) -> None:
    try:
        handler._send_json({
            "port": 8080,
            "config_path": str(handler.config_path),
            "state_path": str(handler.state_path),
        })
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_project_probe(handler) -> None:
    try:
        project_dir = handler._get_project_path() or project_dir_for_config(handler.config_path)
        result = probe_project(project_dir)
        handler._send_json(result.payload)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_init(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        profile = data.get("profile", "solo-dev")
        bootstrap_sessions = data.get("bootstrap_sessions", True)
        config_path, _state_path = handler._resolve_paths()

        result = initialize_workspace(
            project_dir_for_config(config_path),
            profile=profile,
            bootstrap_sessions=bootstrap_sessions,
        )
        handler._send_json({"success": True, **result.payload})
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_save_config(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        content = data.get("content")
        if content is None:
            handler._send_json({"error": "Missing 'content' field"}, 400)
            return

        config_path, state_path = handler._resolve_paths()
        result = save_workspace_config(
            config_path,
            state_path,
            content,
            base_mtime=data.get("base_mtime"),
            base_content_hash=data.get("base_content_hash"),
        )
        if result.code == "config_conflict":
            handler._send_json({"error": result.message, "code": result.code, **result.payload}, 409)
            return
        if result.code == "invalid_config":
            handler._send_json({"error": result.message, "code": result.code, **result.payload}, 400)
            return
        handler._send_json({"success": True, **result.payload})
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_action(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        result = execute_workspace_action(
            *handler._resolve_paths(),
            action=data.get("action"),
            target=data.get("target"),
            opener=data.get("opener") or "auto-terminal",
            intent=data.get("intent"),
            stop_removed=data.get("stop_removed") is True,
            cli=_handler_cli_command(),
        )
        handler._send_action_result(result)
    except OpenerError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def _read_json_body(handler) -> dict:
    content_length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(content_length).decode()
    return json.loads(body) if body else {}


def _handler_cli_command() -> str:
    import cc_branch.webui.server.handler as handler_module

    return handler_module._cli_command()
