import type { SlotConfig, WindowConfig } from "./types";

export interface WorkspaceNameValidation {
  duplicateTabNames: string[];
  hasEmptyTabNames: boolean;
  hasEmptyPaneNames: boolean;
  reservedTargetNames: string[];
}

const TARGET_NAME_SEPARATOR_RE = /[:.]/;

function hasEmptyWindowName(window: WindowConfig): boolean {
  return window.name.trim().length === 0 || Boolean(window.windows?.some(hasEmptyWindowName));
}

function reservedWindowNames(window: WindowConfig): string[] {
  const name = window.name.trim();
  return [
    ...(name && TARGET_NAME_SEPARATOR_RE.test(name) ? [name] : []),
    ...(window.windows ?? []).flatMap(reservedWindowNames),
  ];
}

export function validateWorkspaceNames(slots: SlotConfig[]): WorkspaceNameValidation {
  const tabNames = slots.map((slot) => slot.name.trim()).filter(Boolean);
  const duplicateTabNames = [...new Set(tabNames.filter((name, index, arr) => arr.indexOf(name) !== index))];
  const reservedTargetNames = [
    ...slots.flatMap((slot) => {
      const name = slot.name.trim();
      return name && TARGET_NAME_SEPARATOR_RE.test(name) ? [name] : [];
    }),
    ...slots.flatMap((slot) => slot.windows.flatMap(reservedWindowNames)),
  ];

  return {
    duplicateTabNames,
    hasEmptyTabNames: slots.some((slot) => slot.name.trim().length === 0),
    hasEmptyPaneNames: slots.some((slot) => slot.windows.some(hasEmptyWindowName)),
    reservedTargetNames: [...new Set(reservedTargetNames)],
  };
}
