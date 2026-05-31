"""Section-level raw config validation."""

from __future__ import annotations

from typing import Any

from ...models import Issue
from .constants import (
    AGENT_FIELDS,
    AGENT_STRING_FIELDS,
    CREATE_MODES,
    DEFAULTS_FIELDS,
    DEFAULTS_STRING_FIELDS,
    LABEL_MODES,
    LAYOUT_BACKENDS,
    OPENER_FIELDS,
    OPENER_STRING_FIELDS,
    PANE_FIELDS,
    PANE_STRING_FIELDS,
    REMOTE_FIELDS,
    REMOTE_STRING_FIELDS,
    RESUME_MODES,
    TAB_FIELDS,
    TAB_STRING_FIELDS,
    WINDOW_FIELDS,
    WINDOW_STRING_FIELDS,
)
from .issues import duplicate_issue, invalid_type, missing_launch_command, unknown_field
from .validators import (
    duplicated_names,
    empty_name_issue,
    enum_issue,
    env_issues,
    mapping,
    name_or_fallback,
    reserved_name_separator_issue,
    string_type_issues,
    unknown_fields,
)


def agent_issues(raw_agents: Any) -> list[Issue]:
    issues: list[Issue] = []
    if raw_agents is None:
        return issues
    if not isinstance(raw_agents, dict):
        return [invalid_type("agents", raw_agents, "config", "mapping")]
    for name, raw_agent in raw_agents.items():
        if not isinstance(raw_agent, dict):
            continue
        target = f"agent:{name}"
        issues.extend(unknown_fields(raw_agent, AGENT_FIELDS, target))
        issues.extend(string_type_issues(raw_agent, AGENT_STRING_FIELDS, target))
        for field, allowed in (
            ("resume_mode", RESUME_MODES),
            ("create_mode", CREATE_MODES),
            ("label_mode", LABEL_MODES),
        ):
            issue = enum_issue(raw_agent, field, allowed, target)
            if issue is not None:
                issues.append(issue)
    return issues


def opener_issues(raw_openers: Any) -> list[Issue]:
    issues: list[Issue] = []
    if raw_openers is None:
        return issues
    if not isinstance(raw_openers, dict):
        return [invalid_type("openers", raw_openers, "config", "mapping")]
    openers = raw_openers
    if "items" in openers or "default" in openers:
        for field in sorted(set(openers) - {"items", "default"}):
            issues.append(unknown_field(field, "openers"))
        openers = mapping(openers.get("items"))
    for name, raw_opener in openers.items():
        if isinstance(raw_opener, dict):
            issues.extend(unknown_fields(raw_opener, OPENER_FIELDS, f"opener:{name}"))
            issues.extend(string_type_issues(raw_opener, OPENER_STRING_FIELDS, f"opener:{name}"))
    return issues


def defaults_issues(raw_defaults: Any) -> list[Issue]:
    if raw_defaults is None:
        return []
    if not isinstance(raw_defaults, dict):
        return [invalid_type("defaults", raw_defaults, "config", "mapping")]
    issues: list[Issue] = []
    issues.extend(unknown_fields(raw_defaults, DEFAULTS_FIELDS, "defaults"))
    if raw_defaults.get("shell") is not None and not isinstance(raw_defaults.get("shell"), (str, dict)):
        issues.append(invalid_type("shell", raw_defaults.get("shell"), "defaults", "string or mapping"))
    elif isinstance(raw_defaults.get("shell"), str):
        issues.extend(string_type_issues(raw_defaults, DEFAULTS_STRING_FIELDS, "defaults"))
    return issues


def shell_issues(data: dict, target: str) -> list[Issue]:
    raw_shell = data.get("shell")
    if raw_shell is None:
        return []
    if not isinstance(raw_shell, (str, dict)):
        return [invalid_type("shell", raw_shell, target, "string or mapping")]
    return []


