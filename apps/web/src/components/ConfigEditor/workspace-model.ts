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

export type WorkspaceMutation = {
  slots: SlotConfig[];
  selection: Selection;
};

export type PaneSplitLayout = Extract<TabLayout, "horizontal" | "vertical">;

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

export function uniqueName(existingNames: string[], base: string): string {
  const names = new Set(existingNames.map((name) => name.trim()).filter(Boolean));
  const normalizedBase = base.trim() || "item";
  let name = normalizedBase;
  let i = 1;
  while (names.has(name)) {
    name = `${normalizedBase}-${i}`;
    i++;
  }
  return name;
}

export function uniqueTabName(slots: SlotConfig[], base = "coding"): string {
  return uniqueName(slots.map((slot) => slot.name), base);
}

function copyNameBase(name: string | undefined, fallback: string): string {
  return `${name?.trim() || fallback}-copy`;
}

export function addTabMutation(
  slots: SlotConfig[],
): WorkspaceMutation {
  const name = uniqueTabName(slots);
  const nextSlot: SlotConfig = {
    name,
    runtime: "terminal",
    layout: "auto",
    cwd: ".",
    env: {},
    command: "$SHELL",
    windows: [],
  };
  return {
    slots: [...slots, nextSlot],
    selection: {
      slotIndex: slots.length,
      target: "tab",
      windowIndex: null,
    },
  };
}

export function deleteTabMutation(slots: SlotConfig[], index: number): WorkspaceMutation | null {
  if (index < 0 || index >= slots.length) return null;
  const next = [...slots];
  next.splice(index, 1);
  return {
    slots: next,
    selection: { slotIndex: Math.max(0, index - 1), target: "tab", windowIndex: null },
  };
}

export function addPaneMutation(
  slots: SlotConfig[],
  slotIndex: number,
  agents: string[],
  afterIndex?: number,
  layout?: PaneSplitLayout,
): WorkspaceMutation | null {
  const slot = slots[slotIndex];
  if (!slot) return null;
  if (isLegacyTmuxSlot(slot)) {
    const panes = [tmuxGroupWindowFromSlot(slot)];
    panes.push(emptyWindow(uniqueName(panes.map((pane) => pane.name), "pane-2"), agents[0] ?? null));
    const next = [...slots];
    next[slotIndex] = slotWithWindows(slot, panes, layout || slot.layout || "auto");
    return {
      slots: next,
      selection: { slotIndex, target: "pane", windowIndex: 1 },
    };
  }

  const windows = editableWindowsForSlot(slot);
  const insertAt = afterIndex == null ? windows.length : Math.min(afterIndex + 1, windows.length);
  windows.splice(insertAt, 0, emptyWindow(uniqueName(windows.map((window) => window.name), `pane-${windows.length + 1}`), agents[0] ?? null));
  const next = [...slots];
  next[slotIndex] = slotWithWindows(slot, windows, layout || slot.layout || "auto");
  return {
    slots: next,
    selection: { slotIndex, target: "pane", windowIndex: slot.runtime === "tmux" ? null : insertAt },
  };
}

export function addTmuxGroupPaneMutation(
  slots: SlotConfig[],
  slotIndex: number,
  agents: string[],
  afterIndex?: number,
): WorkspaceMutation | null {
  const slot = slots[slotIndex];
  if (!slot) return null;
  const panes = isLegacyTmuxSlot(slot) ? [tmuxGroupWindowFromSlot(slot)] : editableWindowsForSlot(slot);
  const insertAt = afterIndex == null ? panes.length : Math.min(afterIndex + 1, panes.length);
  const groupName = uniqueName(panes.map((pane) => pane.name), "tmux-group");
  panes.splice(insertAt, 0, {
    ...emptyWindow(groupName),
    layoutBackend: "tmux",
    windows: [emptyWindow("main", agents[0] ?? null)],
  });
  const next = [...slots];
  next[slotIndex] = slotWithWindows(slot, panes, slot.layout || "auto");
  return {
    slots: next,
    selection: { slotIndex, target: "pane", windowIndex: insertAt },
  };
}

export function duplicatePaneMutation(
  slots: SlotConfig[],
  slotIndex: number,
  windowIndex: number | null,
): WorkspaceMutation | null {
  const slot = slots[slotIndex];
  if (!slot) return null;
  if (slot.runtime === "terminal" && slot.windows.length === 0) {
    const copy: SlotConfig = {
      ...slot,
      name: uniqueTabName(slots, copyNameBase(slot.name, "tab")),
      title: slot.title ? `${slot.title}-copy` : slot.title,
      windows: [],
    };
    const next = [...slots];
    next.splice(slotIndex + 1, 0, copy);
    return {
      slots: next,
      selection: { slotIndex: slotIndex + 1, target: "pane", windowIndex: null },
    };
  }

  const sourceIndex = windowIndex ?? 0;
  const windows = editableWindowsForSlot(slot);
  const sourceWindow = windows[sourceIndex];
  if (!sourceWindow) return null;
  const insertAt = sourceIndex + 1;
  windows.splice(insertAt, 0, {
    ...sourceWindow,
    name: uniqueName(windows.map((window) => window.name), copyNameBase(sourceWindow.name, "pane")),
  });
  const next = [...slots];
  next[slotIndex] = slotWithWindows(slot, windows);
  return {
    slots: next,
    selection: { slotIndex, target: "pane", windowIndex: insertAt },
  };
}

