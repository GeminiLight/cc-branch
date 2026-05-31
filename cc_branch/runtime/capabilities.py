"""Slot runtime capability model.

This module keeps runtime policy out of ad hoc string comparisons. A slot
runtime describes how CC Branch executes and manages a slot; the shell command
inside that slot is a separate concern.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

RuntimeId = Literal["tmux", "terminal"]

TMUX_RUNTIME: RuntimeId = "tmux"
TERMINAL_RUNTIME: RuntimeId = "terminal"


@dataclass(frozen=True)
class RuntimeCapabilities:
    """Feature set exposed by a slot runtime."""

    runtime: RuntimeId
    managed: bool
    external_process: bool
    reusable: bool
    supports_windows: bool
    supports_background_start: bool
    supports_attach: bool
    supports_stop: bool
    supports_dashboard: bool


RUNTIME_CAPABILITIES: dict[str, RuntimeCapabilities] = {
    TMUX_RUNTIME: RuntimeCapabilities(
        runtime=TMUX_RUNTIME,
        managed=True,
        external_process=False,
        reusable=True,
        supports_windows=True,
        supports_background_start=True,
        supports_attach=True,
        supports_stop=True,
        supports_dashboard=True,
    ),
    TERMINAL_RUNTIME: RuntimeCapabilities(
        runtime=TERMINAL_RUNTIME,
        managed=False,
        external_process=True,
        reusable=False,
        supports_windows=False,
        supports_background_start=False,
        supports_attach=False,
        supports_stop=False,
        supports_dashboard=False,
    ),
}


def runtime_capabilities(runtime: str) -> RuntimeCapabilities:
    """Return capabilities for a known slot runtime."""
    try:
        return RUNTIME_CAPABILITIES[runtime]
    except KeyError as exc:
        raise ValueError(f"unsupported slot runtime: {runtime}") from exc


def is_known_runtime(runtime: str) -> bool:
    return runtime in RUNTIME_CAPABILITIES


def is_managed_runtime(runtime: str) -> bool:
    return runtime_capabilities(runtime).managed


def is_external_process_runtime(runtime: str) -> bool:
    return runtime_capabilities(runtime).external_process


def supports_windows(runtime: str) -> bool:
    return runtime_capabilities(runtime).supports_windows


def supports_background_start(runtime: str) -> bool:
    return runtime_capabilities(runtime).supports_background_start


def supports_attach(runtime: str) -> bool:
    return runtime_capabilities(runtime).supports_attach


def supports_stop(runtime: str) -> bool:
    return runtime_capabilities(runtime).supports_stop


def supports_dashboard(runtime: str) -> bool:
    return runtime_capabilities(runtime).supports_dashboard


def managed_slots(slots: Iterable):
    """Return slots whose runtime is managed by CC Branch."""
    return [slot for slot in slots if is_managed_runtime(slot.runtime)]


def external_process_slots(slots: Iterable):
    """Return slots that open external local processes."""
    return [slot for slot in slots if is_external_process_runtime(slot.runtime)]
