"""Section-level raw config validation."""

from __future__ import annotations

from typing import Any

from ...models import Issue
from .constants import (
    AGENT_FIELDS,
    AGENT_STRING_FIELDS,
    CREATE_MODES,
    LABEL_MODES,
    OPENER_FIELDS,
    OPENER_STRING_FIELDS,
    RESUME_MODES,
    RUNTIMES,
    SLOT_FIELDS,
    SLOT_STRING_FIELDS,
    WINDOW_FIELDS,
    WINDOW_STRING_FIELDS,
)
from .issues import duplicate_issue, invalid_type, missing_launch_command, unknown_field
from .validators import (
    duplicated_names,
    enum_issue,
    env_issues,
    mapping,
    name_or_fallback,
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


def window_issues(raw_windows: Any, slot_name: str) -> list[Issue]:
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


def slot_issues(raw_slots: Any) -> list[Issue]:
    issues: list[Issue] = []
    if raw_slots is None:
        return issues
    if not isinstance(raw_slots, list):
        return [invalid_type("slots", raw_slots, "config", "list")]
    valid_slots = [slot for slot in raw_slots if isinstance(slot, dict)]
    duplicate_slots = duplicated_names(valid_slots)
    for name in sorted(duplicate_slots):
        issues.append(duplicate_issue("duplicate_slot", name, f"slot:{name}", "slot"))
    for index, raw_slot in enumerate(raw_slots):
        if not isinstance(raw_slot, dict):
            continue
        slot_name = name_or_fallback(raw_slot, f"slot[{index}]")
        target = f"slot:{slot_name}"
        issues.extend(unknown_fields(raw_slot, SLOT_FIELDS, target))
        issues.extend(string_type_issues(raw_slot, SLOT_STRING_FIELDS, target))
        issues.extend(env_issues(raw_slot, target))
        issue = enum_issue(raw_slot, "runtime", RUNTIMES, target)
        if issue is not None:
            issues.append(issue)
        raw_windows = raw_slot.get("windows")
        if raw_windows is not None:
            issues.extend(window_issues(raw_windows, slot_name))
        elif raw_slot.get("command") is None and raw_slot.get("agent") is None:
            issues.append(missing_launch_command(f"window:{slot_name}:main"))
    return issues
