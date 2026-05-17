"""Web UI API endpoint handlers.

Functions in this module receive the active ``WebUIHandler`` instance. Keeping
endpoint policy here lets ``handler.py`` stay focused on HTTP routing and
transport plumbing.
"""

from __future__ import annotations

import json
from json import JSONDecodeError

from ...app_state import ProjectIndexStore
from ...application.config_workflows import (
    agent_options,
    agent_session_options,
    create_workspace_config,
    delete_workspace_config,
    initialize_workspace,
    opener_options,
    probe_project,
    profile_options,
    read_workspace_config,
    rename_workspace_config,
    save_workspace_config,
)
from ...application.diagnostics import get_doctor_payload
from ...application.global_agents import read_global_agents, save_global_agents
from ...application.workspace_actions import execute_workspace_action
from ...application.workspace_status import get_workspace_status
from ...config import (
    config_options_payload,
    project_dir_for_config,
    resolve_config_path,
    resolve_config_selection,
)
from ...openers import OpenerError
from ...runtime.backends import get_backend
from ...runtime.shells import default_shell_command
from .directory_picker import pick_directory
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
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_config(handler) -> None:
    try:
        config_path, state_path = handler._resolve_paths()
        result = read_workspace_config(config_path, state_path)
        handler._send_json(result.payload)
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_configs(handler) -> None:
    try:
        config_path, _state_path = handler._resolve_paths()
        project_dir = project_dir_for_config(config_path)
        if handler._get_project_path() and not handler._get_config_selection():
            config_path = resolve_config_path(project_dir)
        handler._send_json(config_options_payload(project_dir, config_path))
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_configs_create(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        project_dir = handler._get_project_path() or project_dir_for_config(handler.config_path)
        name = str(data.get("name") or "").strip()
        source_value = str(data.get("source_config_path") or "").strip()
        source = resolve_config_path(project_dir) if not source_value else _resolve_project_config(project_dir, source_value)
        result = create_workspace_config(project_dir, name, source)
        handler._send_json({"success": True, **result.payload})
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_configs_rename(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        project_dir = handler._get_project_path() or project_dir_for_config(handler.config_path)
        config_path = _resolve_project_config(project_dir, str(data.get("config_path") or ""))
        name = str(data.get("name") or "").strip()
        result = rename_workspace_config(project_dir, config_path, name)
        handler._send_json({"success": True, **result.payload})
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_configs_delete(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        project_dir = handler._get_project_path() or project_dir_for_config(handler.config_path)
        config_path = _resolve_project_config(project_dir, str(data.get("config_path") or ""))
        result = delete_workspace_config(project_dir, config_path)
        handler._send_json({"success": True, **result.payload})
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_doctor(handler) -> None:
    try:
        config_path, state_path = handler._resolve_paths()
        result = get_doctor_payload(config_path, state_path)
        handler._send_json(result.payload)
    except ValueError as error:
        handler._send_json({"status": "missing", "report": str(error), "error": str(error)}, 400)
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
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_agents(handler) -> None:
    try:
        config_path, _state_path = handler._resolve_paths()
        handler._send_json(agent_options(config_path).payload)
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_agent_sessions(handler) -> None:
    try:
        config_path, _state_path = handler._resolve_paths()
        agent = handler._get_query().get("agent", [None])[0]
        handler._send_json(agent_session_options(config_path, agent=agent).payload)
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_global_agents(handler) -> None:
    try:
        handler._send_json(read_global_agents().payload)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_save_global_agents(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        content = data.get("content")
        if content is None:
            handler._send_json({"error": "Missing 'content' field"}, 400)
            return

        result = save_global_agents(
            str(content),
            base_mtime=data.get("base_mtime"),
            base_content_hash=data.get("base_content_hash"),
        )
        if result.code == "global_agents_conflict":
            handler._send_json({"error": result.message, "code": result.code, **result.payload}, 409)
            return
        if result.code == "invalid_global_agents":
            handler._send_json({"error": result.message, "code": result.code, **result.payload}, 400)
            return
        handler._send_json({"success": True, **result.payload})
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_info(handler) -> None:
    try:
        handler._send_json({
            "port": int(getattr(handler.server, "server_port", 0) or 0),
            "config_path": str(handler.config_path),
            "state_path": str(handler.state_path),
            "default_shell": default_shell_command(),
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


def api_project_pick_directory(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        picked = pick_directory(data.get("starting_dir"))
        handler._send_json({"path": picked})
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_projects(handler) -> None:
    try:
        handler._send_json(ProjectIndexStore().payload())
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_projects_add(handler) -> None:
    try:
        data = _read_json_body(handler)
        path = str(data.get("path") or "").strip()
        name = data.get("name")
        if not path:
            handler._send_json({"error": "Missing 'path' field"}, 400)
            return
        payload = ProjectIndexStore().add_project(path, name=str(name) if name else None)
        handler._send_json(payload)
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_projects_remove(handler) -> None:
    try:
        data = _read_json_body(handler)
        project_id = str(data.get("id") or "").strip()
        if not project_id:
            handler._send_json({"error": "Missing 'id' field"}, 400)
            return
        handler._send_json(ProjectIndexStore().remove_project(project_id))
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_projects_activate(handler) -> None:
    try:
        data = _read_json_body(handler)
        project_id = str(data.get("id") or "").strip()
        if not project_id:
            handler._send_json({"error": "Missing 'id' field"}, 400)
            return
        handler._send_json(ProjectIndexStore().activate_project(project_id))
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_projects_pin(handler) -> None:
    try:
        data = _read_json_body(handler)
        project_id = str(data.get("id") or "").strip()
        if not project_id:
            handler._send_json({"error": "Missing 'id' field"}, 400)
            return
        handler._send_json(ProjectIndexStore().set_project_pinned(project_id, bool(data.get("pinned"))))
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_projects_reorder(handler) -> None:
    try:
        data = _read_json_body(handler)
        project_id = str(data.get("id") or "").strip()
        before_raw = data.get("before_id")
        before_id = str(before_raw).strip() if before_raw is not None else None
        if not project_id:
            handler._send_json({"error": "Missing 'id' field"}, 400)
            return
        handler._send_json(ProjectIndexStore().reorder_project(project_id, before_id=before_id or None))
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_projects_current(handler) -> None:
    try:
        config_path, _state_path = handler._resolve_paths()
        project_dir = project_dir_for_config(config_path)
        payload = ProjectIndexStore().inject_current_project(
            str(project_dir),
            selected_config_path=str(config_path),
        )
        handler._send_json(payload)
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_projects_config(handler) -> None:
    try:
        data = _read_json_body(handler)
        project_path = str(data.get("project_path") or "").strip()
        config_path = str(data.get("config_path") or "").strip()
        if not project_path:
            handler._send_json({"error": "Missing 'project_path' field"}, 400)
            return
        if not config_path:
            handler._send_json({"error": "Missing 'config_path' field"}, 400)
            return
        payload = ProjectIndexStore().set_project_config(project_path, config_path)
        handler._send_json(payload)
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_init(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        profile = data.get("profile", "development")
        bootstrap_sessions = data.get("bootstrap_sessions", True)
        config_path, _state_path = handler._resolve_paths()

        result = initialize_workspace(
            project_dir_for_config(config_path),
            profile=profile,
            bootstrap_sessions=bootstrap_sessions,
        )
        handler._send_json({"success": True, **result.payload})
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
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
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
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
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except OpenerError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def _read_json_body(handler) -> dict:
    content_length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(content_length).decode()
    if not body:
        return {}
    try:
        data = json.loads(body)
    except JSONDecodeError as error:
        raise ValueError("Invalid JSON body") from error
    if not isinstance(data, dict):
        raise ValueError("Invalid JSON body")
    return data


def _resolve_project_config(project_dir, value: str):
    if not value.strip():
        raise ValueError("Missing 'config_path' field")
    return resolve_config_selection(project_dir, value, restrict_to_project=True)


def _handler_cli_command() -> str:
    import cc_branch.webui.server.handler as handler_module

    return handler_module._cli_command()
