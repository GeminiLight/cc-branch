"""Backend abstraction for managed workspace runtimes.

The :class:`Backend` protocol defines the interface that ``runtime.execution``
expects from a persistent session/window implementation. The default
implementation is :class:`TmuxBackend`.
"""

from __future__ import annotations

import subprocess
from typing import Protocol

from .executables import which


def _exact_tmux_target(target: str) -> str:
    """Force tmux to match session/window names exactly instead of by prefix."""
    if target.startswith("="):
        return target
    if ":" not in target:
        return f"={target}"
    session, window = target.split(":", 1)
    if window.startswith("="):
        return f"={session}:{window}"
    return f"={session}:={window}"


class Backend(Protocol):
    """Abstract interface for managed session/window operations."""

    def available(self) -> bool:
        """Return True if the backend CLI is installed and on PATH."""
        ...

    def has_session(self, name: str) -> bool:
        ...

    def has_window(self, session: str, window: str) -> bool:
        ...

    def list_windows(self, session: str) -> set[str]:
        ...

    def send_keys(self, target: str, keys: str) -> None:
        ...

    def create_session(
        self,
        name: str,
        cwd: str | None = None,
        window_name: str | None = None,
        command: list[str] | None = None,
    ) -> None:
        ...

    def create_window(self, session: str, name: str, cwd: str | None = None) -> None:
        ...

    def kill_session(self, name: str) -> None:
        ...

    def kill_window(self, target: str) -> None:
        ...

    def attach_session(self, target: str) -> None:
        ...

    def split_window(self, target: str, command: list[str]) -> None:
        ...

    def select_layout(self, target: str, layout: str) -> None:
        ...


class TmuxBackend:
    """tmux-based backend implementation."""

    def _command(self) -> str | None:
        return which("tmux")

    def _required_command(self) -> str:
        return self._command() or "tmux"

    def available(self) -> bool:
        return self._command() is not None

    def has_session(self, name: str) -> bool:
        tmux = self._command()
        if tmux is None:
            return False
        try:
            result = subprocess.run(
                [tmux, "has-session", "-t", _exact_tmux_target(name)],
                capture_output=True,
                check=False,
                timeout=2,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def has_window(self, session: str, window: str) -> bool:
        return window in self.list_windows(session)

    def list_windows(self, session: str) -> set[str]:
        tmux = self._command()
        if tmux is None:
            return set()
        try:
            result = subprocess.run(
                [tmux, "list-windows", "-t", _exact_tmux_target(session), "-F", "#{window_name}"],
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
            if result.returncode != 0:
                return set()
            return set(result.stdout.splitlines())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return set()

    def send_keys(self, target: str, keys: str) -> None:
        tmux = self._required_command()
        subprocess.run(
            [tmux, "send-keys", "-t", _exact_tmux_target(target), keys, "Enter"],
            check=True,
        )

    def create_session(
        self,
        name: str,
        cwd: str | None = None,
        window_name: str | None = None,
        command: list[str] | None = None,
    ) -> None:
        cmd = [self._required_command(), "new-session", "-d", "-s", name]
        if window_name:
            cmd.extend(["-n", window_name])
        if cwd:
            cmd.extend(["-c", cwd])
        if command:
            cmd.extend(command)
        subprocess.run(cmd, check=True)

    def create_window(self, session: str, name: str, cwd: str | None = None) -> None:
        cmd = [self._required_command(), "new-window", "-d", "-t", _exact_tmux_target(session), "-n", name]
        if cwd:
            cmd.extend(["-c", cwd])
        subprocess.run(cmd, check=True)

    def kill_session(self, name: str) -> None:
        subprocess.run([self._required_command(), "kill-session", "-t", _exact_tmux_target(name)], check=True)

    def kill_window(self, target: str) -> None:
        subprocess.run([self._required_command(), "kill-window", "-t", _exact_tmux_target(target)], check=True)

    def attach_session(self, target: str) -> None:
        subprocess.run([self._required_command(), "attach-session", "-t", _exact_tmux_target(target)], check=True)

    def split_window(self, target: str, command: list[str]) -> None:
        cmd = [self._required_command(), "split-window", "-t", _exact_tmux_target(target)]
        cmd.extend(command)
        subprocess.run(cmd, check=True)

    def select_layout(self, target: str, layout: str) -> None:
        subprocess.run(
            [self._required_command(), "select-layout", "-t", _exact_tmux_target(target), layout],
            check=True,
        )


# ---------------------------------------------------------------------------
# Module-level default backend (lazy init so tests can swap it out)
# ---------------------------------------------------------------------------

_default_backend: Backend | None = None


def get_backend() -> Backend:
    """Return the active backend instance (default: TmuxBackend)."""
    global _default_backend
    if _default_backend is None:
        _default_backend = TmuxBackend()
    return _default_backend


def set_backend(backend: Backend) -> None:
    """Replace the global backend (useful for testing)."""
    global _default_backend
    _default_backend = backend
