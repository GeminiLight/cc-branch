"""Warp opener support."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from .platform import _open_uri, _slug, _warp_launch_config_dir
from .types import OpenCommandSpec


@dataclass(frozen=True)
class WarpLauncher:
    """Builds Warp launch configurations and opens them through Warp URIs."""

    def open_uri(self, uri: str) -> None:
        _open_uri(uri)

    def launch_config_path(self, name: str, commands: list[OpenCommandSpec]) -> Path:
        directory = _warp_launch_config_dir()
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{_slug(name)}.yaml"

    def launch_config_name(self, name: str, commands: list[OpenCommandSpec]) -> str:
        return _launch_name(name)

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
        launch_name = self.launch_config_name(name, commands)
        path = self.launch_config_path(launch_name, commands)
        path.write_text(self.layout_yaml(launch_name, commands), encoding="utf-8")
        self.cleanup_legacy_launch_configs(name, keep=path)
        self.cleanup_legacy_launch_configs(launch_name, keep=path)
        self.open_uri(f"warp://launch/{quote(launch_name, safe='')}")

    def open_command(self, cwd: Path, command: str, *, title: str) -> None:
        self.open_layout([OpenCommandSpec(title=title, cwd=cwd, command=command)], name=title)

    def open_project(self, cwd: Path) -> None:
        name = f"CC Branch Project {cwd.name or 'workspace'}"
        self.open_layout([OpenCommandSpec(title="Project", cwd=cwd, command=":")], name=name)

    def cleanup_legacy_launch_configs(self, name: str, *, keep: Path) -> None:
        legacy_pattern = f"{_slug(name)}-*.yaml"
        for path in keep.parent.glob(legacy_pattern):
            if path == keep:
                continue
            try:
                path.unlink()
            except OSError:
                continue


def _yaml_string(value: str) -> str:
    return json.dumps(value)


def _launch_name(value: str) -> str:
    return " ".join(value.replace(":", " ").split())


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
