import type { SlotConfig, WindowConfig } from "./types";

export function isTmuxGroupWindow(window: WindowConfig | null | undefined): boolean {
  return Boolean(window && (window.layoutBackend === "tmux" || Array.isArray(window.windows)));
}

export function isLegacyTmuxSlot(slot: SlotConfig | null | undefined): boolean {
  return Boolean(slot && slot.runtime === "tmux" && !slot.windows.some(isTmuxGroupWindow));
}

export function configuredPaneCount(slot: SlotConfig): number {
  if (isLegacyTmuxSlot(slot)) return 1;
  return Math.max(slot.windows.length, 1);
}
