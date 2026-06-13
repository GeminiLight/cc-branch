"""Web UI API endpoint handlers.

Functions in this module receive the active ``WebUIHandler`` instance. Keeping
endpoint policy here lets ``handler.py`` stay focused on HTTP routing and
transport plumbing.
"""

from __future__ import annotations

import json
import os
import subprocess
from json import JSONDecodeError
from pathlib import Path

from ...app_state import ProjectIndexStore
from ...application.agent_bus import AgentBusStore
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
    set_window_enabled,
)
from ...application.diagnostics import get_diagnostic_bundle, get_doctor_payload
from ...application.global_agents import read_global_agents, save_global_agents
from ...application.global_openers import read_global_openers, save_global_openers
from ...application.remote_directory import list_remote_directories
from ...application.session_restore import restore_sessions_for_workspace
from ...application.ssh_config import discover_ssh_hosts
from ...application.system_paths import reveal_path
from ...application.agent_worktrees import (
    AgentWorktreeStore,
    cleanup_agent_worktree,
    finish_agent_worktree,
    setup_agent_worktree_for_workspace,
    worktree_status_for_agents,
)
from ...application.workspace_snapshots import (
    WorkspaceSnapshotStore,
    capture_snapshot_for_workspace,
    export_workspace_snapshot,
    import_workspace_snapshot,
    preview_workspace_snapshot_restore,
    restore_workspace_snapshot,
)
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


def _worktree_runner(command):
    from ...application.agent_worktrees import _run

    return _run(command)


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


def api_diagnostics_bundle(handler) -> None:
    try:
        config_path, state_path = handler._resolve_paths()
        port = int(getattr(handler.server, "server_port", 0) or 0)
        handler._send_json(get_diagnostic_bundle(config_path, state_path, backend_port=port))
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


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


