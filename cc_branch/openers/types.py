"""Shared opener types and capability constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

OpenIntentKind = Literal["workspace_dashboard", "attach_target", "project_folder"]
OpenerKind = Literal["terminal", "editor"]


class OpenerError(RuntimeError):
    """Raised when an opener cannot handle the requested action."""


@dataclass(frozen=True)
class OpenIntent:
    """A user-level intent for opening a workspace target."""

    kind: OpenIntentKind
    target: str | None = None


@dataclass(frozen=True)
class OpenerInfo:
    """Serializable metadata for an opener."""

    id: str
    label: str
    kind: OpenerKind
    available: bool
    capabilities: list[str]
    source: str = "builtin"
    executable: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict:
        payload = {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "available": self.available,
            "capabilities": self.capabilities,
            "source": self.source,
        }
        if self.executable:
            payload["executable"] = self.executable
        if self.reason:
            payload["reason"] = self.reason
        return payload


TERMINAL_CAPABILITIES = ["run_command", "dashboard", "attach_target", "open_project"]
PROJECT_CAPABILITIES = ["open_project"]
EDITOR_WORKSPACE_CAPABILITIES = ["open_project", "workspace_file"]
WARP_CAPABILITIES = ["run_command", "dashboard", "attach_target", "open_project", "layout"]


@dataclass(frozen=True)
class OpenCommandSpec:
    """A visible terminal command with enough metadata for native layouts."""

    title: str
    cwd: Path
    command: str
