"""Opener discovery and metadata registry."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass

from ..models import OpenerSpec
from .platform import _find_macos_app
from .types import (
    EDITOR_WORKSPACE_CAPABILITIES,
    PROJECT_CAPABILITIES,
    TERMINAL_CAPABILITIES,
    WARP_CAPABILITIES,
    OpenerInfo,
    OpenerKind,
)


@dataclass(frozen=True)
class OpenerRegistry:
    """Discovers built-in and configured openers for the current machine."""

    custom_openers: dict[str, OpenerSpec] | None = None

    def list_payload(self, default: str = "auto-terminal") -> dict:
        return {
            "default": default,
            "openers": [info.to_dict() for info in [*self.custom_infos(), *self.builtin_infos()]],
        }

    def label(self, opener_id: str) -> str:
        info = self.find(opener_id)
        return info.label if info else opener_id

    def supports(self, opener_id: str, capability: str) -> bool:
        info = self.find(opener_id or "auto-terminal")
        return bool(info and info.available and capability in info.capabilities)

    def find(self, opener_id: str) -> OpenerInfo | None:
        for info in self.custom_infos():
            if info.id == opener_id:
                return info
        for info in self.builtin_infos():
            if info.id == opener_id:
                return info
        return None

    def builtin_infos(self) -> list[OpenerInfo]:
        openers: list[OpenerInfo] = [_system_file_manager_info(), _auto_terminal_info()]

        if sys.platform == "darwin":
            openers.extend([
                _macos_app_info("terminal-app", "Terminal.app", "Terminal"),
                _macos_app_info("iterm2", "iTerm2", "iTerm"),
                _macos_app_info(
                    "warp",
                    "Warp",
                    "Warp",
                    capabilities=WARP_CAPABILITIES,
                    kind="terminal",
                    require_osascript=False,
                ),
            ])
        elif os.name == "nt":
            openers.extend([
                _command_info("windows-terminal", "Windows Terminal", "wt", TERMINAL_CAPABILITIES, kind="terminal"),
                _command_info("powershell", "PowerShell", "powershell", TERMINAL_CAPABILITIES, kind="terminal"),
            ])
        else:
            openers.extend([
                _command_info("gnome-terminal", "GNOME Terminal", "gnome-terminal", TERMINAL_CAPABILITIES, kind="terminal"),
                _command_info("konsole", "Konsole", "konsole", TERMINAL_CAPABILITIES, kind="terminal"),
                _command_info("xfce4-terminal", "XFCE Terminal", "xfce4-terminal", TERMINAL_CAPABILITIES, kind="terminal"),
                _command_info("xterm", "xterm", "xterm", TERMINAL_CAPABILITIES, kind="terminal"),
                _command_info("wezterm", "WezTerm", "wezterm", TERMINAL_CAPABILITIES, kind="terminal"),
                _command_info("alacritty", "Alacritty", "alacritty", TERMINAL_CAPABILITIES, kind="terminal"),
            ])

        openers.extend([
            _command_info("vscode", "VS Code", "code", EDITOR_WORKSPACE_CAPABILITIES, kind="editor"),
            _command_info("cursor", "Cursor", "cursor", EDITOR_WORKSPACE_CAPABILITIES, kind="editor"),
        ])
        return openers

    def custom_infos(self) -> list[OpenerInfo]:
        infos: list[OpenerInfo] = []
        for opener_id, spec in (self.custom_openers or {}).items():
            capabilities = spec.capabilities or (
                TERMINAL_CAPABILITIES if spec.kind == "terminal" else PROJECT_CAPABILITIES
            )
            executable = shutil.which(spec.command) if spec.command else None
            infos.append(
                OpenerInfo(
                    id=opener_id,
                    label=spec.label or opener_id,
                    kind="editor" if spec.kind == "editor" else "terminal",
                    available=executable is not None,
                    capabilities=list(capabilities),
                    source="config",
                    executable=executable,
                    reason=None if executable else f"{spec.command or opener_id} CLI not found",
                )
            )
        return infos


def list_openers(
    default: str = "auto-terminal",
    custom_openers: dict[str, OpenerSpec] | None = None,
) -> dict:
    """Return serializable opener metadata for the current machine."""
    return OpenerRegistry(custom_openers).list_payload(default)


def opener_label(
    opener_id: str,
    custom_openers: dict[str, OpenerSpec] | None = None,
) -> str:
    """Return a human-friendly label for *opener_id*."""
    return OpenerRegistry(custom_openers).label(opener_id)


def opener_supports(
    opener_id: str,
    capability: str,
    custom_openers: dict[str, OpenerSpec] | None = None,
) -> bool:
    """Return whether a registered opener supports a capability."""
    return OpenerRegistry(custom_openers).supports(opener_id, capability)


def _builtin_openers() -> list[OpenerInfo]:
    return OpenerRegistry().builtin_infos()


def _custom_openers(custom_openers: dict[str, OpenerSpec]) -> list[OpenerInfo]:
    return OpenerRegistry(custom_openers).custom_infos()


def _opener_info(
    opener_id: str,
    custom_openers: dict[str, OpenerSpec] | None = None,
) -> OpenerInfo | None:
    return OpenerRegistry(custom_openers).find(opener_id)


def _command_info(
    opener_id: str,
    label: str,
    command: str,
    capabilities: list[str],
    *,
    kind: OpenerKind,
) -> OpenerInfo:
    executable = shutil.which(command)
    return OpenerInfo(
        id=opener_id,
        label=label,
        kind=kind,
        available=executable is not None,
        capabilities=capabilities,
        executable=executable,
        reason=None if executable else f"{command} CLI not found",
    )


def _macos_app_info(
    opener_id: str,
    label: str,
    app_name: str,
    *,
    capabilities: list[str] = TERMINAL_CAPABILITIES,
    kind: OpenerKind = "terminal",
    require_osascript: bool = True,
) -> OpenerInfo:
    if require_osascript and "run_command" in capabilities and shutil.which("osascript") is None:
        return OpenerInfo(
            id=opener_id,
            label=label,
            kind=kind,
            available=False,
            capabilities=capabilities,
            reason="osascript is not available",
        )
    app_path = _find_macos_app(app_name)
    if app_path is None:
        return OpenerInfo(
            id=opener_id,
            label=label,
            kind=kind,
            available=False,
            capabilities=capabilities,
            reason=f"{label} not found",
        )
    return OpenerInfo(
        id=opener_id,
        label=label,
        kind=kind,
        available=True,
        capabilities=capabilities,
        executable=str(app_path),
    )


def _auto_terminal_info() -> OpenerInfo:
    reason = _auto_terminal_unavailable_reason()
    return OpenerInfo(
        id="auto-terminal",
        label="System Terminal",
        kind="terminal",
        available=reason is None,
        capabilities=TERMINAL_CAPABILITIES,
        reason=reason,
    )


def _system_file_manager_info() -> OpenerInfo:
    if sys.platform == "darwin":
        executable = shutil.which("open")
        return OpenerInfo(
            id="system-file-manager",
            label="Finder",
            kind="editor",
            available=executable is not None,
            capabilities=PROJECT_CAPABILITIES,
            executable=executable,
            reason=None if executable else "open is not available",
        )
    if os.name == "nt":
        return OpenerInfo(
            id="system-file-manager",
            label="File Explorer",
            kind="editor",
            available=True,
            capabilities=PROJECT_CAPABILITIES,
        )
    executable = shutil.which("xdg-open")
    return OpenerInfo(
        id="system-file-manager",
        label="File Manager",
        kind="editor",
        available=executable is not None,
        capabilities=PROJECT_CAPABILITIES,
        executable=executable,
        reason=None if executable else "xdg-open is not available",
    )


def _auto_terminal_unavailable_reason() -> str | None:
    if sys.platform == "darwin":
        return None if shutil.which("osascript") else "osascript is not available"
    if os.name == "nt":
        return None if shutil.which("powershell") else "powershell is not available"
    candidates = [
        "x-terminal-emulator",
        "gnome-terminal",
        "konsole",
        "xfce4-terminal",
        "xterm",
        "wezterm",
        "alacritty",
    ]
    return None if any(shutil.which(candidate) for candidate in candidates) else "no supported terminal emulator was found"
