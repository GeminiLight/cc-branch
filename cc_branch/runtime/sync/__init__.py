"""Runtime/config synchronization facade."""

from __future__ import annotations

from ..backends import get_backend
from .fingerprints import (
    agent_spec_dict as _agent_spec_dict,
)
from .fingerprints import (
    desired_fingerprint,
    fingerprint_launch_spec,
    window_launch_spec,
)
from .inspection import list_window_names as _list_window_names
from .inspection import tmux_has_session as _tmux_has_session
from .models import (
    LAUNCH_SPEC_VERSION,
    RuntimeSyncReport,
    SlotSyncStatus,
    SyncStatus,
    WindowSyncStatus,
)
from .report import build_runtime_sync_report
from .state import now_iso as _now_iso
from .state import record_applied_results
from .targets import (
    changed_or_missing_targets,
    extra_window_targets,
    reconcilable_targets,
    sync_report_for_target,
)

__all__ = [
    "LAUNCH_SPEC_VERSION",
    "RuntimeSyncReport",
    "SlotSyncStatus",
    "SyncStatus",
    "WindowSyncStatus",
    "_agent_spec_dict",
    "_list_window_names",
    "_now_iso",
    "_tmux_has_session",
    "build_runtime_sync_report",
    "changed_or_missing_targets",
    "desired_fingerprint",
    "extra_window_targets",
    "fingerprint_launch_spec",
    "get_backend",
    "reconcilable_targets",
    "record_applied_results",
    "sync_report_for_target",
    "window_launch_spec",
]
