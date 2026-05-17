from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Issue:
    """A single diagnosed issue."""

    issue_type: str
    severity: str  # "error" | "warning" | "info"
    message: str
    target: str = ""  # e.g. "dev.planner" or "tmux"
    context: dict[str, Any] = field(default_factory=dict)
    fixable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_type": self.issue_type,
            "severity": self.severity,
            "message": self.message,
            "target": self.target,
            "context": self.context,
            "fixable": self.fixable,
        }


@dataclass
class DoctorReport:
    """Structured result of a workspace health check."""

    project: str
    issues: list[Issue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == "warning" for i in self.issues)

    @property
    def fixable_issues(self) -> list[Issue]:
        return [i for i in self.issues if i.fixable]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "issues": [issue.to_dict() for issue in self.issues],
            "has_errors": self.has_errors,
            "has_warnings": self.has_warnings,
        }

