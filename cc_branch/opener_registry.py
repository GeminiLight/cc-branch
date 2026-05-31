"""User-level opener registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import OpenerSpec

DEFAULT_GLOBAL_OPENERS = """# User-level opener definitions for cc-branch.
# Built-in openers load first; this file adds tools for all projects.
# A project can still override these values in .cc-branch/config.yaml.
openers: {}
"""


def user_openers_path() -> Path:
    return Path.home() / ".cc-branch" / "openers.yaml"


def parse_opener_definitions(data: dict[str, Any]) -> dict[str, OpenerSpec]:
    raw_openers = data.get("openers", {})
    if not isinstance(raw_openers, dict):
        return {}
    return {
        str(name): OpenerSpec.from_dict(spec)
        for name, spec in raw_openers.items()
        if isinstance(name, str) and name.strip() and isinstance(spec, dict)
    }


def load_global_openers() -> dict[str, OpenerSpec]:
    path = user_openers_path()
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}
    return parse_opener_definitions(data)


def merge_global_openers(local_openers: dict[str, OpenerSpec] | None = None) -> dict[str, OpenerSpec]:
    return {
        **load_global_openers(),
        **(local_openers or {}),
    }
