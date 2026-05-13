import type { SlotConfig, WindowConfig } from "./types";
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