export function deletePaneMutation(
  slots: SlotConfig[],
  slotIndex: number,
  windowIndex: number | null,
): WorkspaceMutation | null {
  const slot = slots[slotIndex];
  if (!slot) return null;
  if (slot.runtime === "terminal" && slot.windows.length === 0) {
    return deleteTabMutation(slots, slotIndex);
  }

  const targetIndex = windowIndex ?? 0;
  const windows = editableWindowsForSlot(slot);
  if (targetIndex < 0 || targetIndex >= windows.length) return null;
  windows.splice(targetIndex, 1);
  if (windows.length === 0) {
    return deleteTabMutation(slots, slotIndex);
  }

  const next = [...slots];
  next[slotIndex] = slotWithWindows(slot, windows);
  return {
    slots: next,
    selection: {
      slotIndex,
      target: "pane",
      windowIndex: slot.runtime === "tmux" ? null : Math.max(0, targetIndex - 1),
    },
  };
}

function updateTmuxWindowsInSlot(
  slot: SlotConfig,
  paneIndex: number | null,
  updateWindows: (windows: WindowConfig[]) => WindowConfig[] | null,
): SlotConfig | null {
  if (isLegacyTmuxSlot(slot)) {
    const windows = updateWindows([...slot.windows]);
    if (!windows) return null;
    return { ...slot, windows };
  }

  const targetPaneIndex = paneIndex ?? 0;
  const pane = slot.windows[targetPaneIndex];
  if (!isTmuxGroupWindow(pane)) return null;
  const windows = updateWindows(tmuxGroupWindows(pane));
  if (!windows) return null;
  const panes = [...slot.windows];
  panes[targetPaneIndex] = { ...pane, windows };
  return { ...slot, windows: panes };
}

function updateTmuxWindowsMutation(
  slots: SlotConfig[],
  slotIndex: number,
  paneIndex: number | null,
  updateWindows: (windows: WindowConfig[]) => WindowConfig[] | null,
): SlotConfig[] | null {
  const slot = slots[slotIndex];
  if (!slot) return null;
  const nextSlot = updateTmuxWindowsInSlot(slot, paneIndex, updateWindows);
  if (!nextSlot) return null;
  const next = [...slots];
  next[slotIndex] = nextSlot;
  return next;
}

export function updateTmuxWindowMutation(
  slots: SlotConfig[],
  slotIndex: number,
  paneIndex: number | null,
  tmuxWindowIndex: number,
  patch: Partial<WindowConfig>,
): SlotConfig[] | null {
  return updateTmuxWindowsMutation(slots, slotIndex, paneIndex, (windows) => {
    const target = windows[tmuxWindowIndex];
    if (!target) return null;
    const next = [...windows];
    next[tmuxWindowIndex] = { ...target, ...patch };
    return next;
  });
}

export function addTmuxWindowMutation(
  slots: SlotConfig[],
  slotIndex: number,
  paneIndex: number | null,
): SlotConfig[] | null {
  return updateTmuxWindowsMutation(slots, slotIndex, paneIndex, (windows) => {
    const name = uniqueName(windows.map((window) => window.name), `window-${windows.length + 1}`);
    return [...windows, emptyWindow(name)];
  });
}

export function moveTmuxWindowMutation(
  slots: SlotConfig[],
  slotIndex: number,
  paneIndex: number | null,
  tmuxWindowIndex: number,
  dir: number,
): SlotConfig[] | null {
  return updateTmuxWindowsMutation(slots, slotIndex, paneIndex, (windows) => {
    const targetIndex = tmuxWindowIndex + dir;
    if (targetIndex < 0 || targetIndex >= windows.length) return null;
    const next = [...windows];
    const [moved] = next.splice(tmuxWindowIndex, 1);
    if (!moved) return null;
    next.splice(targetIndex, 0, moved);
    return next;
  });
}

export function deleteTmuxWindowMutation(
  slots: SlotConfig[],
  slotIndex: number,
  paneIndex: number | null,
  tmuxWindowIndex: number,
): SlotConfig[] | null {
  return updateTmuxWindowsMutation(slots, slotIndex, paneIndex, (windows) => {
    if (windows.length <= 1 || tmuxWindowIndex < 0 || tmuxWindowIndex >= windows.length) return null;
    return windows.filter((_, index) => index !== tmuxWindowIndex);
  });
}

