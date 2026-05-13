"""OpenCommandSpec builders for workspace action open policies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...openers import OpenCommandSpec
from ...runtime.capabilities import is_external_process_runtime


@dataclass(frozen=True)
class WorkspaceCommandSpecs:
    """Builds terminal/editor command specifications from planned slots and windows."""

    def terminal_command_specs(self, slots, *, windows=None) -> list[OpenCommandSpec]:
        specs: list[OpenCommandSpec] = []
        if windows is not None and len(slots) == 1:
            slot = slots[0]
            for window in windows:
                specs.append(
                    OpenCommandSpec(
                        title=f"{slot.name}:{window.name}",
                        cwd=Path(window.cwd),
                        command=window.launch_command,
                        split_group=slot.name,
                    )
                )
            return specs
        for slot in slots:
            for window in slot.windows:
                specs.append(
                    OpenCommandSpec(
                        title=f"{slot.name}:{window.name}",
                        cwd=Path(window.cwd),
                        command=window.launch_command,
                        split_group=slot.name,
                    )
                )
        return specs

    def tmux_slot_attach_specs(self, slots, cli: str) -> list[OpenCommandSpec]:
        return [
            OpenCommandSpec(
                title=slot.name,
                cwd=Path(slot.cwd),
                command=f"{cli} attach {slot.name}",
                split_group=slot.name,
            )
            for slot in slots
        ]

    def tmux_window_attach_specs(self, slots, cli: str) -> list[OpenCommandSpec]:
        specs: list[OpenCommandSpec] = []
        for slot in slots:
            if not slot.windows:
                specs.extend(self.tmux_slot_attach_specs([slot], cli))
                continue
            for window in slot.windows:
                target = f"{slot.name}:{window.name}"
                specs.append(
                    OpenCommandSpec(
                        title=target,
                        cwd=Path(window.cwd),
                        command=f"{cli} attach {target}",
                        split_group=slot.name,
                    )
                )
        return specs

    def attach_target_specs(self, slot, window, target: str, cli: str) -> list[OpenCommandSpec]:
        if is_external_process_runtime(slot.runtime):
            windows = [window] if window is not None else slot.windows
            return self.terminal_command_specs([slot], windows=windows)
        if window is not None:
            return [
                OpenCommandSpec(
                    title=target,
                    cwd=Path(window.cwd),
                    command=f"{cli} attach {target}",
                    split_group=slot.name,
                )
            ]
        return self.tmux_window_attach_specs([slot], cli)


command_specs = WorkspaceCommandSpecs()


def _terminal_command_specs(slots, *, windows=None) -> list[OpenCommandSpec]:
    return command_specs.terminal_command_specs(slots, windows=windows)


def _tmux_slot_attach_specs(slots, cli: str) -> list[OpenCommandSpec]:
    return command_specs.tmux_slot_attach_specs(slots, cli)


def _tmux_window_attach_specs(slots, cli: str) -> list[OpenCommandSpec]:
    return command_specs.tmux_window_attach_specs(slots, cli)


def _attach_target_specs(slot, window, target: str, cli: str) -> list[OpenCommandSpec]:
    return command_specs.attach_target_specs(slot, window, target, cli)
