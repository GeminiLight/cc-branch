"""Application-level state persistence boundary."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from pathlib import Path

from ..models import WorkspaceState
from ..state import load_state, save_state


class StateStore:
    """Load, save, and update workspace state through one boundary."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> WorkspaceState:
        return load_state(self.path)

    def save(self, state: WorkspaceState) -> None:
        save_state(self.path, state)

    def update(self, fn: Callable[[WorkspaceState], WorkspaceState]) -> WorkspaceState:
        current_state = self.load()
        original_state = deepcopy(current_state)
        next_state = fn(current_state)
        if next_state != original_state:
            self.save(next_state)
        return next_state
