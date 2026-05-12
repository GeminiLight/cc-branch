"""Editor workspace-file openers."""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .platform import _cache_dir, _popen, _slug
from .types import OpenCommandSpec, OpenerError, OpenerInfo


@dataclass(frozen=True)
class EditorWorkspaceOpener:
    """Opens editor folders and starts workspace commands where supported."""

    def open(self, opener_id: str, info: OpenerInfo, cwd: Path, commands: list[OpenCommandSpec]) -> None:
        if opener_id in {"vscode", "cursor"}:
            self.open_project_folder(opener_id, info, cwd)
            if commands and sys.platform == "darwin":
                self.open_integrated_terminals_macos(opener_id, cwd, commands)
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

    def open_integrated_terminals_macos(self, opener_id: str, cwd: Path, commands: list[OpenCommandSpec]) -> None:
        app_info = {
            "vscode": ("Visual Studio Code", "Code"),
            "cursor": ("Cursor", "Cursor"),
        }.get(opener_id)
        if not app_info:
            raise OpenerError(f"Opener {opener_id} cannot create integrated terminals")
        app_name, process_name = app_info

        rendered_commands = [self._terminal_command(cwd, spec) for spec in commands]
        script = self._macos_terminal_script(app_name, process_name, rendered_commands)
        try:
            result = subprocess.run(
                ["osascript", *[arg for line in script.splitlines() for arg in ("-e", line)]],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=max(20, len(rendered_commands) * 8),
            )
        except subprocess.TimeoutExpired as error:
            raise OpenerError(f"{app_name} terminal automation timed out") from error
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise OpenerError(
                f"Opened project in {app_name}, but could not create integrated terminals. "
                "Grant Accessibility permission to the terminal or app running cc-branch, then try again."
                + (f" Details: {detail}" if detail else "")
            )

    def _terminal_command(self, workspace_cwd: Path, spec: OpenCommandSpec) -> str:
        if spec.cwd == workspace_cwd:
            return spec.command
        return f"cd {shlex.quote(str(spec.cwd))} && {spec.command}"

    def _macos_terminal_script(self, app_name: str, process_name: str, commands: list[str]) -> str:
        command_list = ", ".join(json.dumps(command) for command in commands)
        return f"""
set commandList to {{{command_list}}}
set previousClipboard to the clipboard
tell application {json.dumps(app_name)} to activate
delay 1.4
tell application "System Events"
  tell process {json.dumps(process_name)}
    set frontmost to true
    delay 0.2
    repeat with commandText in commandList
      key code 50 using {{control down, shift down}}
      delay 0.5
      set the clipboard to commandText as text
      keystroke "v" using {{command down}}
      key code 36
      delay 0.4
    end repeat
  end tell
end tell
set the clipboard to previousClipboard
"""

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
