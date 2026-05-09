"""Agent adapter facade.

Adapters abstract differences between AI CLI tools so planning code can ask
for launch and label commands without embedding per-agent conditionals.
"""

from __future__ import annotations

from .base import AgentAdapter
from .none import NoneAdapter
from .none import NoneAdapter as _NoneAdapter
from .resume import (
    FlagResumeAdapter,
    InternalResumeAdapter,
)
from .resume import (
    FlagResumeAdapter as _FlagResumeAdapter,
)
from .resume import (
    InternalResumeAdapter as _InternalResumeAdapter,
)
from .selection import get_adapter

__all__ = [
    "AgentAdapter",
    "FlagResumeAdapter",
    "InternalResumeAdapter",
    "NoneAdapter",
    "get_adapter",
]
