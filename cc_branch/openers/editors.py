"""Editor workspace-file openers."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from .platform import _cache_dir, _popen, _slug
from .types import OpenCommandSpec, OpenerError, OpenerInfo


@dataclass(frozen=True)
class EditorWorkspaceOpener:
    """Opens editor folders and starts workspace commands where supported."""

    def open(self, opener_id: str, info: OpenerInfo, cwd: Path, commands: list[OpenCommandSpec]) -> None:
        if opener_id in {"vscode", "cursor"}:
            if commands:
                self.prepare_project_tasks(cwd, commands)
            self.open_project_folder(opener_id, info, cwd)
            return

        workspace_file = self.workspace_file_path(opener_id, cwd, commands)
        workspace_file.write_text(self.workspace_json(cwd, commands), encoding="utf-8")
        self.cleanup_stale_workspace_files(opener_id, cwd, keep=workspace_file)
        self.open_workspace_file(opener_id, info, workspace_file)

    def open_project_folder(self, opener_id: str, info: OpenerInfo, cwd: Path) -> None:
        executable = info.executable
        if not executable:
            raise OpenerError(f"Opener {opener_id} is not available")
        if opener_id in {"vscode", "cursor"}:
            _popen([executable, "-n", str(cwd)])
            return
        _popen([executable, str(cwd)])

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
        payload = {
            "folders": [{"path": str(cwd)}],
            "tasks": self.tasks_payload(commands),
        }
        return json.dumps(payload, indent=2) + "\n"

    def tasks_payload(self, commands: list[OpenCommandSpec]) -> dict:
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
                        "group": self.task_group(spec),
                        "clear": False,
                    },
                    "runOptions": {"runOn": "folderOpen"},
                }
            )
        return {
            "version": "2.0.0",
            "tasks": tasks,
        }

    def project_tasks_json(self, commands: list[OpenCommandSpec]) -> str:
        return json.dumps(self.tasks_payload(commands), indent=2) + "\n"

    def task_group(self, spec: OpenCommandSpec) -> str:
        """Return the VS Code split-terminal group for a command spec."""
        group_name = spec.split_group
        if group_name is None:
            tab_name, separator, _pane_name = spec.title.partition(":")
            group_name = tab_name if separator else spec.title
        return f"cc-branch:{group_name.strip() or 'workspace'}"

    def prepare_project_tasks(self, cwd: Path, commands: list[OpenCommandSpec]) -> None:
        sidecar = self.project_tasks_path(cwd)
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        self.ensure_generated_gitignore(sidecar.parent)
        sidecar.write_text(self.project_tasks_json(commands), encoding="utf-8")

        bridge = cwd / ".vscode" / "tasks.json"
        if bridge.exists() or bridge.is_symlink():
            if not self.is_cc_branch_tasks_bridge(bridge, sidecar):
                if not self.merge_project_tasks_bridge(bridge, commands):
                    raise OpenerError(
                        f"Cannot install VS Code/Cursor launch tasks because {bridge} "
                        "could not be parsed or updated. Fix that file, then open the workspace again."
                    )
                return
            bridge.unlink()
        bridge.parent.mkdir(parents=True, exist_ok=True)
        try:
            relative_target = os.path.relpath(sidecar, bridge.parent)
            bridge.symlink_to(relative_target)
        except OSError:
            bridge.write_text(sidecar.read_text(encoding="utf-8"), encoding="utf-8")

    def project_tasks_path(self, cwd: Path) -> Path:
        return cwd / ".cc-branch" / ".generated" / "vscode-tasks.json"

    def ensure_generated_gitignore(self, directory: Path) -> None:
        gitignore = directory / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n!.gitignore\n", encoding="utf-8")

    def is_cc_branch_tasks_bridge(self, bridge: Path, sidecar: Path) -> bool:
        if bridge.is_symlink():
            try:
                return bridge.resolve() == sidecar.resolve()
            except OSError:
                return False
        try:
            payload = _loads_tasks_json(bridge.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        tasks = payload.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            return False
        return all(isinstance(task, dict) and str(task.get("label", "")).startswith("cc-branch: ") for task in tasks)

    def merge_project_tasks_bridge(self, bridge: Path, commands: list[OpenCommandSpec]) -> bool:
        """Append generated cc-branch tasks to an existing user-owned tasks.json."""
        try:
            payload = _loads_tasks_json(bridge.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(payload, dict):
            return False
        existing_tasks = payload.get("tasks")
        if existing_tasks is None:
            existing_tasks = []
        if not isinstance(existing_tasks, list):
            return False

        generated_tasks = self.tasks_payload(commands)["tasks"]
        preserved_tasks = [
            task
            for task in existing_tasks
            if not (isinstance(task, dict) and str(task.get("label", "")).startswith("cc-branch: "))
        ]
        next_payload = {
            **payload,
            "version": str(payload.get("version") or "2.0.0"),
            "tasks": [*preserved_tasks, *generated_tasks],
        }
        try:
            bridge.write_text(json.dumps(next_payload, indent=2) + "\n", encoding="utf-8")
        except OSError:
            return False
        return True

    def open_workspace_file(self, opener_id: str, info: OpenerInfo, workspace_file: Path) -> None:
        executable = info.executable
        if not executable:
            raise OpenerError(f"Opener {opener_id} is not available")
        if opener_id in {"vscode", "cursor"}:
            _popen([executable, "-n", str(workspace_file)])
            return
        _popen([executable, str(workspace_file)])


editor_workspace_opener = EditorWorkspaceOpener()


def _loads_tasks_json(content: str) -> dict:
    """Load VS Code tasks JSON, accepting the JSONC syntax VS Code writes."""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        payload = json.loads(_strip_jsonc(content))
    if not isinstance(payload, dict):
        raise json.JSONDecodeError("tasks payload must be an object", content, 0)
    return payload


def _strip_jsonc(content: str) -> str:
    return _strip_trailing_commas(_strip_jsonc_comments(content))


def _strip_jsonc_comments(content: str) -> str:
    output: list[str] = []
    in_string = False
    escaped = False
    i = 0
    while i < len(content):
        char = content[i]
        next_char = content[i + 1] if i + 1 < len(content) else ""
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            i += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            i += 1
            continue
        if char == "/" and next_char == "/":
            i += 2
            while i < len(content) and content[i] not in "\r\n":
                i += 1
            continue
        if char == "/" and next_char == "*":
            i += 2
            while i + 1 < len(content) and not (content[i] == "*" and content[i + 1] == "/"):
                output.append("\n" if content[i] in "\r\n" else " ")
                i += 1
            i += 2 if i + 1 < len(content) else 0
            continue
        output.append(char)
        i += 1
    return "".join(output)


def _strip_trailing_commas(content: str) -> str:
    output: list[str] = []
    in_string = False
    escaped = False
    i = 0
    while i < len(content):
        char = content[i]
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            i += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            i += 1
            continue
        if char == ",":
            j = i + 1
            while j < len(content) and content[j].isspace():
                j += 1
            if j < len(content) and content[j] in "]}":
                i += 1
                continue
        output.append(char)
        i += 1
    return "".join(output)


def _editor_workspace_file_path(opener_id: str, cwd: Path, commands: list[OpenCommandSpec]) -> Path:
    return editor_workspace_opener.workspace_file_path(opener_id, cwd, commands)


def _cleanup_stale_editor_workspace_files(opener_id: str, cwd: Path, *, keep: Path) -> None:
    editor_workspace_opener.cleanup_stale_workspace_files(opener_id, cwd, keep=keep)


def _editor_workspace_json(cwd: Path, commands: list[OpenCommandSpec]) -> str:
    return editor_workspace_opener.workspace_json(cwd, commands)


def _open_editor_workspace_file(opener_id: str, info: OpenerInfo, workspace_file: Path) -> None:
    editor_workspace_opener.open_workspace_file(opener_id, info, workspace_file)
