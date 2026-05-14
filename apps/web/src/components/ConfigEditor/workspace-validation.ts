import type { SlotConfig, WindowConfig } from "./types";

export interface WorkspaceNameValidation {
  duplicateTabNames: string[];
  hasEmptyTabNames: boolean;
  hasEmptyPaneNames: boolean;
}

function hasEmptyWindowName(window: WindowConfig): boolean {
  return window.name.trim().length === 0 || Boolean(window.windows?.some(hasEmptyWindowName));
}

export function validateWorkspaceNames(slots: SlotConfig[]): WorkspaceNameValidation {
  const tabNames = slots.map((slot) => slot.name.trim()).filter(Boolean);
  const duplicateTabNames = [...new Set(tabNames.filter((name, index, arr) => arr.indexOf(name) !== index))];

  return {
    duplicateTabNames,
    hasEmptyTabNames: slots.some((slot) => slot.name.trim().length === 0),
    hasEmptyPaneNames: slots.some((slot) => slot.windows.some(hasEmptyWindowName)),
  };
}
