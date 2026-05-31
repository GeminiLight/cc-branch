"""User-level opener settings."""

from __future__ import annotations

from pathlib import Path

import yaml

from ..opener_registry import DEFAULT_GLOBAL_OPENERS, parse_opener_definitions, user_openers_path
from ..openers import list_openers
from .config_workflows.versioning import (
    base_version_matches,
    content_hash,
    file_version_payload,
    write_text_atomic,
)
from .results import ActionResult


def read_global_openers() -> ActionResult:
    """Return the editable user-level openers file."""
    path = user_openers_path()
    exists = path.exists()
    content = path.read_text(encoding="utf-8") if exists else DEFAULT_GLOBAL_OPENERS
    return ActionResult(
        ok=True,
        code="global_openers_loaded",
        message="Global openers loaded",
        payload=_payload(path, content, exists=exists),
    )


def save_global_openers(
    content: str,
    *,
    base_mtime: object | None = None,
    base_content_hash: str | None = None,
) -> ActionResult:
    """Validate and save the user-level openers file."""
    path = user_openers_path()
    current_content = path.read_text(encoding="utf-8") if path.exists() else DEFAULT_GLOBAL_OPENERS
    current_version: dict[str, object] = (
        file_version_payload(path, current_content)
        if path.exists()
        else {
            "mtime": None,
            "content_hash": content_hash(current_content),
        }
    )
    if not base_version_matches(
        current_version,
        base_mtime=base_mtime,
        base_content_hash=base_content_hash,
    ):
        return ActionResult(
            ok=False,
            code="global_openers_conflict",
            message="Global openers file changed on disk. Reload before saving.",
            payload={
                **_payload(path, current_content, exists=path.exists()),
                "current_content": current_content,
            },
        )

    issue = _validate_global_openers(content)
    if issue:
        return ActionResult(
            ok=False,
            code="invalid_global_openers",
            message=issue,
            payload={"issues": [{"message": issue}]},
        )

    write_text_atomic(path, _ensure_trailing_newline(content))
    saved_content = path.read_text(encoding="utf-8")
    return ActionResult(
        ok=True,
        code="global_openers_saved",
        message="Global openers saved",
        payload=_payload(path, saved_content, exists=True),
    )


def _payload(path: Path, content: str, *, exists: bool) -> dict:
    try:
        user_data = yaml.safe_load(content) or {}
    except yaml.YAMLError:
        user_data = {}
    user_data = user_data if isinstance(user_data, dict) else {}
    user_openers = parse_opener_definitions(user_data)
    version = file_version_payload(path, content) if path.exists() else {
        "mtime": None,
        "content_hash": content_hash(content),
    }
    return {
        "path": str(path),
        "exists": exists,
        "content": content,
        **version,
        "openers": list_openers(custom_openers=user_openers)["openers"],
        "user_openers": [
            {"id": name, **_opener_spec_payload(spec)}
            for name, spec in sorted(user_openers.items())
        ],
    }


def _opener_spec_payload(spec) -> dict:
    return {
        "label": spec.label,
        "kind": "editor" if spec.kind == "editor" else "terminal",
        "command": spec.command,
        "args": list(spec.args),
        "capabilities": list(spec.capabilities),
    }


def _validate_global_openers(content: str) -> str | None:
    try:
        data = yaml.safe_load(content) or {}
    except yaml.YAMLError as error:
        return str(error)
    if not isinstance(data, dict):
        return "Global openers YAML must be a mapping."
    openers = data.get("openers", {})
    if openers is None:
        return None
    if not isinstance(openers, dict):
        return "Global openers YAML must contain an 'openers' mapping."
    for name, spec in openers.items():
        if not isinstance(name, str) or not name.strip():
            return "Opener names must be non-empty strings."
        if not isinstance(spec, dict):
            return f"Opener '{name}' must be a mapping."
    return None


def _ensure_trailing_newline(content: str) -> str:
    return content if content.endswith("\n") else f"{content}\n"