def remote_issues(raw_remote: Any, target: str, *, require_host: bool = True) -> list[Issue]:
    if raw_remote is None:
        return []
    if raw_remote is False:
        return []
    if isinstance(raw_remote, str):
        if raw_remote.strip():
            return []
        return [invalid_type("remote", raw_remote, target, "non-empty string or mapping")]
    if not isinstance(raw_remote, dict):
        return [invalid_type("remote", raw_remote, target, "string or mapping")]

    issues: list[Issue] = []
    issues.extend(unknown_fields(raw_remote, REMOTE_FIELDS, f"{target}.remote"))
    issues.extend(string_type_issues(raw_remote, REMOTE_STRING_FIELDS, f"{target}.remote"))
    if require_host and not str(raw_remote.get("host") or "").strip():
        issues.append(invalid_type("host", raw_remote.get("host"), f"{target}.remote", "non-empty string"))
    raw_port = raw_remote.get("port")
    if raw_port is not None:
        try:
            port = int(raw_port)
        except (TypeError, ValueError):
            issues.append(invalid_type("port", raw_port, f"{target}.remote", "integer"))
        else:
            if port <= 0 or port > 65535:
                issues.append(invalid_type("port", raw_port, f"{target}.remote", "1-65535"))
    raw_args = raw_remote.get("args")
    if raw_args is not None and not (
        isinstance(raw_args, list)
        and all(isinstance(arg, str) for arg in raw_args)
    ):
        issues.append(invalid_type("args", raw_args, f"{target}.remote", "list of strings"))
    raw_options = raw_remote.get("options")
    if raw_options is not None and not isinstance(raw_options, dict):
        issues.append(invalid_type("options", raw_options, f"{target}.remote", "mapping"))
    return issues


def window_issues(raw_windows: Any, slot_name: str, *, inherited_remote: bool = False) -> list[Issue]:
    issues: list[Issue] = []
    if raw_windows is None:
        return issues
    if not isinstance(raw_windows, list):
        return [invalid_type("windows", raw_windows, f"slot:{slot_name}", "list")]
    valid_windows = [window for window in raw_windows if isinstance(window, dict)]
    duplicate_windows = duplicated_names(valid_windows)
    for name in sorted(duplicate_windows):
        issues.append(duplicate_issue("duplicate_window", name, f"window:{slot_name}:{name}", "window"))
    for index, raw_window in enumerate(raw_windows):
        if not isinstance(raw_window, dict):
            continue
        window_name = name_or_fallback(raw_window, f"window[{index}]")
        target = f"window:{slot_name}:{window_name}"
        issues.extend(unknown_fields(raw_window, WINDOW_FIELDS, target))
        issues.extend(string_type_issues(raw_window, WINDOW_STRING_FIELDS, target))
        issues.extend(shell_issues(raw_window, target))
        issues.extend(remote_issues(raw_window.get("remote"), target, require_host=not inherited_remote))
        issue = empty_name_issue(raw_window, target, "window")
        if issue is not None:
            issues.append(issue)
        issue = reserved_name_separator_issue(raw_window, target, "window")
        if issue is not None:
            issues.append(issue)
        issues.extend(env_issues(raw_window, target))
        if raw_window.get("command") is None and raw_window.get("agent") is None:
            issues.append(missing_launch_command(target))
        for field, allowed in (
            ("resume_mode", RESUME_MODES),
            ("create_mode", CREATE_MODES),
            ("label_mode", LABEL_MODES),
        ):
            issue = enum_issue(raw_window, field, allowed, target)
            if issue is not None:
                issues.append(issue)
    return issues


