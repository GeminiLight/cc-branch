"""Application workflows for workspace configuration files."""

from __future__ import annotations

from ..config_validation import collect_config_issues
from ..diagnostics import get_doctor_report, render_report
from ...agent_registry import load_agent_registry
from ...bootstrap import check_environment, initialize_workspace_files
from ...config import init_workspace as init_minimal_workspace
from ...config import (
    load_workspace,
    load_workspace_from_text,
    project_dir_for_config,
    resolve_config_path,
    resolve_state_path,
)
from ...openers import list_openers
from ...planner import plan_workspace
from ...profiles import get_available_profiles, get_profile_description
from ...state import load_state
from .initialization import (
    init_payload as _init_payload,
    initialize_minimal_workspace,
    initialize_workspace,
    initialize_workspace_from_environment,
    inspect_workspace_environment,
)
from .options import agent_options, agent_payload as _agent_payload, opener_options, profile_options
from .read import probe_project, read_workspace_config
from .save import save_workspace_config
from .versioning import (
    base_version_matches,
    base_version_matches as _base_version_matches,
    content_hash,
    file_version_payload,
    write_text_atomic,
    write_text_atomic as _write_text_atomic,
)

__all__ = [
    "agent_options",
    "base_version_matches",
    "check_environment",
    "collect_config_issues",
    "content_hash",
    "file_version_payload",
    "get_available_profiles",
    "get_doctor_report",
    "get_profile_description",
    "init_minimal_workspace",
    "initialize_minimal_workspace",
    "initialize_workspace",
    "initialize_workspace_files",
    "initialize_workspace_from_environment",
    "inspect_workspace_environment",
    "list_openers",
    "load_agent_registry",
    "load_state",
    "load_workspace",
    "load_workspace_from_text",
    "opener_options",
    "plan_workspace",
    "probe_project",
    "profile_options",
    "project_dir_for_config",
    "read_workspace_config",
    "render_report",
    "resolve_config_path",
    "resolve_state_path",
    "save_workspace_config",
    "write_text_atomic",
]
