"""Global application state helpers."""

from __future__ import annotations

from .paths import projects_index_path
from .project_index import ProjectIndexStore

__all__ = [
    "ProjectIndexStore",
    "projects_index_path",
]