def pane_issues(raw_panes: Any, tab_name: str, *, inherited_remote: bool = False) -> list[Issue]:
    issues: list[Issue] = []
    if raw_panes is None:
        return issues
    if not isinstance(raw_panes, list):
        return [invalid_type("panes", raw_panes, f"tab:{tab_name}", "list")]
    valid_panes = [pane for pane in raw_panes if isinstance(pane, dict)]
    duplicate_panes = duplicated_names(valid_panes)
    for name in sorted(duplicate_panes):
        issues.append(duplicate_issue("duplicate_pane", name, f"pane:{tab_name}:{name}", "pane"))
    for index, raw_pane in enumerate(raw_panes):
        if not isinstance(raw_pane, dict):
            continue
        pane_name = name_or_fallback(raw_pane, f"pane[{index}]")
        target = f"pane:{tab_name}:{pane_name}"
        issues.extend(unknown_fields(raw_pane, PANE_FIELDS, target))
        issues.extend(string_type_issues(raw_pane, PANE_STRING_FIELDS, target))
        issues.extend(shell_issues(raw_pane, target))
        pane_has_remote_host = _remote_has_host(raw_pane.get("remote"))
        issues.extend(remote_issues(raw_pane.get("remote"), target, require_host=not inherited_remote))
        issue = empty_name_issue(raw_pane, target, "pane")
        if issue is not None:
            issues.append(issue)
        issue = reserved_name_separator_issue(raw_pane, target, "pane")
        if issue is not None:
            issues.append(issue)
        issues.extend(env_issues(raw_pane, target))
        issue = enum_issue(raw_pane, "layoutBackend", LAYOUT_BACKENDS, target)
        if issue is not None:
            issues.append(issue)
        for field, allowed in (
            ("resume_mode", RESUME_MODES),
            ("create_mode", CREATE_MODES),
            ("label_mode", LABEL_MODES),
        ):
            issue = enum_issue(raw_pane, field, allowed, target)
            if issue is not None:
                issues.append(issue)

        raw_windows = raw_pane.get("windows")
        if raw_windows is not None:
            issues.extend(window_issues(raw_windows, pane_name, inherited_remote=inherited_remote or pane_has_remote_host))
            if isinstance(raw_windows, list) and not raw_windows and raw_pane.get("command") is None and raw_pane.get("agent") is None:
                issues.append(missing_launch_command(target))
        elif raw_pane.get("command") is None and raw_pane.get("agent") is None:
            issues.append(missing_launch_command(target))
    return issues


def tab_issues(raw_tabs: Any) -> list[Issue]:
    issues: list[Issue] = []
    if raw_tabs is None:
        return issues
    if not isinstance(raw_tabs, list):
        return [invalid_type("tabs", raw_tabs, "config", "list")]
    valid_tabs = [tab for tab in raw_tabs if isinstance(tab, dict)]
    duplicate_tabs = duplicated_names(valid_tabs)
    for name in sorted(duplicate_tabs):
        issues.append(duplicate_issue("duplicate_tab", name, f"tab:{name}", "tab"))
    for index, raw_tab in enumerate(raw_tabs):
        if not isinstance(raw_tab, dict):
            continue
        tab_name = name_or_fallback(raw_tab, f"tab[{index}]")
        target = f"tab:{tab_name}"
        issues.extend(unknown_fields(raw_tab, TAB_FIELDS, target))
        issues.extend(string_type_issues(raw_tab, TAB_STRING_FIELDS, target))
        tab_has_remote_host = _remote_has_host(raw_tab.get("remote"))
        issues.extend(remote_issues(raw_tab.get("remote"), target))
        issue = empty_name_issue(raw_tab, target, "tab")
        if issue is not None:
            issues.append(issue)
        issue = reserved_name_separator_issue(raw_tab, target, "tab")
        if issue is not None:
            issues.append(issue)
        issues.extend(env_issues(raw_tab, target))
        issue = enum_issue(raw_tab, "layoutBackend", LAYOUT_BACKENDS, target)
        if issue is not None:
            issues.append(issue)
        issues.extend(pane_issues(raw_tab.get("panes"), tab_name, inherited_remote=tab_has_remote_host))
    return issues


def _remote_has_host(raw_remote: Any) -> bool:
    if raw_remote is False:
        return False
    if isinstance(raw_remote, str):
        return bool(raw_remote.strip())
    if isinstance(raw_remote, dict):
        return bool(str(raw_remote.get("host") or "").strip())
    return False
