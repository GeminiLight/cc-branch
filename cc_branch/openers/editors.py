"""Editor workspace-file openers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .platform import _cache_dir, _popen, _slug
from .types import OpenCommandSpec, OpenerError, OpenerInfo


@dataclass(frozen=True)
class EditorWorkspaceOpener:
    """Creates and opens generated editor workspace files for command tasks."""

    def open(self, opener_id: str, info: OpenerInfo, cwd: Path, commands: list[OpenCommandSpec]) -> None:
        workspace_file = self.workspace_file_path(opener_id, cwd, commands)
        workspace_file.write_text(self.workspace_json(cwd, commands), encoding="utf-8")
        self.cleanup_stale_workspace_files(opener_id, cwd, keep=workspace_file)
        self.open_workspace_file(opener_id, info, workspace_file)

    def workspace_file_path(self, opener_id: str, cwd: Path, commands: list[OpenCommandSpec]) -> Path:
        digest_source = f"{opener_id}\0{cwd}\0" + "\n".join(
            f"{spec.title}\0{spec.cwd}\0{spec.command}" for spec in commands
        )
        digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:12]
        directory = _cache_dir() / "editor-workspaces"
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{_slug(cwd.name or 'workspace')}-{opener_id}-{digest}.code-workspace"

    def cleanup_stale_workspace_files(self, opener_id: str, cwd: Path, *, keep: Path) -> None:
        pattern = f"{_slug(cwd.name or 'workspace')}-{opener_id}-*.code-workspace"
        for path in keep.parent.glob(pattern):
            if path == keep:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                folders = payload.get("folders", [])
                if not any(
                    isinstance(folder, dict)
                    and isinstance(folder.get("path"), str)
                    and Path(folder["path"]).expanduser().resolve() == cwd
                    for folder in folders
                ):
                    continue
                path.unlink()
            except (OSError, json.JSONDecodeError):
                continue

    def workspace_json(self, cwd: Path, commands: list[OpenCommandSpec]) -> str:
        tasks = []
        for spec in commands:
            tasks.append(
                {
                    "label": f"cc-branch: {spec.title}",
                    "type": "shell",
                    "command": spec.command,
                    "options": {"cwd": str(spec.cwd)},
                    "problemMatcher": [],
                    "presentation": {
                        "reveal": "always",
                        "panel": "dedicated",
                        "group": "cc-branch",
                        "clear": False,
                    },
                    "runOptions": {"runOn": "folderOpen"},
                }
            )
        payload = {
            "folders": [{"path": str(cwd)}],
            "tasks": {
                "version": "2.0.0",
                "tasks": tasks,
            },
        }
        return json.dumps(payload, indent=2) + "\n"

    def open_workspace_file(self, opener_id: str, info: OpenerInfo, workspace_file: Path) -> None:
        executable = info.executable
        if not executable:
            raise OpenerError(f"Opener {opener_id} is not available")
        if opener_id in {"vscode", "cursor"}:
            _popen([executable, "-n", str(workspace_file)])
            return
        _popen([executable, str(workspace_file)])


editor_workspace_opener = EditorWorkspaceOpener()


def _editor_workspace_file_path(opener_id: str, cwd: Path, commands: list[OpenCommandSpec]) -> Path:
    return editor_workspace_opener.workspace_file_path(opener_id, cwd, commands)


def _cleanup_stale_editor_workspace_files(opener_id: str, cwd: Path, *, keep: Path) -> None:
    editor_workspace_opener.cleanup_stale_workspace_files(opener_id, cwd, keep=keep)


def _editor_workspace_json(cwd: Path, commands: list[OpenCommandSpec]) -> str:
    return editor_workspace_opener.workspace_json(cwd, commands)


def _open_editor_workspace_file(opener_id: str, info: OpenerInfo, workspace_file: Path) -> None:
    editor_workspace_opener.open_workspace_file(opener_id, info, workspace_file)
