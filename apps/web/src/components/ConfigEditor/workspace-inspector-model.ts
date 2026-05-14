import type { SlotConfig } from "./types";
import { paneCount } from "./workspace-display";
import { isLegacyTmuxSlot } from "./workspace-model";
import type { WorkspaceSelectionState } from "./workspace-selection";

type Translate = (key: string, vars?: Record<string, string | number>) => string;

export type MoveTargetOption = { value: string; label: string };

export function selectedMoveTargetIndex(value: string): number {
  return value === "" ? -1 : Number(value);
}

export function inspectorSelectionSubtitle(
  state: WorkspaceSelectionState,
  t: Translate,
): string {
  const slot = state.selectedSlot;
  if (!slot) return t("unnamed");
  if (!state.editingPane) return slot.name || t("unnamed");
  if (state.selectedTmuxGroup) {
    if (isLegacyTmuxSlot(slot)) return slot.name || t("unnamed");
    return state.selectedWindow?.name || slot.name || t("unnamed");
  }
  return state.selectedWindow?.name || slot.title || slot.name || t("unnamed");
}

export function isSelectedPaneMovable(state: WorkspaceSelectionState): boolean {
  return state.normalizedSelection.target === "pane" && Boolean(
    state.selectedWindow || state.selectedTmuxGroup || state.selectedTerminalPane,
  );
}

export function moveTargetOptionsForSelection(
  slots: SlotConfig[],
  state: WorkspaceSelectionState,
  t: Translate,
): MoveTargetOption[] {
  if (!state.selectedSlot || state.normalizedSelection.target !== "pane") return [];
  return slots
    .map((slot, index) => ({ slot, index }))
    .filter(({ index }) => index !== state.normalizedSelection.slotIndex)
    .map(({ slot, index }) => ({
      value: String(index),
      label: `${slot.name || t("unnamed")} · ${t("tabSummaryPanes", { count: paneCount(slot) })}`,
    }));
}

export function canMoveSelectedPaneToTarget(
  state: WorkspaceSelectionState,
  targetIndex: number,
): boolean {
  return Boolean(
    isSelectedPaneMovable(state) &&
      targetIndex >= 0 &&
      targetIndex !== state.normalizedSelection.slotIndex,
  );
}

export function selectedPaneOrderState(state: WorkspaceSelectionState): {
  canMoveUp: boolean;
  canMoveDown: boolean;
} {
  const slot = state.selectedSlot;
  const windowIndex = state.normalizedSelection.windowIndex ?? 0;
  return {
    canMoveUp: Boolean(slot && slot.windows.length > 0 && windowIndex > 0),
    canMoveDown: Boolean(slot && slot.windows.length > 0 && windowIndex < slot.windows.length - 1),
  };
}

export function selectedTmuxGroupPositionState(
  slots: SlotConfig[],
  state: WorkspaceSelectionState,
): {
  isLegacy: boolean;
  canMoveUp: boolean;
  canMoveDown: boolean;
} {
  const isLegacy = Boolean(state.selectedTmuxGroup && isLegacyTmuxSlot(state.selectedSlot));
  const windowIndex = state.normalizedSelection.windowIndex ?? 0;
  return {
    isLegacy,
    canMoveUp: isLegacy
      ? state.normalizedSelection.slotIndex > 0
      : Boolean(state.selectedTmuxGroup && windowIndex > 0),
    canMoveDown: isLegacy
      ? state.normalizedSelection.slotIndex < slots.length - 1
      : Boolean(
          state.selectedSlot &&
            state.selectedTmuxGroup &&
            windowIndex < state.selectedSlot.windows.length - 1,
        ),
  };
}
