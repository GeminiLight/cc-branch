"""Opener discovery and metadata registry."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePath

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
                _macos_app_info(
                    "iterm2",
                    "iTerm2",
                    "iTerm",
                    capabilities=PROJECT_CAPABILITIES,
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

        warp_info = _warp_info()
        if warp_info is not None:
            openers.append(warp_info)

        openers.extend([
            _command_info("vscode", "VS Code", "code", EDITOR_WORKSPACE_CAPABILITIES, kind="editor", search_extra_paths=True),
            _command_info("cursor", "Cursor", "cursor", EDITOR_WORKSPACE_CAPABILITIES, kind="editor", search_extra_paths=True),
        ])
        return openers

    def custom_infos(self) -> list[OpenerInfo]:
        infos: list[OpenerInfo] = []
        for opener_id, spec in (self.custom_openers or {}).items():
            capabilities = spec.capabilities or (
                TERMINAL_CAPABILITIES if spec.kind == "terminal" else PROJECT_CAPABILITIES
            )
            executable = _resolve_command(spec.command, search_extra_paths=True) if spec.command else None
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
    search_extra_paths: bool = False,
) -> OpenerInfo:
    executable = _resolve_command(command, search_extra_paths=search_extra_paths)
    return OpenerInfo(
        id=opener_id,
        label=label,
        kind=kind,
        available=executable is not None,
        capabilities=capabilities,
        executable=executable,
        reason=None if executable else f"{command} CLI not found",
    )


def _resolve_command(command: str, *, search_extra_paths: bool = False) -> str | None:
    executable = shutil.which(command)
    if executable:
        return executable

    if not search_extra_paths:
        return None

    for candidate in _candidate_command_paths(command):
        if _is_executable(candidate):
            return str(candidate)

    if shell_path := _login_shell_command_path(command):
        return str(shell_path)

    return None


def _candidate_command_paths(command: str) -> list[Path]:
    candidates: list[Path] = []
    for directory in _extra_command_dirs():
        for name in _command_names(command):
            candidates.append(directory / name)

    if sys.platform == "darwin":
        candidates.extend(_macos_app_cli_candidates(command))

    return candidates


def _extra_command_dirs() -> list[Path]:
    home = Path.home()
    if sys.platform == "darwin":
        return [
            Path("/opt/homebrew/bin"),
            Path("/usr/local/bin"),
            Path("/usr/bin"),
            Path("/bin"),
            Path("/usr/sbin"),
            Path("/sbin"),
            home / ".local" / "bin",
        ]
    if os.name == "nt":
        local_app_data = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
        program_files = Path(os.environ.get("PROGRAMFILES") or "C:/Program Files")
        program_files_x86 = Path(os.environ.get("PROGRAMFILES(X86)") or "C:/Program Files (x86)")
        return [
            local_app_data / "Programs" / "Microsoft VS Code" / "bin",
            local_app_data / "Programs" / "Cursor" / "resources" / "app" / "bin",
            local_app_data / "Programs" / "cursor" / "resources" / "app" / "bin",
            program_files / "Microsoft VS Code" / "bin",
            program_files / "Cursor" / "resources" / "app" / "bin",
            program_files_x86 / "Microsoft VS Code" / "bin",
        ]
    return [
        Path("/usr/local/bin"),
        Path("/usr/bin"),
        Path("/bin"),
        home / ".local" / "bin",
        Path("/snap/bin"),
        Path("/var/lib/flatpak/exports/bin"),
        home / ".local" / "share" / "flatpak" / "exports" / "bin",
    ]


def _command_names(command: str) -> list[str]:
    if os.name != "nt" or PurePath(command).suffix:
        return [command]
    return [command, f"{command}.cmd", f"{command}.exe", f"{command}.bat"]


def _macos_app_cli_candidates(command: str) -> list[Path]:
    app_bins = {
        "code": [("Visual Studio Code", "code")],
        "cursor": [("Cursor", "cursor"), ("Cursor", "code")],
    }.get(command, [])
    return [
        app_path / "Contents" / "Resources" / "app" / "bin" / bin_name
        for app_name, bin_name in app_bins
        if (app_path := _find_macos_app(app_name)) is not None
    ]


def _is_executable(path: Path) -> bool:
    return path.exists() and os.access(path, os.X_OK)


@lru_cache(maxsize=64)
def _login_shell_command_path(command: str) -> Path | None:
    if os.name == "nt":
        return None

    for shell in _candidate_login_shells():
        script = f"command -v {shlex.quote(command)}"
        args = _login_shell_args(shell, script)
        try:
            result = subprocess.run(
                args,
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=3,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode != 0:
            continue
        if path := _first_executable_path(result.stdout):
            return path
    return None


def _candidate_login_shells() -> list[str]:
    candidates: list[str] = []
    if shell := os.environ.get("SHELL"):
        candidates.append(shell)
    candidates.extend(["/bin/zsh", "/bin/bash", "/bin/sh"])

    unique: list[str] = []
    seen: set[str] = set()
    for shell in candidates:
        if shell in seen or not Path(shell).exists():
            continue
        seen.add(shell)
        unique.append(shell)
    return unique


def _login_shell_args(shell: str, script: str) -> list[str]:
    name = Path(shell).name
    if name == "fish":
        return [shell, "--login", "--interactive", "--command", script]
    if name in {"bash", "zsh", "ksh"}:
        return [shell, "-l", "-i", "-c", script]
    return [shell, "-lc", script]


def _first_executable_path(output: str) -> Path | None:
    for line in output.splitlines():
        value = line.strip()
        if not value:
            continue
        candidate = Path(value).expanduser()
        if candidate.is_absolute() and _is_executable(candidate):
            return candidate
    return None


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


def _warp_info() -> OpenerInfo | None:
    if sys.platform == "darwin":
        executable = _find_macos_app("Warp")
        if executable is None:
            return OpenerInfo(
                id="warp",
                label="Warp",
                kind="terminal",
                available=False,
                capabilities=WARP_CAPABILITIES,
                reason="Warp not found",
            )
        return OpenerInfo(
            id="warp",
            label="Warp",
            kind="terminal",
            available=True,
            capabilities=WARP_CAPABILITIES,
            executable=str(executable),
        )

    if os.name == "nt":
        candidates: list[Path] = []
        for root_key in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
            root = os.environ.get(root_key)
            if not root:
                continue
            candidates.extend([
                Path(root) / "Programs" / "Warp" / "warp.exe",
                Path(root) / "Warp" / "warp.exe",
            ])
        for candidate in candidates:
            if candidate.exists():
                return OpenerInfo(
                    id="warp",
                    label="Warp",
                    kind="terminal",
                    available=True,
                    capabilities=WARP_CAPABILITIES,
                    executable=str(candidate),
                )
        executable = shutil.which("warp") or shutil.which("warp.exe")
        if executable:
            return OpenerInfo(
                id="warp",
                label="Warp",
                kind="terminal",
                available=True,
                capabilities=WARP_CAPABILITIES,
                executable=executable,
            )
        return OpenerInfo(
            id="warp",
            label="Warp",
            kind="terminal",
            available=False,
            capabilities=WARP_CAPABILITIES,
            reason="Warp not found",
        )

    executable = shutil.which("warp-terminal") or shutil.which("warp")
    if executable:
        return OpenerInfo(
            id="warp",
            label="Warp",
            kind="terminal",
            available=True,
            capabilities=WARP_CAPABILITIES,
            executable=executable,
        )
    return OpenerInfo(
        id="warp",
        label="Warp",
        kind="terminal",
        available=False,
        capabilities=WARP_CAPABILITIES,
        reason="warp-terminal is not available",
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
