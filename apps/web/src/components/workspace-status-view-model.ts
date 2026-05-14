import type { SlotInfo } from "../types";

export function tabGroupName(slot: SlotInfo): string {
  return slot.split_group || slot.name;
}

export function workspaceTabCount(slots: SlotInfo[]): number {
  return new Set(slots.map(tabGroupName)).size;
}

export function runningWorkspaceTabCount(slots: SlotInfo[]): number {
  const runningTabs = new Set<string>();
  for (const slot of slots) {
    if (slot.status === "running") {
      runningTabs.add(tabGroupName(slot));
    }
  }
  return runningTabs.size;
}

export function tabPaneCount(slot: SlotInfo): number {
  if (slot.runtime === "tmux") return 1;
  return Math.max(slot.windows.length, 1);
}
