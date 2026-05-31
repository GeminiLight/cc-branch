"""Current workspace schema guards."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

CURRENT_CONFIG_SCHEMA_VERSION = 2
CURRENT_STATE_SCHEMA_VERSION = 1


def _int_version(data: dict[str, Any], *, schema_name: str) -> int:
    try:
        return int(data["version"])
    except KeyError as exc:
        raise ValueError(f"{schema_name} schema version is required") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{schema_name} schema version must be an integer") from exc


def require_current_config_schema(data: dict[str, Any]) -> dict[str, Any]:
    """Return config data only when it already matches the current public schema."""
    version = _int_version(data, schema_name="config")
    if version != CURRENT_CONFIG_SCHEMA_VERSION:
        raise ValueError(
            f"config schema version {version} is unsupported; expected {CURRENT_CONFIG_SCHEMA_VERSION}"
        )
    if "slots" in data:
        raise ValueError("unsupported config field 'slots'; use 'tabs' with 'panes'")
    if "default_opener" in data:
        raise ValueError("unsupported config field 'default_opener'; use 'openWith'")
    for tab in data.get("tabs") or []:
        if not isinstance(tab, dict):
            continue
        if "runtime" in tab:
            raise ValueError("unsupported tab field 'runtime'; use 'layoutBackend'")
        if "windows" in tab:
            raise ValueError("unsupported tab field 'windows'; use 'panes'")
        for pane in tab.get("panes") or []:
            if not isinstance(pane, dict):
                continue
            if "runtime" in pane:
                raise ValueError("unsupported pane field 'runtime'; use 'layoutBackend'")
            if "session_id" in pane:
                raise ValueError("unsupported pane field 'session_id'; use 'session'")
            for window in pane.get("windows") or []:
                if isinstance(window, dict) and "session_id" in window:
                    raise ValueError("unsupported window field 'session_id'; use 'session'")
    return deepcopy(data)


def require_current_state_schema(data: dict[str, Any]) -> dict[str, Any]:
    """Return state data only when it already matches the current state schema."""
    if "version" not in data and not data:
        return {"version": CURRENT_STATE_SCHEMA_VERSION, "windows": {}, "slots": {}}
    version = _int_version(data, schema_name="state")
    if version != CURRENT_STATE_SCHEMA_VERSION:
        raise ValueError(
            f"state schema version {version} is unsupported; expected {CURRENT_STATE_SCHEMA_VERSION}"
        )
    return deepcopy(data)


def schema_summary() -> dict[str, dict[str, int]]:
    """Return current schema metadata for diagnostics."""
    return {
        "config": {"current_version": CURRENT_CONFIG_SCHEMA_VERSION},
        "state": {"current_version": CURRENT_STATE_SCHEMA_VERSION},
    }
