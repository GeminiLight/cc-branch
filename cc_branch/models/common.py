from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def _as_public_dict(obj: Any) -> Any:
    """Recursively convert dataclasses to compact public dictionaries."""
    if is_dataclass(obj) and not isinstance(obj, type):
        result: dict[str, Any] = {}
        for k, v in asdict(obj).items():
            if k.startswith("_"):
                continue
            if k == "enabled" and v is True:
                continue
            if v in (None, "", [], {}):
                # Keep explicit nested containers that downstream renderers expect,
                # while omitting empty scalar defaults.
                if k in ("env", "windows", "agents") and not v:
                    result[k] = v
                continue
            result[k] = _as_public_dict(v)
        return result
    if isinstance(obj, list):
        return [_as_public_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _as_public_dict(v) for k, v in obj.items()}
    return obj
