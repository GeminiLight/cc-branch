import type { SlotConfig, WindowConfig } from "./types";

export function isTmuxGroupWindow(window: WindowConfig | null | undefined): boolean {
  return Boolean(window && (window.layoutBackend === "tmux" || window.windows?.length));
}

export function isLegacyTmuxSlot(slot: SlotConfig | null | undefined): boolean {
  return Boolean(slot && slot.runtime === "tmux" && !slot.windows.some(isTmuxGroupWindow));
}

export function configuredPaneCount(slot: SlotConfig): number {
  if (isLegacyTmuxSlot(slot)) return 1;
  return Math.max(slot.windows.length, 1);
}
