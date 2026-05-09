from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def _as_legacy_dict(obj: Any) -> Any:
    """Recursively convert dataclasses to plain dicts for legacy compatibility."""
    if is_dataclass(obj) and not isinstance(obj, type):
        result: dict[str, Any] = {}
        for k, v in asdict(obj).items():
            if k.startswith("_"):
                continue
            if v in (None, "", [], {}):
                # Preserve behaviour of old load_workspace: keep explicit overrides
                # but omit empty defaults
                if k in ("env", "windows", "agents") and not v:
                    result[k] = v if k == "env" else v
                continue
            result[k] = _as_legacy_dict(v)
        return result
    if isinstance(obj, list):
        return [_as_legacy_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _as_legacy_dict(v) for k, v in obj.items()}
    return obj
