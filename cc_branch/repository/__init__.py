"""State repository facade."""

from __future__ import annotations

from .codec import state_data, state_data as _state_data, yaml_to_state, yaml_to_state as _yaml_to_state
from .state_repository import StateRepository
from .validation import require_yaml_path, require_yaml_path as _require_yaml_path

__all__ = [
    "StateRepository",
    "require_yaml_path",
    "state_data",
    "yaml_to_state",
]
