"""Raw config validation entrypoint."""

from __future__ import annotations

from pathlib import Path

from ...models import Issue
from .constants import DISPLAY_FIELDS, LAYOUT_BACKENDS, TOP_LEVEL_FIELDS, TOP_LEVEL_STRING_FIELDS
from .issues import invalid_type
from .sections import agent_issues, defaults_issues, opener_issues, slot_issues, tab_issues
from .validators import enum_issue, string_type_issues, unknown_fields

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


def collect_config_issues(content: str, path: Path) -> list[Issue]:
    """Collect structural config issues without normalizing or planning."""
    suffix = path.suffix.lower()
    if suffix not in {".yaml", ".yml"}:
        return [
            Issue(
                "unsupported_config_format",
                "error",
                f"Unsupported config format: {path.suffix}; use YAML",
                target="config",
            )
        ]
    if yaml is None:  # pragma: no cover
        return [Issue("missing_yaml_dependency", "error", "YAML support requires PyYAML", target="config")]
    data = yaml.safe_load(content) or {}
    if not isinstance(data, dict):
        return [Issue("invalid_config_shape", "error", "workspace config must deserialize to a mapping", target="config")]

    issues = unknown_fields(data, TOP_LEVEL_FIELDS, "config")
    issues.extend(string_type_issues(data, TOP_LEVEL_STRING_FIELDS, "config"))
    issue = enum_issue(data, "layoutBackend", LAYOUT_BACKENDS, "config")
    if issue is not None:
        issues.append(issue)
    raw_display = data.get("display")
    if raw_display is not None:
        if isinstance(raw_display, dict):
            issues.extend(unknown_fields(raw_display, DISPLAY_FIELDS, "display"))
        else:
            issues.append(invalid_type("display", raw_display, "config", "mapping"))
    issues.extend(defaults_issues(data.get("defaults")))
    issues.extend(agent_issues(data.get("agents")))
    issues.extend(opener_issues(data.get("openers")))
    issues.extend(tab_issues(data.get("tabs")))
    issues.extend(slot_issues(data.get("slots")))
    return issues
