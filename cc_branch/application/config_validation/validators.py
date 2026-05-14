"""Shared raw config validators."""

from __future__ import annotations

import re
from typing import Any

from ...models import Issue
from .issues import (
    empty_name,
    invalid_enum,
    invalid_env_key,
    invalid_type,
    reserved_name_separator,
    unknown_field,
)


def mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def unknown_fields(data: dict, allowed: set[str], target: str) -> list[Issue]:
    return [unknown_field(field, target) for field in sorted(set(data) - allowed)]


def enum_issue(data: dict, field: str, allowed: set[str], target: str) -> Issue | None:
    value = data.get(field)
    if value is None or not isinstance(value, str) or value in allowed:
        return None
    return invalid_enum(field, value, target, allowed)


def string_type_issues(data: dict, fields: set[str], target: str) -> list[Issue]:
    issues: list[Issue] = []
    for field in sorted(fields):
        value = data.get(field)
        if value is not None and not isinstance(value, str):
            issues.append(invalid_type(field, value, target, "string"))
    return issues


def env_issues(data: dict, target: str) -> list[Issue]:
    raw_env = data.get("env")
    if raw_env is None:
        return []
    if not isinstance(raw_env, dict):
        return [invalid_type("env", raw_env, target, "mapping")]
    return [
        invalid_env_key(str(key), target)
        for key in sorted(raw_env)
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", str(key))
    ]


def name_or_fallback(data: dict, fallback: str) -> str:
    value = data.get("name")
    if not isinstance(value, str):
        return fallback
    name = value.strip()
    return name or fallback


def empty_name_issue(data: dict, target: str, scope: str) -> Issue | None:
    value = data.get("name")
    if isinstance(value, str) and not value.strip():
        return empty_name(target, scope)
    return None


def reserved_name_separator_issue(data: dict, target: str, scope: str) -> Issue | None:
    value = data.get("name")
    if isinstance(value, str):
        name = value.strip()
        if name and (":" in name or "." in name):
            return reserved_name_separator(target, scope, name)
    return None


def duplicated_names(items: list[dict]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        name = item.get("name")
        if not isinstance(name, str):
            continue
        name = name.strip()
        if not name:
            continue
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    return duplicates
