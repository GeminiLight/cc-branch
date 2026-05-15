import type { SlotConfig, WindowConfig } from "./types";

export interface WorkspaceNameValidation {
  duplicateTabNames: string[];
  duplicatePaneNames: string[];
  hasEmptyTabNames: boolean;
  hasEmptyPaneNames: boolean;
  missingLaunchTargets: string[];
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

function windowMissingLaunchTargets(scope: string, windows: WindowConfig[]): string[] {
  return windows.flatMap((window) => {
    const windowName = window.name.trim() || "unnamed";
    const target = `${scope}/${windowName}`;
    if (window.windows) {
      if (window.windows.length > 0) {
        return windowMissingLaunchTargets(target, window.windows);
      }
      return window.agent || window.command ? [] : [target];
    }
    return window.agent || window.command ? [] : [target];
  });
}

function duplicateNames(names: string[]): string[] {
  const seen = new Set<string>();
  const duplicates = new Set<string>();
  for (const rawName of names) {
    const name = rawName.trim();
    if (!name) continue;
    if (seen.has(name)) duplicates.add(name);
    seen.add(name);
  }
  return [...duplicates];
}

function scopedDuplicateWindowNames(scope: string, windows: WindowConfig[]): string[] {
  const directDuplicates = duplicateNames(windows.map((window) => window.name)).map((name) => `${scope}/${name}`);
  const nestedDuplicates = windows.flatMap((window) => {
    if (!window.windows) return [];
    const windowName = window.name.trim() || "unnamed";
    return scopedDuplicateWindowNames(`${scope}/${windowName}`, window.windows);
  });
  return [...directDuplicates, ...nestedDuplicates];
}

export function validateWorkspaceNames(slots: SlotConfig[]): WorkspaceNameValidation {
  const tabNames = slots.map((slot) => slot.name.trim()).filter(Boolean);
  const duplicateTabNames = [...new Set(tabNames.filter((name, index, arr) => arr.indexOf(name) !== index))];
  const duplicatePaneNames = slots.flatMap((slot) => {
    const slotName = slot.name.trim() || "unnamed";
    return scopedDuplicateWindowNames(slotName, slot.windows);
  });
  const missingLaunchTargets = slots.flatMap((slot) => {
    const slotName = slot.name.trim() || "unnamed";
    if (slot.windows.length > 0) return windowMissingLaunchTargets(slotName, slot.windows);
    return slot.agent || slot.command ? [] : [slotName];
  });
  const reservedTargetNames = [
    ...slots.flatMap((slot) => {
      const name = slot.name.trim();
      return name && TARGET_NAME_SEPARATOR_RE.test(name) ? [name] : [];
    }),
    ...slots.flatMap((slot) => slot.windows.flatMap(reservedWindowNames)),
  ];

  return {
    duplicateTabNames,
    duplicatePaneNames: [...new Set(duplicatePaneNames)],
    hasEmptyTabNames: slots.some((slot) => slot.name.trim().length === 0),
    hasEmptyPaneNames: slots.some((slot) => slot.windows.some(hasEmptyWindowName)),
    missingLaunchTargets: [...new Set(missingLaunchTargets)],
    reservedTargetNames: [...new Set(reservedTargetNames)],
  };
}
