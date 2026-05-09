"""Warp opener support."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from .platform import _find_macos_app, _open_uri, _popen, _slug, _warp_launch_config_dir
from .types import OpenCommandSpec


@dataclass(frozen=True)
class WarpLauncher:
    """Builds Warp launch configurations and opens them through Warp URIs."""

    def open_uri(self, uri: str) -> None:
        if sys.platform == "darwin":
            app_path = _find_macos_app("Warp")
            if app_path is not None:
                _popen(["open", "-a", str(app_path), uri])
                return
        _open_uri(uri)

    def launch_config_path(self, name: str, commands: list[OpenCommandSpec]) -> Path:
        digest_source = "\n".join(f"{spec.title}\0{spec.cwd}\0{spec.command}" for spec in commands)
        digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:12]
        directory = _warp_launch_config_dir()
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{_slug(name)}-{digest}.yaml"

    def layout_yaml(self, name: str, commands: list[OpenCommandSpec]) -> str:
        lines = [
            "---",
            f"name: {_yaml_string(name)}",
            "active_window_index: 0",
            "windows:",
            "  - active_tab_index: 0",
            "    tabs:",
            f"      - title: {_yaml_string(name)}",
            "        layout:",
        ]
        if len(commands) == 1:
            spec = commands[0]
            lines.extend([
                f"          cwd: {_yaml_string(str(spec.cwd))}",
                "          commands:",
                f"            - exec: {_yaml_string(spec.command)}",
            ])
        else:
            lines.extend([
                "          split_direction: vertical",
                "          panes:",
            ])
            lines.extend(self.pane_lines(commands, indent=12, depth=0, focus_first=True))
        lines.extend([
            "        color: blue",
            "",
        ])
        return "\n".join(lines)

    def leaf_lines(self, spec: OpenCommandSpec, *, indent: int, focused: bool) -> list[str]:
        spaces = " " * indent
        child = " " * (indent + 2)
        command_indent = " " * (indent + 4)
        lines = [
            f"{spaces}- cwd: {_yaml_string(str(spec.cwd))}",
            f"{child}commands:",
            f"{command_indent}- exec: {_yaml_string(spec.command)}",
        ]
        if focused:
            lines.append(f"{child}is_focused: true")
        return lines

    def pane_lines(
        self,
        commands: list[OpenCommandSpec],
        *,
        indent: int,
        depth: int,
        focus_first: bool,
    ) -> list[str]:
        """Render panes as nested binary splits, matching Warp's documented examples."""
        if not commands:
            return []
        if len(commands) == 1:
            return self.leaf_lines(commands[0], indent=indent, focused=focus_first)
        if len(commands) == 2:
            return [
                *self.leaf_lines(commands[0], indent=indent, focused=focus_first),
                *self.leaf_lines(commands[1], indent=indent, focused=False),
            ]

        split_direction = "horizontal" if depth % 2 == 0 else "vertical"
        spaces = " " * indent
        child = " " * (indent + 2)
        lines = self.leaf_lines(commands[0], indent=indent, focused=focus_first)
        lines.extend([
            f"{spaces}- split_direction: {split_direction}",
            f"{child}panes:",
        ])
        lines.extend(
            self.pane_lines(
                commands[1:],
                indent=indent + 4,
                depth=depth + 1,
                focus_first=False,
            )
        )
        return lines

    def open_layout(self, commands: list[OpenCommandSpec], *, name: str = "CC Branch") -> None:
        path = self.launch_config_path(name, commands)
        path.write_text(self.layout_yaml(name, commands), encoding="utf-8")
        self.open_uri(f"warp://launch/{quote(str(path), safe='/:')}")

    def open_command(self, cwd: Path, command: str, *, title: str) -> None:
        self.open_layout([OpenCommandSpec(title=title, cwd=cwd, command=command)], name=title)


def _yaml_string(value: str) -> str:
    return json.dumps(value)


warp_launcher = WarpLauncher()


def _open_warp_uri(uri: str) -> None:
    warp_launcher.open_uri(uri)


def _warp_launch_config_path(name: str, commands: list[OpenCommandSpec]) -> Path:
    return warp_launcher.launch_config_path(name, commands)


def _warp_layout_yaml(name: str, commands: list[OpenCommandSpec]) -> str:
    return warp_launcher.layout_yaml(name, commands)


def _warp_leaf_lines(spec: OpenCommandSpec, *, indent: int, focused: bool) -> list[str]:
    return warp_launcher.leaf_lines(spec, indent=indent, focused=focused)


def _warp_pane_lines(
    commands: list[OpenCommandSpec],
    *,
    indent: int,
    depth: int,
    focus_first: bool,
) -> list[str]:
    return warp_launcher.pane_lines(
        commands,
        indent=indent,
        depth=depth,
        focus_first=focus_first,
    )


def _open_warp_layout(commands: list[OpenCommandSpec], *, name: str = "CC Branch") -> None:
    warp_launcher.open_layout(commands, name=name)


def _open_warp_command(cwd: Path, command: str, *, title: str) -> None:
    warp_launcher.open_command(cwd, command, title=title)