export function movePaneWithinTabMutation(
  slots: SlotConfig[],
  slotIndex: number,
  windowIndex: number,
  dir: number,
): WorkspaceMutation | null {
  const slot = slots[slotIndex];
  if (!slot || (slot.runtime === "terminal" && slot.windows.length === 0)) return null;
  const targetIndex = windowIndex + dir;
  const windows = editableWindowsForSlot(slot);
  if (windowIndex < 0 || windowIndex >= windows.length) return null;
  if (targetIndex < 0 || targetIndex >= windows.length) return null;
  const [moved] = windows.splice(windowIndex, 1);
  if (!moved) return null;
  windows.splice(targetIndex, 0, moved);
  const next = [...slots];
  next[slotIndex] = slotWithWindows(slot, windows);
  return {
    slots: next,
    selection: { slotIndex, target: "pane", windowIndex: slot.runtime === "tmux" ? null : targetIndex },
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
  return isLegacyTmuxSlot(slot) || slot.runtime === "terminal" || slot.windows.length > 0;
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

export function moveTab(slots: SlotConfig[], fromSlotIndex: number, toSlotIndex: number, selection: Selection): WorkspaceMutation | null {
  if (fromSlotIndex < 0 || fromSlotIndex >= slots.length) return null;
  const next = [...slots];
  const selectedBeforeMove = slots[selection.slotIndex];
  const [moved] = next.splice(fromSlotIndex, 1);
  if (!moved) return null;
  const insertIndex = Math.min(
    Math.max(fromSlotIndex < toSlotIndex ? toSlotIndex - 1 : toSlotIndex, 0),
    next.length
  );
  next.splice(insertIndex, 0, moved);
  const nextSelectedIndex = selectedBeforeMove ? Math.max(next.indexOf(selectedBeforeMove), 0) : insertIndex;
  return {
    slots: next,
    selection: {
      slotIndex: nextSelectedIndex,
      target: selection.target,
      windowIndex: selection.windowIndex,
    },
  };
}

export function movePaneBetweenSlots(
  slots: SlotConfig[],
  fromSlotIndex: number,
  fromPaneIndex: number,
  toSlotIndex: number,
  toPaneIndex: number,
): WorkspaceMutation | null {
  const source = slots[fromSlotIndex];
  const target = slots[toSlotIndex];
  if (!source || !target) return null;
  if (fromSlotIndex === toSlotIndex && isLegacyTmuxSlot(source)) return null;
  if (fromSlotIndex === toSlotIndex && fromPaneIndex === toPaneIndex) return null;
  if (fromPaneIndex < 0) return null;

  if (fromSlotIndex === toSlotIndex) {
    if (source.windows.length === 0) return null;
    const windows = editableWindowsForSlot(source);
    if (fromPaneIndex >= windows.length) return null;
    const [moved] = windows.splice(fromPaneIndex, 1);
    if (!moved) return null;
    const insertIndex = Math.min(
      Math.max(fromPaneIndex < toPaneIndex ? toPaneIndex - 1 : toPaneIndex, 0),
      windows.length
    );
    windows.splice(insertIndex, 0, moved);
    const next = [...slots];
    next[fromSlotIndex] = slotWithWindows(source, windows);
    return {
      slots: next,
      selection: { slotIndex: fromSlotIndex, target: "pane", windowIndex: insertIndex },
    };
  }

  const sourceIsLegacyTmuxGroup = isLegacyTmuxSlot(source);
  if (sourceIsLegacyTmuxGroup && fromPaneIndex !== 0) return null;
  const sourceWindows = sourceIsLegacyTmuxGroup ? [] : editableWindowsForSlot(source);
  if (!sourceIsLegacyTmuxGroup && fromPaneIndex >= sourceWindows.length) return null;

  const moved = sourceIsLegacyTmuxGroup
    ? tmuxGroupWindowFromSlot(source)
    : sourceWindows.splice(fromPaneIndex, 1)[0];
  if (!moved) return null;

  const targetWindows = isLegacyTmuxSlot(target) ? [tmuxGroupWindowFromSlot(target)] : editableWindowsForSlot(target);
  const insertIndex = Math.min(Math.max(toPaneIndex, 0), targetWindows.length);
  targetWindows.splice(insertIndex, 0, moved);

  const next = [...slots];
  if (sourceIsLegacyTmuxGroup || sourceWindows.length === 0) {
    next.splice(fromSlotIndex, 1);
    const adjustedTargetIndex = fromSlotIndex < toSlotIndex ? toSlotIndex - 1 : toSlotIndex;
    next[adjustedTargetIndex] = slotWithWindows(target, targetWindows);
    return {
      slots: next,
      selection: { slotIndex: adjustedTargetIndex, target: "pane", windowIndex: insertIndex },
    };
  }

  next[fromSlotIndex] = slotWithWindows(source, sourceWindows);
  next[toSlotIndex] = slotWithWindows(target, targetWindows);
  return {
    slots: next,
    selection: { slotIndex: toSlotIndex, target: "pane", windowIndex: insertIndex },
  };
}