def api_global_openers(handler) -> None:
    try:
        handler._send_json(read_global_openers().payload)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_save_global_openers(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        content = data.get("content")
        if content is None:
            handler._send_json({"error": "Missing 'content' field"}, 400)
            return

        result = save_global_openers(
            str(content),
            base_mtime=data.get("base_mtime"),
            base_content_hash=data.get("base_content_hash"),
        )
        if result.code == "global_openers_conflict":
            handler._send_json({"error": result.message, "code": result.code, **result.payload}, 409)
            return
        if result.code == "invalid_global_openers":
            handler._send_json({"error": result.message, "code": result.code, **result.payload}, 400)
            return
        handler._send_json({"success": True, **result.payload})
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
        query = handler._get_query()
        agent = query.get("agent", [None])[0]
        scope = query.get("scope", ["project"])[0] or "project"
        handler._send_json(agent_session_options(config_path, agent=agent, scope=scope).payload)
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_agent_bus(handler) -> None:
    try:
        query = handler._get_query()
        target = (query.get("target", [None])[0] or "").strip() or None
        limit_raw = (query.get("limit", ["100"])[0] or "100").strip()
        try:
            limit = max(1, min(500, int(limit_raw)))
        except ValueError:
            limit = 100
        store = AgentBusStore()
        handler._send_json({
            "events": store.events(target=target, limit=limit),
            "inbox": store.inbox(target=target, unread_only=True, limit=limit),
            "storage_path": str(store.path),
        })
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_agent_bus_read(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        target = str(data.get("target") or "").strip() or None
        event_id = str(data.get("event_id") or "").strip() or None
        receipt = AgentBusStore().mark_read(target=target, event_id=event_id)
        handler._send_json({
            "success": True,
            "code": "agent_inbox_marked_read",
            "message": f"Marked {receipt['count']} message(s) as read",
            "receipt": receipt,
        })
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_snapshots(handler) -> None:
    try:
        handler._send_json({"snapshots": WorkspaceSnapshotStore().list()})
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_snapshots_create(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        config_path, state_path = handler._resolve_paths()
        snapshot = capture_snapshot_for_workspace(
            config_path=config_path,
            state_path=state_path,
            name=str(data.get("name") or "").strip() or None,
            include_files=bool(data.get("include_files")),
        )
        handler._send_json(snapshot)
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_snapshots_restore(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        snapshot_id = str(data.get("id") or data.get("snapshot_id") or "").strip()
        if not snapshot_id:
            handler._send_json({"error": "Missing snapshot id"}, 400)
            return
        state_path = Path(str(data.get("state_path"))) if data.get("state_path") else None
        restore_files = data.get("restore_files")
        result = restore_workspace_snapshot(
            snapshot_id,
            state_path=state_path,
            dry_run=bool(data.get("dry_run")),
            restore_files=bool(restore_files) if restore_files is not None else None,
        )
        handler._send_json(result)
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_snapshots_preview(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        snapshot_id = str(data.get("id") or data.get("snapshot_id") or "").strip()
        if not snapshot_id:
            handler._send_json({"error": "Missing snapshot id"}, 400)
            return
        state_path = Path(str(data.get("state_path"))) if data.get("state_path") else None
        handler._send_json(preview_workspace_snapshot_restore(snapshot_id, state_path=state_path))
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_snapshots_export(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        snapshot_id = str(data.get("id") or data.get("snapshot_id") or "").strip()
        output = str(data.get("path") or data.get("output") or "").strip()
        if not snapshot_id:
            handler._send_json({"error": "Missing snapshot id"}, 400)
            return
        if not output:
            handler._send_json({"error": "Missing output path"}, 400)
            return
        handler._send_json(export_workspace_snapshot(snapshot_id, Path(output)))
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_snapshots_import(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        path = str(data.get("path") or "").strip()
        if not path:
            handler._send_json({"error": "Missing path"}, 400)
            return
        name = str(data.get("name") or "").strip() or None
        handler._send_json(import_workspace_snapshot(Path(path), name=name))
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_worktrees(handler) -> None:
    try:
        handler._send_json({"worktrees": worktree_status_for_agents(runner=_worktree_runner)})
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_worktrees_setup(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        config_path, state_path = handler._resolve_paths()
        record = setup_agent_worktree_for_workspace(
            config_path,
            state_path,
            str(data.get("target") or ""),
            path=Path(str(data["path"])) if data.get("path") else None,
            branch=str(data.get("branch") or "").strip() or None,
            base_ref=str(data.get("base") or "HEAD"),
            copy_ignored=data.get("copy") or [],
            symlink_ignored=data.get("symlink") or [],
            setup_hook=str(data.get("setup_hook") or "").strip() or None,
            runner=_worktree_runner,
        )
        handler._send_json(record)
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_worktrees_cleanup(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        target = str(data.get("target") or "").strip()
        if not target:
            handler._send_json({"error": "Missing target"}, 400)
            return
        record = cleanup_agent_worktree(target, runner=_worktree_runner, force=bool(data.get("force")))
        handler._send_json(record)
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_worktrees_finish(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        target = str(data.get("target") or "").strip()
        if not target:
            handler._send_json({"error": "Missing target"}, 400)
            return
        record = finish_agent_worktree(target, runner=_worktree_runner)
        handler._send_json(record)
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
        payload = {
            "port": int(getattr(handler.server, "server_port", 0) or 0),
            "config_path": str(handler.config_path),
            "state_path": str(handler.state_path),
            "backend_source": os.environ.get("CC_BRANCH_BACKEND_SOURCE", "cli"),
            "backend_scope": os.environ.get("CC_BRANCH_BACKEND_SCOPE", "project"),
            "default_shell": default_shell_command(),
            "ssh_hosts": discover_ssh_hosts(),
        }
        desktop_metadata = {
            "desktop_version": os.environ.get("CC_BRANCH_DESKTOP_VERSION"),
            "desktop_platform": os.environ.get("CC_BRANCH_DESKTOP_PLATFORM"),
            "desktop_arch": os.environ.get("CC_BRANCH_DESKTOP_ARCH"),
        }
        payload.update(
            {
                key: value
                for key, value in desktop_metadata.items()
                if isinstance(value, str) and value.strip()
            }
        )
        handler._send_json(payload)
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


def api_remote_list_directories(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        remote = data.get("remote")
        if not isinstance(remote, dict):
            handler._send_json({"error": "Missing 'remote' field"}, 400)
            return
        handler._send_json(list_remote_directories(remote, data.get("path")))
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except subprocess.TimeoutExpired as error:
        handler._send_json({"error": str(error)}, 504)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_system_reveal(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        raw_path = str(data.get("path") or "").strip()
        if not raw_path:
            handler._send_json({"error": "Missing 'path' field"}, 400)
            return
        reveal_path(Path(raw_path))
        handler._send_json({"success": True, "path": raw_path})
    except FileNotFoundError as error:
        handler._send_json({"error": str(error)}, 404)
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
        remote = data.get("remote")
        if isinstance(remote, dict):
            agent = str(data.get("agent") or remote.get("agent") or "codex")
            payload = ProjectIndexStore().add_remote_project(remote, name=str(name) if name else None, agent=agent)
            handler._send_json(payload)
            return
        if not path:
            handler._send_json({"error": "Missing 'path' field"}, 400)
            return
        payload = ProjectIndexStore().add_project(path, name=str(name) if name else None)
        handler._send_json(payload)
    except ValueError as error:
        handler._send_json({"error": str(error)}, 400)
    except Exception as error:
        handler._send_json({"error": str(error)}, 500)


def api_projects_preview_remote(handler) -> None:
    try:
        data = _read_json_body(handler)
        remote = data.get("remote")
        if not isinstance(remote, dict):
            handler._send_json({"error": "Missing 'remote' field"}, 400)
            return
        name = data.get("name")
        agent = str(data.get("agent") or remote.get("agent") or "codex")
        payload = ProjectIndexStore().preview_remote_project(remote, name=str(name) if name else None, agent=agent)
        handler._send_json({"success": True, "dry_run": True, **payload})
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
        if os.environ.get("CC_BRANCH_BACKEND_SCOPE") == "app":
            handler._send_json(ProjectIndexStore().payload())
            return
        config_path, _state_path = handler._resolve_paths()
        project_dir = project_dir_for_config(config_path)
        payload = ProjectIndexStore().inject_current_project(
            str(project_dir),
            selected_config_path=str(config_path),
            activate_current=True,
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


def api_window_enabled(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        target = str(data.get("target") or "").strip()
        if not target:
            handler._send_json({"error": "Missing 'target' field"}, 400)
            return
        if "enabled" not in data:
            handler._send_json({"error": "Missing 'enabled' field"}, 400)
            return
        config_path, state_path = handler._resolve_paths()
        result = set_window_enabled(config_path, state_path, target, bool(data.get("enabled")))
        if not result.ok:
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
            message=data.get("message"),
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


def api_session_restore(handler) -> None:
    if not handler._require_auth():
        return

    try:
        data = _read_json_body(handler)
        config_path, state_path = handler._resolve_paths()
        limit_raw = data.get("limit") or 20
        try:
            limit = int(limit_raw)
        except (TypeError, ValueError):
            limit = 20
        result = restore_sessions_for_workspace(
            config_path,
            state_path,
            target=str(data.get("target") or "").strip() or None,
            agent=str(data.get("agent") or "").strip() or None,
            dry_run=bool(data.get("dry_run")),
            force=bool(data.get("force")),
            limit=limit,
            session_id=str(data.get("session_id") or "").strip() or None,
            session_scope=str(data.get("session_scope") or "project").strip() or "project",
        )
        handler._send_action_result(result)
    except ValueError as error:
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
