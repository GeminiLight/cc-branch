import type { SlotConfig, WindowConfig } from "./types";

export type Selection = {
  slotIndex: number;
  target: "tab" | "pane";
  windowIndex: number | null;
};

export type TabLayout = NonNullable<SlotConfig["layout"]>;

export type CanvasPane = {
  name: string;
  agent: string | null;
  cwd: string | null;
  windowIndex: number | null;
  kind: "terminal" | "tmux-group";
};

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

export function emptyWindow(name = "main", agent: string | null = null): WindowConfig {
  return {
    name,
    agent,
    command: null,
    cwd: null,
    env: {},
    session: null,
    session_id: null,
    label: null,
    label_template: null,
    resume_mode: null,
    resume_template: null,
    create_mode: null,
    create_template: null,
    label_mode: null,
    rename_template: null,
  };
}

export function tmuxGroupWindowFromSlot(slot: SlotConfig): WindowConfig {
  return {
    ...emptyWindow(slot.name || "tmux"),
    layoutBackend: "tmux",
    cwd: slot.cwd || null,
    env: { ...slot.env },
    windows: slot.windows.length > 0 ? slot.windows : [emptyWindow("main")],
  };
}

export function tmuxGroupWindows(window: WindowConfig | null | undefined): WindowConfig[] {
  if (!window) return [emptyWindow("main")];
  if (window.windows && window.windows.length > 0) return window.windows;
  return [emptyWindow(window.name || "main", window.agent ?? null)];
}

export function terminalPaneName(slot: SlotConfig): string {
  return slot.title || slot.name || "terminal";
}

export function terminalSlotToWindow(slot: SlotConfig): WindowConfig {
  return {
    ...emptyWindow(terminalPaneName(slot), slot.agent ?? null),
    command: slot.agent ? null : slot.command ?? "$SHELL",
    cwd: slot.cwd || null,
    env: { ...slot.env },
    session: slot.session ?? null,
    session_id: slot.session_id ?? null,
    label: slot.label ?? null,
  };
}

export function slotToPanes(slot: SlotConfig): WindowConfig[] {
  if (isLegacyTmuxSlot(slot)) {
    return slot.windows.length > 0 ? slot.windows : [emptyWindow("main")];
  }
  return slot.windows.length > 0 ? slot.windows : [terminalSlotToWindow(slot)];
}

export function slotToCanvasPanes(slot: SlotConfig): CanvasPane[] {
  if (isLegacyTmuxSlot(slot)) {
    const agent = slot.windows.find((window) => window.agent)?.agent ?? null;
    return [{
      name: slot.name || "tmux",
      agent,
      cwd: slot.cwd || null,
      windowIndex: null,
      kind: "tmux-group",
    }];
  }
  const panes = slotToPanes(slot);
  return panes.map((pane, index) => ({
    name: slot.windows.length === 0 ? terminalPaneName(slot) : pane.name,
    agent: isTmuxGroupWindow(pane)
      ? tmuxGroupWindows(pane).find((window) => window.agent)?.agent ?? null
      : slot.windows.length === 0 ? slot.agent ?? null : pane.agent ?? null,
    cwd: pane.cwd || slot.cwd || null,
    windowIndex: slot.windows.length === 0 ? null : index,
    kind: isTmuxGroupWindow(pane) ? "tmux-group" : "terminal",
  }));
}

export function editableWindowsForSlot(slot: SlotConfig): WindowConfig[] {
  if (slot.windows.length > 0) return [...slot.windows];
  if (slot.runtime === "terminal") return [terminalSlotToWindow(slot)];
  return [emptyWindow("main")];
}

export function slotWithWindows(slot: SlotConfig, windows: WindowConfig[], layout?: TabLayout): SlotConfig {
  const hasTmuxGroup = windows.some(isTmuxGroupWindow);
  const next: SlotConfig = {
    ...slot,
    runtime: hasTmuxGroup ? "terminal" : slot.runtime,
    windows,
    ...(layout ? { layout } : {}),
  };
  if (next.runtime === "terminal") {
    return {
      ...next,
      command: undefined,
      title: undefined,
      agent: undefined,
      session: undefined,
      session_id: undefined,
      label: undefined,
    };
  }
  return next;
}

export function canDragPane(slot: SlotConfig): boolean {
  return isLegacyTmuxSlot(slot) || slot.windows.length > 0;
}

export function clampSelection(selection: Selection, slots: SlotConfig[]): Selection {
  if (slots.length === 0) return { slotIndex: 0, target: "tab", windowIndex: null };
  const slotIndex = Math.min(Math.max(selection.slotIndex, 0), slots.length - 1);
  const slot = slots[slotIndex];
  if (selection.target === "tab") return { slotIndex, target: "tab", windowIndex: null };
  if (isLegacyTmuxSlot(slot)) {
    return { slotIndex, target: "pane", windowIndex: null };
  }
  if (slot.runtime === "terminal" && slot.windows.length === 0) {
    return { slotIndex, target: "pane", windowIndex: null };
  }
  const maxWindow = Math.max(slotToPanes(slot).length - 1, 0);
  return {
    slotIndex,
    target: "pane",
    windowIndex: Math.min(Math.max(selection.windowIndex ?? 0, 0), maxWindow),
  };
}

export function normalizedLayout(slot: SlotConfig, paneLength: number): TabLayout {
  const layout = slot.layout || "auto";
  if (layout !== "auto") return layout;
  if (paneLength <= 2) return "horizontal";
  if (paneLength === 3) return "main-left";
  return "grid";
}
