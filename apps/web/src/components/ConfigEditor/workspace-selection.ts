import type { SlotConfig, WindowConfig, WorkspaceEditTarget } from "./types";
import {
  clampSelection,
  isLegacyTmuxSlot,
  isTmuxGroupWindow,
  type Selection,
} from "./workspace-model";

export type WorkspaceSelectionState = {
  normalizedSelection: Selection;
  selectedSlot: SlotConfig | undefined;
  selectedWindow: WindowConfig | null;
  selectedTerminalPane: boolean;
  selectedTerminalWindow: WindowConfig | null;
  selectedTmuxGroup: boolean;
  editingPane: boolean;
};

export function deriveWorkspaceSelection(slots: SlotConfig[], selection: Selection): WorkspaceSelectionState {
  const normalizedSelection = clampSelection(selection, slots);
  const selectedSlot = slots[normalizedSelection.slotIndex];
  const selectedWindow =
    normalizedSelection.target === "pane" && !isLegacyTmuxSlot(selectedSlot) && selectedSlot?.windows.length
      ? selectedSlot.windows[normalizedSelection.windowIndex ?? 0]
      : null;
  const selectedTerminalPane =
    normalizedSelection.target === "pane" &&
    selectedSlot?.runtime === "terminal" &&
    selectedSlot.windows.length === 0;
  const selectedTerminalWindow = selectedSlot?.runtime === "terminal" && !isTmuxGroupWindow(selectedWindow)
    ? selectedWindow
    : null;
  const selectedTmuxGroup =
    normalizedSelection.target === "pane" &&
    (isLegacyTmuxSlot(selectedSlot) || isTmuxGroupWindow(selectedWindow));
  const editingPane = Boolean(selectedWindow || selectedTerminalPane || selectedTmuxGroup);

  return {
    normalizedSelection,
    selectedSlot,
    selectedWindow,
    selectedTerminalPane,
    selectedTerminalWindow,
    selectedTmuxGroup,
    editingPane,
  };
}

function paneSelectionForSlot(
  slots: SlotConfig[],
  slotIndex: number,
  windowName?: string,
): Selection {
  const slot = slots[slotIndex];
  if (!slot) return { slotIndex: 0, target: "tab", windowIndex: null };
  if (isLegacyTmuxSlot(slot) || slot.windows.length === 0) {
    return { slotIndex, target: "pane", windowIndex: null };
  }
  if (windowName) {
    const directIndex = slot.windows.findIndex((window) => window.name === windowName);
    if (directIndex >= 0) return { slotIndex, target: "pane", windowIndex: directIndex };
    const groupIndex = slot.windows.findIndex((window) =>
      isTmuxGroupWindow(window) && window.windows?.some((child) => child.name === windowName)
    );
    if (groupIndex >= 0) return { slotIndex, target: "pane", windowIndex: groupIndex };
  }
  return { slotIndex, target: "pane", windowIndex: 0 };
}

export function selectionForWorkspaceTarget(
  slots: SlotConfig[],
  target: WorkspaceEditTarget,
): Selection | null {
  const slotName = target.slotName.trim();
  const windowName = target.windowName?.trim();
  if (!slotName) return null;

  const exactSlotIndex = slots.findIndex((slot) => slot.name === slotName);
  if (exactSlotIndex >= 0) {
    return paneSelectionForSlot(slots, exactSlotIndex, windowName);
  }

  for (let slotIndex = 0; slotIndex < slots.length; slotIndex += 1) {
    const slot = slots[slotIndex];
    const windowIndex = slot.windows.findIndex((window) => {
      const splitSlotName = `${slot.name}-${window.name}`;
      if (splitSlotName !== slotName) return false;
      if (!windowName) return true;
      return (
        window.name === windowName ||
        (isTmuxGroupWindow(window) && window.windows?.some((child) => child.name === windowName))
      );
    });
    if (windowIndex >= 0) return { slotIndex, target: "pane", windowIndex };
  }

  return null;
}
