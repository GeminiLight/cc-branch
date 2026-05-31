"""Compatibility facade for slot runtime capabilities."""

from __future__ import annotations

from .runtime.capabilities import (
    RUNTIME_CAPABILITIES,
    TERMINAL_RUNTIME,
    TMUX_RUNTIME,
    RuntimeCapabilities,
    RuntimeId,
    external_process_slots,
    is_external_process_runtime,
    is_known_runtime,
    is_managed_runtime,
    managed_slots,
    runtime_capabilities,
    supports_attach,
    supports_background_start,
    supports_dashboard,
    supports_stop,
    supports_windows,
)

__all__ = [
    "RUNTIME_CAPABILITIES",
    "TERMINAL_RUNTIME",
    "TMUX_RUNTIME",
    "RuntimeCapabilities",
    "RuntimeId",
    "external_process_slots",
    "is_external_process_runtime",
    "is_known_runtime",
    "is_managed_runtime",
    "managed_slots",
    "runtime_capabilities",
    "supports_attach",
    "supports_background_start",
    "supports_dashboard",
    "supports_stop",
    "supports_windows",
]
