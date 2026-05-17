import { displayAgentName } from "../ui/AgentMark";
import type { SlotConfig, WindowConfig } from "./types";
import {
  configuredPaneCount,
  isLegacyTmuxSlot,
  isTmuxGroupWindow,
  slotToCanvasPanes,
  tmuxGroupWindows,
} from "./workspace-model";

type Translate = (key: string, vars?: Record<string, string | number>) => string;

export function countText(
  t: Translate,
  singularKey: string,
  pluralKey: string,
  count: number,
): string {
  return t(count === 1 ? singularKey : pluralKey, { count });
}

export function paneCount(slot: SlotConfig): number {
  return configuredPaneCount(slot);
}

export function paneCountText(t: Translate, count: number): string {
  return t(count === 1 ? "windowCountShortOne" : "windowCountShort", { count });
}

export function paneSummary(t: Translate, win: WindowConfig): string {
  if (win.agent) return t("paneSummaryAgent", { agent: displayAgentName(win.agent) });
  if (win.command) return t("paneSummaryCommand", { command: win.command });
  return t("paneSummaryInherited");
}

export function terminalPaneSummary(t: Translate, slot: SlotConfig): string {
  if (slot.agent) return t("paneSummaryAgent", { agent: displayAgentName(slot.agent) });
  return t("paneSummaryCommand", { command: slot.command || "$SHELL" });
}

export function tabSummary(t: Translate, slot: SlotConfig): string {
  if (isLegacyTmuxSlot(slot)) {
    return countText(t, "tmuxWindowGroupSummary_one", "tmuxWindowGroupSummary", slot.windows.length);
  }
  const panes = slotToCanvasPanes(slot);
  if (panes.length > 1) return paneCountText(t, panes.length);
  if (slot.windows.length === 1) {
    const window = slot.windows[0];
    return isTmuxGroupWindow(window)
      ? countText(t, "tmuxWindowGroupSummary_one", "tmuxWindowGroupSummary", tmuxGroupWindows(window).length)
      : paneSummary(t, window);
  }
  if (slot.agent) return t("tabSummaryTerminalAgent", { agent: displayAgentName(slot.agent) });
  return t("tabSummaryCommand", { command: slot.command || "$SHELL" });
}
