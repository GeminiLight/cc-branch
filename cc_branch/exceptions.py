"""Domain exceptions for cc-branch.

All custom exceptions inherit from :class:`CcbError` so that the CLI and
Web UI can catch them uniformly and present user-friendly messages.
"""

from __future__ import annotations


class CcbError(Exception):
    """Base exception for all cc-branch errors."""


class ConfigError(CcbError):
    """Raised when workspace configuration is invalid, missing, or unreadable."""


class WorkspaceError(CcbError):
    """Raised when workspace operations fail."""


class SlotNotFoundError(WorkspaceError):
    """Raised when a referenced slot does not exist in the workspace plan."""


class WindowNotFoundError(WorkspaceError):
    """Raised when a referenced window does not exist in the workspace plan."""


class RuntimeError(CcbError):
    """Raised when a runtime operation (tmux, shell, process) fails."""


class StateError(CcbError):
    """Raised when state persistence (load, save, merge) fails."""
