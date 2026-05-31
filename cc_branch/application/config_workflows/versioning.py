"""Config editor versioning and atomic writes."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path


def content_hash(content: str) -> str:
    """Return the version hash used by config editor clients."""
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def file_version_payload(path: Path, content: str) -> dict[str, object]:
    """Return file version metadata for optimistic concurrency checks."""
    mtime = path.stat().st_mtime if path.exists() else None
    return {"mtime": mtime, "content_hash": content_hash(content)}


def write_text_atomic(path: Path, content: str) -> None:
    """Write text through a temp file and backup existing content."""
    temp_path = path.with_suffix(path.suffix + ".tmp")
    backup_path = path.with_suffix(path.suffix + ".bak")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_text(content, encoding="utf-8")
    if path.exists():
        shutil.copy2(path, backup_path)
    temp_path.replace(path)


def base_version_matches(
    current_version: dict[str, object],
    *,
    base_mtime: object | None,
    base_content_hash: str | None,
) -> bool:
    """Return whether a client base version matches the current file."""
    current_mtime = _float_or_zero(current_version.get("mtime"))
    mtime_matches = base_mtime is None or abs(_float_or_zero(base_mtime) - current_mtime) < 0.000001
    hash_matches = base_content_hash is None or base_content_hash == current_version.get("content_hash")
    return mtime_matches and hash_matches


def _float_or_zero(value: object | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (str, bytes, bytearray, int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0
