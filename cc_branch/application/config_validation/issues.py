"""Issue factories for raw config validation."""

from __future__ import annotations

from typing import Any

from ...models import Issue


def unknown_field(field: str, target: str) -> Issue:
    return Issue(
        "unknown_field",
        "warning",
        f"Unknown field '{field}'",
        target=target,
        context={"field": field},
    )


def invalid_enum(field: str, value: Any, target: str, allowed: set[str]) -> Issue:
    return Issue(
        "invalid_enum",
        "error",
        f"Invalid {field}: {value}",
        target=target,
        context={"field": field, "value": value, "allowed": sorted(allowed)},
    )


def invalid_type(field: str, value: Any, target: str, expected: str) -> Issue:
    return Issue(
        "invalid_type",
        "error",
        f"Invalid type for {field}: expected {expected}",
        target=target,
        context={"field": field, "expected": expected, "actual": type(value).__name__},
    )


def empty_name(target: str, scope: str) -> Issue:
    return Issue(
        "empty_name",
        "error",
        f"{scope.capitalize()} name cannot be empty",
        target=target,
        context={"field": "name", "scope": scope},
    )


def reserved_name_separator(target: str, scope: str, name: str) -> Issue:
    return Issue(
        "reserved_name_separator",
        "error",
        f"{scope.capitalize()} name cannot contain ':' or '.'",
        target=target,
        context={"field": "name", "scope": scope, "name": name, "separators": [":", "."]},
    )


def invalid_env_key(key: str, target: str) -> Issue:
    return Issue(
        "invalid_env_key",
        "error",
        f"Invalid environment variable name: {key}",
        target=target,
        context={"key": key},
    )


def duplicate_issue(issue_type: str, name: str, target: str, scope: str) -> Issue:
    return Issue(
        issue_type,
        "error",
        f"Duplicate {scope} '{name}'",
        target=target,
        context={"name": name, "scope": scope},
    )


def missing_launch_command(target: str) -> Issue:
    return Issue(
        "missing_launch_command",
        "error",
        "Window has neither command nor agent",
        target=target,
    )
