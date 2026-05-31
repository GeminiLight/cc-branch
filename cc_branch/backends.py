"""Compatibility facade for runtime backend APIs."""

from __future__ import annotations

from .runtime.backends import Backend, TmuxBackend, get_backend, set_backend

__all__ = ["Backend", "TmuxBackend", "get_backend", "set_backend"]
