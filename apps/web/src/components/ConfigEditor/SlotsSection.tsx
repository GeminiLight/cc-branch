/**
 * ConfigEditor — Workspace canvas for Tab / Pane layout editing.
 *
 * The persisted schema is still slots/windows. The UI presents those as
 * tabs/panes so users edit the workspace model, not the storage model.
 */

import { useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import {
  ArrowDown,
  ArrowUp,
  ChevronDown,
  Plus,
  Trash2,
} from "lucide-react";
import { useI18n } from "../../i18n";
import type { RuntimeAvailability, WorkspaceScope } from "../../types";
import AgentMark, { displayAgentName } from "../ui/AgentMark";
import type { SlotConfig, WindowConfig } from "./types";
import {
  MoveToTabActions,
  PaneSchedulingActions,
  RemovePaneAction,
  TmuxGroupPositionActions,
} from "./InspectorActions";
import LayoutPicker from "./LayoutPicker";
import SessionInput from "./SessionInput";
import WorkspaceCanvas from "./WorkspaceCanvas";
import {
  FieldLabel,
  TextInput,
  SelectInput,
  KeyValueList,
  InlineError,
} from "./FormPrimitives";
import {
  canDragPane,
  clampSelection,
  editableWindowsForSlot,
  emptyWindow,
  isLegacyTmuxSlot,
  isTmuxGroupWindow,
  movePaneBetweenSlots,
  moveTab as moveTabModel,
  normalizedLayout,
  slotWithWindows,
  tmuxGroupWindowFromSlot,
  tmuxGroupWindows,
  type Selection,
  type TabLayout,
} from "./workspace-model";
import { countText, paneCount } from "./workspace-display";

type PaneDragState = { slotIndex: number; paneIndex: number } | null;
type TabDragState = { slotIndex: number } | null;

function runtimeLabel(t: (key: string, vars?: Record<string, string | number>) => string, runtime: SlotConfig["runtime"]): string {
  return runtime === "terminal" ? t("runtimeTerminal") : t("runtimeTmux");
}

export default function SlotsSection({
  slots,
  agents,
  scope,
  onChange,
  runtimeAvailability,
}: {
  slots: SlotConfig[];
  agents: string[];
  scope?: WorkspaceScope;
  onChange: (slots: SlotConfig[]) => void;
  runtimeAvailability?: RuntimeAvailability;
}) {
  const { t } = useI18n();
  const defaultRuntime = runtimeAvailability?.tmux?.available === false ? "terminal" : "tmux";
  const [selection, setSelection] = useState<Selection>({ slotIndex: 0, target: "tab", windowIndex: null });
  const [moveTarget, setMoveTarget] = useState("0");
  const [paneDrag, setPaneDrag] = useState<PaneDragState>(null);
  const [tabDrag, setTabDrag] = useState<TabDragState>(null);
  const paneDragRef = useRef<PaneDragState>(null);

  const normalizedSelection = useMemo(() => clampSelection(selection, slots), [selection, slots]);
  const selectedSlot = slots[normalizedSelection.slotIndex];
  const selectedWindow =
    normalizedSelection.target === "pane" && !isLegacyTmuxSlot(selectedSlot) && selectedSlot?.windows.length
      ? selectedSlot.windows[normalizedSelection.windowIndex ?? 0]
      : null;
  const selectedTerminalPane =
    normalizedSelection.target === "pane" &&
    selectedSlot?.runtime === "terminal" &&
    selectedSlot.windows.length === 0;
  const selectedTerminalWindow = selectedSlot?.runtime === "terminal" && !isTmuxGroupWindow(selectedWindow) ? selectedWindow : null;
  const selectedTmuxGroup = normalizedSelection.target === "pane" && (isLegacyTmuxSlot(selectedSlot) || isTmuxGroupWindow(selectedWindow));
  const editingPane = Boolean(selectedWindow || selectedTerminalPane || selectedTmuxGroup);

  useEffect(() => {
    const next = clampSelection(selection, slots);
    if (
      next.slotIndex !== selection.slotIndex ||
      next.target !== selection.target ||
      next.windowIndex !== selection.windowIndex
    ) {
      setSelection(next);
    }
  }, [selection, slots]);

  const agentOptions = [
    { value: "", label: t("noneOption") },
    ...agents.map((agent) => ({ value: agent, label: agent })),
  ];
  const layoutOptions = [
    { value: "auto", label: t("layoutAuto") },
    { value: "horizontal", label: t("layoutHorizontal") },
    { value: "vertical", label: t("layoutVertical") },
    { value: "main-left", label: t("layoutMainLeft") },
    { value: "main-top", label: t("layoutMainTop") },
    { value: "grid", label: t("layoutGrid") },
  ];

  const moveTargetOptions = useMemo(() => {
    if (!selectedSlot || normalizedSelection.target !== "pane") return [];
    return slots
      .map((slot, index) => ({ slot, index }))
      .filter(({ index }) => index !== normalizedSelection.slotIndex)
      .map(({ slot, index }) => ({
        value: String(index),
        label: `${slot.name || t("unnamed")} · ${t("tabSummaryPanes", { count: paneCount(slot) })}`,
      }));
  }, [normalizedSelection.slotIndex, normalizedSelection.target, selectedSlot, slots, t]);

  useEffect(() => {
    if (moveTargetOptions.length === 0) {
      if (moveTarget !== "") setMoveTarget("");
      return;
    }
    if (!moveTargetOptions.some((option) => option.value === moveTarget)) {
      setMoveTarget(moveTargetOptions[0].value);
    }
  }, [moveTarget, moveTargetOptions]);

  const selectedMoveTargetIndex = moveTarget === "" ? -1 : Number(moveTarget);
  const selectedMovablePane = normalizedSelection.target === "pane" && Boolean(selectedWindow || selectedTmuxGroup);
  const canMovePaneToSelectedTab = Boolean(
    selectedMovablePane &&
    selectedMoveTargetIndex >= 0 &&
    selectedMoveTargetIndex !== normalizedSelection.slotIndex
  );

  function updateSlot(index: number, patch: Partial<SlotConfig>) {
    const next = [...slots];
    next[index] = { ...next[index], ...patch };
    onChange(next);
  }

  function replaceSlots(next: SlotConfig[], nextSelection?: Selection) {
    onChange(next);
    if (nextSelection) setSelection(nextSelection);
  }

  function addTab() {
    const names = new Set(slots.map((slot) => slot.name));
    let name = "coding";
    let i = 1;
    while (names.has(name)) {
      name = `coding-${i}`;
      i++;
    }
    const nextSlot: SlotConfig = {
      name,
      runtime: defaultRuntime,
      layout: "auto",
      cwd: ".",
      env: {},
      ...(defaultRuntime === "terminal"
        ? agents[0]
          ? { agent: agents[0] }
          : { command: "$SHELL" }
        : {}),
      windows: defaultRuntime === "tmux" ? [emptyWindow("builder", agents[0] ?? null)] : [],
    };
    replaceSlots([...slots, nextSlot], {
      slotIndex: slots.length,
      target: "tab",
      windowIndex: null,
    });
  }

  function deleteTab(index: number) {
    const next = [...slots];
    next.splice(index, 1);
    replaceSlots(next, { slotIndex: Math.max(0, index - 1), target: "tab", windowIndex: null });
  }

  function moveTabByDrag(fromSlotIndex: number, toSlotIndex: number) {
    const mutation = moveTabModel(slots, fromSlotIndex, toSlotIndex, normalizedSelection);
    if (!mutation) return;
    replaceSlots(mutation.slots, mutation.selection);
  }

  function moveTab(index: number, dir: number) {
    if (dir < 0) {
      moveTabByDrag(index, index - 1);
      return;
    }
    moveTabByDrag(index, index + 2);
  }

  function handleTabDragStart(event: DragEvent<HTMLElement>, slotIndex: number) {
    setTabDrag({ slotIndex });
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", `tab:${slotIndex}`);
  }

  function handleTabDragOver(event: DragEvent<HTMLElement>) {
    if (!tabDrag) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }

  function handleTabDrop(event: DragEvent<HTMLElement>, slotIndex: number) {
    event.preventDefault();
    event.stopPropagation();
    if (!tabDrag) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const after = event.clientY > rect.top + rect.height / 2;
    moveTabByDrag(tabDrag.slotIndex, slotIndex + (after ? 1 : 0));
    setTabDrag(null);
  }

  function updateWindow(index: number, patch: Partial<WindowConfig>) {
    if (!selectedSlot || selectedSlot.windows.length === 0) return;
    const windows = [...selectedSlot.windows];
    windows[index] = { ...windows[index], ...patch };
    updateSlot(normalizedSelection.slotIndex, { windows });
  }

  function splitSelectedPane(layout: Extract<TabLayout, "horizontal" | "vertical">) {
    if (!selectedSlot) return;
    addPaneToSlot(normalizedSelection.slotIndex, normalizedSelection.windowIndex ?? 0, layout);
  }

  function addPaneToSlot(slotIndex: number, afterIndex?: number, layout?: Extract<TabLayout, "horizontal" | "vertical">) {
    const slot = slots[slotIndex];
    if (!slot) return;
    if (isLegacyTmuxSlot(slot)) {
      const panes = [tmuxGroupWindowFromSlot(slot), emptyWindow("pane-2", agents[0] ?? null)];
      const next = [...slots];
      next[slotIndex] = slotWithWindows(slot, panes, layout || slot.layout || "auto");
      replaceSlots(next, { slotIndex, target: "pane", windowIndex: 1 });
      return;
    }
    const windows = editableWindowsForSlot(slot);
    const insertAt = afterIndex == null ? windows.length : Math.min(afterIndex + 1, windows.length);
    windows.splice(insertAt, 0, emptyWindow(`pane-${windows.length + 1}`, agents[0] ?? null));
    const next = [...slots];
    next[slotIndex] = slotWithWindows(slot, windows, layout || slot.layout || "auto");
    replaceSlots(next, { slotIndex, target: "pane", windowIndex: slot.runtime === "tmux" ? null : insertAt });
  }

  function duplicatePane() {
    if (!selectedSlot) return;
    duplicatePaneAtSlot(normalizedSelection.slotIndex, normalizedSelection.windowIndex ?? null);
  }

  function duplicatePaneAtSlot(slotIndex: number, windowIndex: number | null) {
    const slot = slots[slotIndex];
    if (!slot) return;
    if (slot.runtime === "terminal" && slot.windows.length === 0) {
      const copy: SlotConfig = {
        ...slot,
        name: `${slot.name || "tab"}-copy`,
        title: slot.title ? `${slot.title}-copy` : slot.title,
        windows: [],
      };
      const next = [...slots];
      next.splice(slotIndex + 1, 0, copy);
      replaceSlots(next, { slotIndex: slotIndex + 1, target: "pane", windowIndex: null });
      return;
    }
    const sourceIndex = windowIndex ?? 0;
    const windows = editableWindowsForSlot(slot);
    const sourceWindow = windows[sourceIndex];
    if (!sourceWindow) return;
    const insertAt = sourceIndex + 1;
    windows.splice(insertAt, 0, { ...sourceWindow, name: `${sourceWindow.name || "pane"}-copy` });
    const next = [...slots];
    next[slotIndex] = slotWithWindows(slot, windows);
    replaceSlots(next, { slotIndex, target: "pane", windowIndex: insertAt });
  }

  function deletePane() {
    if (!selectedSlot) return;
    deletePaneAtSlot(normalizedSelection.slotIndex, normalizedSelection.windowIndex ?? null);
  }

  function deletePaneAtSlot(slotIndex: number, windowIndex: number | null) {
    const slot = slots[slotIndex];
    if (!slot) return;
    if (slot.runtime === "terminal" && slot.windows.length === 0) {
      deleteTab(slotIndex);
      return;
    }
    const targetIndex = windowIndex ?? 0;
    const windows = editableWindowsForSlot(slot);
    windows.splice(targetIndex, 1);
    if (windows.length === 0) {
      deleteTab(slotIndex);
      return;
    }
    const next = [...slots];
    next[slotIndex] = slotWithWindows(slot, windows);
    replaceSlots(next, {
      slotIndex,
      target: "pane",
      windowIndex: slot.runtime === "tmux" ? null : Math.max(0, targetIndex - 1),
    });
  }

  function movePane(dir: number) {
    movePaneAt(normalizedSelection.windowIndex ?? 0, dir);
  }

  function movePaneAt(windowIndex: number, dir: number) {
    movePaneAtSlot(normalizedSelection.slotIndex, windowIndex, dir);
  }

  function movePaneAtSlot(slotIndex: number, windowIndex: number, dir: number) {
    const slot = slots[slotIndex];
    if (!slot || (slot.runtime === "terminal" && slot.windows.length === 0)) return;
    const targetIndex = windowIndex + dir;
    const windows = editableWindowsForSlot(slot);
    if (targetIndex < 0 || targetIndex >= windows.length) return;
    const [moved] = windows.splice(windowIndex, 1);
    windows.splice(targetIndex, 0, moved);
    const next = [...slots];
    next[slotIndex] = slotWithWindows(slot, windows);
    replaceSlots(next, { slotIndex, target: "pane", windowIndex: slot.runtime === "tmux" ? null : targetIndex });
  }

  function movePaneByDrag(fromSlotIndex: number, fromPaneIndex: number, toSlotIndex: number, toPaneIndex: number) {
    const mutation = movePaneBetweenSlots(slots, fromSlotIndex, fromPaneIndex, toSlotIndex, toPaneIndex);
    if (!mutation) return;
    replaceSlots(mutation.slots, mutation.selection);
  }

  function handlePaneDragStart(event: DragEvent<HTMLElement>, slotIndex: number, paneIndex: number) {
    const slot = slots[slotIndex];
    if (!slot || !canDragPane(slot)) return;
    event.stopPropagation();
    const nextDrag = { slotIndex, paneIndex };
    paneDragRef.current = nextDrag;
    setPaneDrag(nextDrag);
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", `${slotIndex}:${paneIndex}`);
  }

  function paneDragFromEvent(event: DragEvent<HTMLElement>): PaneDragState {
    const payload = event.dataTransfer.getData("text/plain");
    const match = payload.match(/^(\d+):(\d+)$/);
    if (!match) return null;
    return { slotIndex: Number(match[1]), paneIndex: Number(match[2]) };
  }

  function handlePaneDragOver(event: DragEvent<HTMLElement>, slotIndex: number) {
    const target = slots[slotIndex];
    const currentDrag = paneDragRef.current ?? paneDrag ?? paneDragFromEvent(event);
    const source = currentDrag ? slots[currentDrag.slotIndex] : null;
    if (!currentDrag || !target || !source) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }

  function handlePaneDrop(event: DragEvent<HTMLElement>, slotIndex: number, paneIndex: number) {
    event.preventDefault();
    event.stopPropagation();
    const currentDrag = paneDragRef.current ?? paneDrag ?? paneDragFromEvent(event);
    if (!currentDrag) return;
    const target = slots[slotIndex];
    const rect = event.currentTarget.getBoundingClientRect();
    const layout = target ? normalizedLayout(target, paneCount(target)) : "horizontal";
    const verticalDrop = layout === "vertical" || layout === "main-top";
    const after =
      verticalDrop
        ? event.clientY > rect.top + rect.height / 2
        : event.clientX > rect.left + rect.width / 2;
    movePaneByDrag(currentDrag.slotIndex, currentDrag.paneIndex, slotIndex, paneIndex + (after ? 1 : 0));
    paneDragRef.current = null;
    setPaneDrag(null);
  }

  function handlePaneAppendDrop(event: DragEvent<HTMLElement>, slotIndex: number) {
    event.preventDefault();
    event.stopPropagation();
    const target = slots[slotIndex];
    const currentDrag = paneDragRef.current ?? paneDrag ?? paneDragFromEvent(event);
    const source = currentDrag ? slots[currentDrag.slotIndex] : null;
    if (!currentDrag || !target || !source) return;
    movePaneByDrag(currentDrag.slotIndex, currentDrag.paneIndex, slotIndex, paneCount(target));
    paneDragRef.current = null;
    setPaneDrag(null);
  }

  function movePaneToTab() {
    if (!selectedSlot || !selectedMovablePane) return;
    const targetIndex = selectedMoveTargetIndex;
    const target = slots[targetIndex];
    if (!target || targetIndex === normalizedSelection.slotIndex) return;
    const mutation = movePaneBetweenSlots(
      slots,
      normalizedSelection.slotIndex,
      normalizedSelection.windowIndex ?? 0,
      targetIndex,
      paneCount(target),
    );
    if (!mutation) return;
    replaceSlots(mutation.slots, mutation.selection);
  }

  const selectedTmuxWindowList = selectedTmuxGroup
    ? isLegacyTmuxSlot(selectedSlot)
      ? selectedSlot.windows
      : selectedWindow
      ? tmuxGroupWindows(selectedWindow)
      : []
    : [];

  function updateSelectedTmuxGroupName(value: string) {
    if (!selectedSlot) return;
    if (isLegacyTmuxSlot(selectedSlot)) {
      updateSlot(normalizedSelection.slotIndex, { name: value });
      return;
    }
    if (selectedWindow) updateWindow(normalizedSelection.windowIndex ?? 0, { name: value });
  }

  function updateSelectedTmuxWindow(windowIndex: number, patch: Partial<WindowConfig>) {
    if (!selectedSlot) return;
    if (isLegacyTmuxSlot(selectedSlot)) {
      updateWindow(windowIndex, patch);
      return;
    }
    if (!selectedWindow) return;
    const windows = tmuxGroupWindows(selectedWindow);
    windows[windowIndex] = { ...windows[windowIndex], ...patch };
    updateWindow(normalizedSelection.windowIndex ?? 0, { windows });
  }

  function addSelectedTmuxWindow() {
    if (!selectedSlot) return;
    if (isLegacyTmuxSlot(selectedSlot)) {
      const windows = [...selectedSlot.windows, emptyWindow(`window-${selectedSlot.windows.length + 1}`)];
      updateSlot(normalizedSelection.slotIndex, { windows });
      return;
    }
    if (!selectedWindow) return;
    const windows = [...tmuxGroupWindows(selectedWindow), emptyWindow(`window-${tmuxGroupWindows(selectedWindow).length + 1}`)];
    updateWindow(normalizedSelection.windowIndex ?? 0, { windows });
  }

  function moveSelectedTmuxWindow(windowIndex: number, dir: number) {
    const targetIndex = windowIndex + dir;
    if (targetIndex < 0 || targetIndex >= selectedTmuxWindowList.length) return;
    const windows = [...selectedTmuxWindowList];
    const [moved] = windows.splice(windowIndex, 1);
    if (!moved) return;
    windows.splice(targetIndex, 0, moved);
    if (isLegacyTmuxSlot(selectedSlot)) {
      updateSlot(normalizedSelection.slotIndex, { windows });
    } else if (selectedWindow) {
      updateWindow(normalizedSelection.windowIndex ?? 0, { windows });
    }
  }

  function deleteSelectedTmuxWindow(windowIndex: number) {
    if (selectedTmuxWindowList.length <= 1) return;
    const windows = selectedTmuxWindowList.filter((_, index) => index !== windowIndex);
    if (isLegacyTmuxSlot(selectedSlot)) {
      updateSlot(normalizedSelection.slotIndex, { windows });
    } else if (selectedWindow) {
      updateWindow(normalizedSelection.windowIndex ?? 0, { windows });
    }
  }

  const dupNames = slots
    .map((slot) => slot.name)
    .filter((name, index, arr) => arr.indexOf(name) !== index);
  const emptyNames = slots.filter((slot) => !slot.name.trim());
  const emptyWindows = slots.filter(
    (slot) => slot.windows.some((win) => !win.name.trim())
  );
  const canMoveSelectedPaneUp = Boolean(selectedSlot && selectedSlot.windows.length > 0 && (normalizedSelection.windowIndex ?? 0) > 0);
  const canMoveSelectedPaneDown = Boolean(
    selectedSlot &&
    selectedSlot.windows.length > 0 &&
    (normalizedSelection.windowIndex ?? 0) < selectedSlot.windows.length - 1
  );
  const selectedTmuxGroupIsLegacy = Boolean(selectedTmuxGroup && isLegacyTmuxSlot(selectedSlot));
  const canMoveSelectedGroupUp = selectedTmuxGroupIsLegacy
    ? normalizedSelection.slotIndex > 0
    : Boolean(selectedTmuxGroup && (normalizedSelection.windowIndex ?? 0) > 0);
  const canMoveSelectedGroupDown = selectedTmuxGroupIsLegacy
    ? normalizedSelection.slotIndex < slots.length - 1
    : Boolean(selectedSlot && selectedTmuxGroup && (normalizedSelection.windowIndex ?? 0) < selectedSlot.windows.length - 1);

  function moveSelectedTmuxGroup(dir: number) {
    if (selectedTmuxGroupIsLegacy) {
      moveTab(normalizedSelection.slotIndex, dir);
      return;
    }
    movePane(dir);
  }

  function deleteSelectedTmuxGroup() {
    if (selectedTmuxGroupIsLegacy) {
      deleteTab(normalizedSelection.slotIndex);
      return;
    }
    deletePaneAtSlot(normalizedSelection.slotIndex, normalizedSelection.windowIndex ?? 0);
  }

  function clearPaneDrag() {
    paneDragRef.current = null;
    setPaneDrag(null);
  }

  const canvasProps = {
    slots,
    selection: normalizedSelection,
    tabDrag,
    paneDrag,
    onAddTab: addTab,
    onDeleteTab: deleteTab,
    onAddPane: addPaneToSlot,
    onSelect: setSelection,
    onTabDragStart: handleTabDragStart,
    onTabDragOver: handleTabDragOver,
    onTabDrop: handleTabDrop,
    onTabDragEnd: () => setTabDrag(null),
    onPaneDragStart: handlePaneDragStart,
    onPaneDragOver: handlePaneDragOver,
    onPaneDrop: handlePaneDrop,
    onPaneAppendDrop: handlePaneAppendDrop,
    onPaneDragEnd: clearPaneDrag,
  };

  return (
    <section className="space-y-3 animate-stagger">
          {dupNames.length > 0 && (
            <InlineError message={t("duplicateSlotNames", { names: [...new Set(dupNames)].join(", ") })} />
          )}
          {emptyNames.length > 0 && (
            <InlineError message={t("allSlotsMustHaveName")} />
          )}
          {emptyWindows.length > 0 && (
            <InlineError message={t("allWindowsMustHaveName")} />
          )}

          {slots.length === 0 ? (
            <WorkspaceCanvas {...canvasProps} />
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_360px] gap-3 items-start">
              <WorkspaceCanvas {...canvasProps} />

              {selectedSlot && (
                <aside className="rounded-lg border border-default bg-[var(--bg-card)] overflow-hidden xl:sticky xl:top-3">
                  <div className="px-3 py-3 border-b border-subtle bg-[var(--bg-card)]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("inspector")}</p>
                    <div className="mt-1 flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <h3 className="text-[15px] font-semibold text-primary">
                          {editingPane ? t("selectedPane") : t("selectedTab")}
                        </h3>
                        <p className="mt-0.5 truncate text-[11px] text-tertiary">
                          {editingPane
                            ? selectedTmuxGroup
                              ? selectedSlot.name || t("unnamed")
                              : selectedWindow?.name ?? selectedSlot.title ?? selectedSlot.name
                            : selectedSlot.name || t("unnamed")}
                        </p>
                      </div>
                      <span className="inline-flex shrink-0 items-center rounded-md border border-default bg-[var(--bg-hover)] px-2 py-1 text-[10px] font-semibold text-tertiary">
                        {selectedTmuxGroup ? t("tmuxWindowStack") : editingPane ? t("pane") : t("tab")}
                      </span>
                    </div>
                  </div>

                  <div className="p-3 space-y-3">
                    {!editingPane && (
                    <section className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("tab")}</p>
                        <span className="text-[10px] text-tertiary">{t("tabGroup")}</span>
                      </div>
                      <div>
                        <FieldLabel required>{t("tabName")}</FieldLabel>
                        <TextInput
                          value={selectedSlot.name}
                          onChange={(value) => updateSlot(normalizedSelection.slotIndex, { name: value })}
                          placeholder="coding"
                          invalid={!selectedSlot.name.trim()}
                        />
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-1 gap-2.5">
                        <div>
                          <FieldLabel>{t("tabLayout")}</FieldLabel>
                          <LayoutPicker
                            value={selectedSlot.layout || "auto"}
                            options={layoutOptions}
                            onChange={(value) => updateSlot(normalizedSelection.slotIndex, { layout: value })}
                          />
                        </div>
                      </div>
                    </section>
                    )}

                    {editingPane && (
                    <section className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("pane")}</p>
                        <span className="text-[10px] text-tertiary">{runtimeLabel(t, selectedSlot.runtime)}</span>
                      </div>
	                      {selectedSlot.runtime === "terminal" && !selectedTmuxGroup ? (
                        <div className="space-y-2.5">
                          <div>
                            <FieldLabel>{t("title")}</FieldLabel>
                            <TextInput
                              value={selectedTerminalWindow?.name ?? selectedSlot.title ?? ""}
                              onChange={(value) => {
                                if (selectedTerminalWindow) updateWindow(normalizedSelection.windowIndex ?? 0, { name: value });
                                else updateSlot(normalizedSelection.slotIndex, { title: value || undefined });
                              }}
                              placeholder="main"
                            />
                          </div>
                          <div>
                            <FieldLabel>{t("agent")}</FieldLabel>
                            <SelectInput
                              value={selectedTerminalWindow?.agent ?? selectedSlot.agent ?? ""}
                              onChange={(value) => {
                                if (selectedTerminalWindow) {
                                  updateWindow(normalizedSelection.windowIndex ?? 0, {
                                    agent: value || null,
                                    command: value ? null : selectedTerminalWindow.command,
                                    session: value ? selectedTerminalWindow.session ?? "auto" : null,
                                  });
                                } else {
                                  updateSlot(normalizedSelection.slotIndex, {
                                    agent: value || undefined,
                                    command: value ? undefined : selectedSlot.command,
                                    session: value ? selectedSlot.session ?? "auto" : undefined,
                                  });
                                }
                              }}
                              options={agentOptions}
                            />
                          </div>
                          {(selectedTerminalWindow?.agent ?? selectedSlot.agent) ? (
                            <div>
                              <FieldLabel>{t("agentSession")}</FieldLabel>
                              <SessionInput
                                value={selectedTerminalWindow?.session ?? selectedTerminalWindow?.session_id ?? selectedSlot.session ?? selectedSlot.session_id ?? "auto"}
                                onChange={(value) => {
                                  if (selectedTerminalWindow) updateWindow(normalizedSelection.windowIndex ?? 0, { session: value || null, session_id: null });
                                  else updateSlot(normalizedSelection.slotIndex, { session: value || undefined, session_id: undefined });
                                }}
                                agent={selectedTerminalWindow?.agent ?? selectedSlot.agent}
                                scope={scope}
                              />
                            </div>
                          ) : (
                            <div>
                              <FieldLabel>{t("shellCommand")}</FieldLabel>
                              <TextInput
                                value={selectedTerminalWindow?.command ?? selectedSlot.command ?? ""}
                                onChange={(value) => {
                                  if (selectedTerminalWindow) updateWindow(normalizedSelection.windowIndex ?? 0, { command: value || null });
                                  else updateSlot(normalizedSelection.slotIndex, { command: value || undefined });
                                }}
                                placeholder="$SHELL"
                              />
                            </div>
                          )}
                          <details className="group rounded-md border border-default bg-[var(--bg-card)]">
                            <summary className="flex items-center gap-2 px-3 py-2 cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-tertiary hover:text-secondary">
                              <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" />
                              {t("advanced")}
                            </summary>
                            <div className="px-3 pb-3 pt-1 space-y-2.5">
                              <div>
                                <FieldLabel>{t("workingDirectory")}</FieldLabel>
                                <TextInput
                                  value={selectedTerminalWindow?.cwd ?? selectedSlot.cwd ?? ""}
                                  onChange={(value) => {
                                    if (selectedTerminalWindow) updateWindow(normalizedSelection.windowIndex ?? 0, { cwd: value || null });
                                    else updateSlot(normalizedSelection.slotIndex, { cwd: value || "." });
                                  }}
                                  placeholder="."
                                />
                              </div>
                              <div>
                                <FieldLabel>{t("environmentVariables")}</FieldLabel>
                                <KeyValueList
                                  items={selectedTerminalWindow?.env ?? selectedSlot.env}
                                  onChange={(env) => {
                                    if (selectedTerminalWindow) updateWindow(normalizedSelection.windowIndex ?? 0, { env });
                                    else updateSlot(normalizedSelection.slotIndex, { env });
                                  }}
                                />
                              </div>
                            </div>
                          </details>
                        </div>
                      ) : selectedTmuxGroup ? (
                        <div className="space-y-3">
                          <div>
	                            <FieldLabel required>{t("paneName")}</FieldLabel>
	                            <TextInput
	                              value={isLegacyTmuxSlot(selectedSlot) ? selectedSlot.name : selectedWindow?.name ?? ""}
	                              onChange={updateSelectedTmuxGroupName}
	                              placeholder="tmux"
	                              invalid={!(isLegacyTmuxSlot(selectedSlot) ? selectedSlot.name : selectedWindow?.name ?? "").trim()}
	                            />
                          </div>
                          <div className="rounded-md border border-default bg-[var(--bg-hover)]/30 p-2.5">
                            <div className="flex items-center justify-between gap-2">
                              <div className="min-w-0">
	                                <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("tmuxWindows")}</p>
	                                <p className="mt-0.5 text-[11px] text-tertiary">
	                                  {countText(t, "tmuxWindowGroupSummary_one", "tmuxWindowGroupSummary", selectedTmuxWindowList.length)}
	                                </p>
                              </div>
                              <button
                                type="button"
	                                onClick={addSelectedTmuxWindow}
                                className="control-touch rounded-md border border-default bg-[var(--bg-card)] px-2.5 text-[11px] font-semibold text-secondary hover:border-[var(--border-strong)] hover:text-primary transition-colors inline-flex items-center gap-1.5"
                              >
                                <Plus className="h-3.5 w-3.5 text-tertiary" />
                                {t("addTmuxWindow")}
                              </button>
                            </div>
                            <div className="mt-2 space-y-2">
	                              {selectedTmuxWindowList.map((window, windowIndex) => (
                                <div
                                  key={`${window.name}-${windowIndex}-detail`}
                                  className="rounded-md border border-default bg-[var(--bg-card)] p-2 shadow-sm"
                                >
                                  <div className="mb-2 flex items-center justify-between gap-2">
                                    <div className="flex min-w-0 items-center gap-2">
                                      <AgentMark agent={window.agent} compact />
                                      <div className="min-w-0">
                                        <p className="truncate text-[12px] font-semibold text-primary">{window.name || t("unnamed")}</p>
                                        <p className="truncate text-[10px] text-tertiary">{window.agent ? displayAgentName(window.agent) : window.command || "$SHELL"}</p>
                                      </div>
                                    </div>
                                    <div className="flex shrink-0 items-center gap-1">
                                      <button
                                        type="button"
	                                        onClick={() => moveSelectedTmuxWindow(windowIndex, -1)}
                                        disabled={windowIndex === 0}
                                        className="icon-touch sm:min-h-7 sm:min-w-7 rounded-md text-tertiary hover:bg-[var(--bg-hover)] hover:text-primary disabled:opacity-30"
                                        aria-label={t("moveUp")}
                                        title={t("moveUp")}
                                      >
                                        <ArrowUp className="h-3.5 w-3.5" />
                                      </button>
                                      <button
                                        type="button"
	                                        onClick={() => moveSelectedTmuxWindow(windowIndex, 1)}
	                                        disabled={windowIndex >= selectedTmuxWindowList.length - 1}
                                        className="icon-touch sm:min-h-7 sm:min-w-7 rounded-md text-tertiary hover:bg-[var(--bg-hover)] hover:text-primary disabled:opacity-30"
                                        aria-label={t("moveDown")}
                                        title={t("moveDown")}
                                      >
                                        <ArrowDown className="h-3.5 w-3.5" />
                                      </button>
                                      <button
                                        type="button"
	                                        onClick={() => deleteSelectedTmuxWindow(windowIndex)}
	                                        disabled={selectedTmuxWindowList.length <= 1}
                                        className="icon-touch sm:min-h-7 sm:min-w-7 rounded-md text-tertiary hover:bg-[var(--danger-bg)] hover:text-[var(--danger)] disabled:opacity-30"
                                        aria-label={t("removeTmuxWindow")}
                                        title={t("removeTmuxWindow")}
                                      >
                                        <Trash2 className="h-3.5 w-3.5" />
                                      </button>
                                    </div>
                                  </div>
                                  <div className="grid grid-cols-1 gap-2">
                                    <div>
                                      <FieldLabel required>{t("tmuxWindow")}</FieldLabel>
                                      <TextInput
                                        value={window.name}
	                                        onChange={(value) => updateSelectedTmuxWindow(windowIndex, { name: value })}
                                        placeholder="main"
                                        invalid={!window.name.trim()}
                                      />
                                    </div>
                                    <div>
                                      <FieldLabel>{t("agent")}</FieldLabel>
                                      <SelectInput
                                        value={window.agent ?? ""}
	                                        onChange={(value) => updateSelectedTmuxWindow(windowIndex, {
                                          agent: value || null,
                                          command: value ? null : window.command,
                                          session: value ? window.session ?? "auto" : null,
                                        })}
                                        options={agentOptions}
                                      />
                                    </div>
                                    {window.agent ? (
                                      <div>
                                        <FieldLabel>{t("agentSession")}</FieldLabel>
                                        <SessionInput
                                          value={window.session ?? window.session_id ?? "auto"}
	                                          onChange={(value) => updateSelectedTmuxWindow(windowIndex, { session: value || null, session_id: null })}
                                          agent={window.agent}
                                          scope={scope}
                                        />
                                      </div>
                                    ) : (
                                      <div>
                                        <FieldLabel>{t("shellCommand")}</FieldLabel>
                                        <TextInput
                                          value={window.command ?? ""}
	                                          onChange={(value) => updateSelectedTmuxWindow(windowIndex, { command: value || null })}
                                          placeholder="$SHELL"
                                        />
                                      </div>
                                    )}
                                  </div>
                                  <details className="group mt-2 rounded-md border border-subtle bg-[var(--bg-hover)]/25">
                                    <summary className="flex items-center gap-2 px-2.5 py-2 cursor-pointer text-[10px] font-semibold uppercase tracking-wide text-tertiary hover:text-secondary">
                                      <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" />
                                      {t("advanced")}
                                    </summary>
                                    <div className="px-2.5 pb-2.5 pt-0 space-y-2.5">
                                      <div>
                                        <FieldLabel>{t("workingDirectory")}</FieldLabel>
                                        <TextInput
                                          value={window.cwd ?? ""}
	                                          onChange={(value) => updateSelectedTmuxWindow(windowIndex, { cwd: value || null })}
                                          placeholder={t("relativeToSlotCwd")}
                                        />
                                      </div>
                                      <div>
                                        <FieldLabel>{t("label")}</FieldLabel>
                                        <TextInput
                                          value={window.label ?? ""}
	                                          onChange={(value) => updateSelectedTmuxWindow(windowIndex, { label: value || null })}
                                          placeholder={t("overrideLabel")}
                                        />
                                      </div>
                                      <div>
                                        <FieldLabel>{t("environmentVariables")}</FieldLabel>
                                        <KeyValueList
                                          items={window.env}
	                                          onChange={(env) => updateSelectedTmuxWindow(windowIndex, { env })}
                                        />
                                      </div>
                                    </div>
                                  </details>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      ) : selectedWindow ? (
                        <div className="space-y-2.5">
                          <div>
                            <FieldLabel required>{t("paneName")}</FieldLabel>
                            <TextInput
                              value={selectedWindow.name}
                              onChange={(value) => updateWindow(normalizedSelection.windowIndex ?? 0, { name: value })}
                              placeholder="builder"
                              invalid={!selectedWindow.name.trim()}
                            />
                          </div>
                          <div>
                            <FieldLabel>{t("agent")}</FieldLabel>
                            <SelectInput
                              value={selectedWindow.agent ?? ""}
                              onChange={(value) => updateWindow(normalizedSelection.windowIndex ?? 0, {
                                agent: value || null,
                                session: value ? selectedWindow.session ?? "auto" : null,
                              })}
                              options={agentOptions}
                            />
                          </div>
                          <div>
                            <FieldLabel>{t("agentSession")}</FieldLabel>
                            <SessionInput
                              value={selectedWindow.session ?? selectedWindow.session_id ?? "auto"}
                              onChange={(value) => updateWindow(normalizedSelection.windowIndex ?? 0, { session: value || null, session_id: null })}
                              agent={selectedWindow.agent}
                              scope={scope}
                            />
                          </div>
                          <details className="group rounded-md border border-default bg-[var(--bg-card)]">
                            <summary className="flex items-center gap-2 px-3 py-2 cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-tertiary hover:text-secondary">
                              <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" />
                              {t("advanced")}
                            </summary>
                            <div className="px-3 pb-3 pt-1 space-y-2.5">
                              <div>
                                <FieldLabel>{t("commandOverride")}</FieldLabel>
                                <TextInput
                                  value={selectedWindow.command ?? ""}
                                  onChange={(value) => updateWindow(normalizedSelection.windowIndex ?? 0, { command: value || null })}
                                  placeholder="npm run dev"
                                />
                              </div>
                              <div>
                                <FieldLabel>{t("workingDirectory")}</FieldLabel>
                                <TextInput
                                  value={selectedWindow.cwd ?? ""}
                                  onChange={(value) => updateWindow(normalizedSelection.windowIndex ?? 0, { cwd: value || null })}
                                  placeholder={t("relativeToSlotCwd")}
                                />
                              </div>
                              <div>
                                <FieldLabel>{t("label")}</FieldLabel>
                                <TextInput
                                  value={selectedWindow.label ?? ""}
                                  onChange={(value) => updateWindow(normalizedSelection.windowIndex ?? 0, { label: value || null })}
                                  placeholder={t("overrideLabel")}
                                />
                              </div>
                              <div>
                                <FieldLabel>{t("environmentVariables")}</FieldLabel>
                                <KeyValueList
                                  items={selectedWindow.env}
                                  onChange={(env) => updateWindow(normalizedSelection.windowIndex ?? 0, { env })}
                                />
                              </div>
                            </div>
                          </details>
                        </div>
                      ) : (
                        <div className="rounded-md border border-dashed border-default p-4 text-[12px] text-tertiary">
                          {t("noPanesYet")}
                        </div>
                      )}
                    </section>
                    )}

                    {selectedTmuxGroup ? (
                      <TmuxGroupPositionActions
                        canMoveUp={canMoveSelectedGroupUp}
                        canMoveDown={canMoveSelectedGroupDown}
                        onMoveUp={() => moveSelectedTmuxGroup(-1)}
                        onMoveDown={() => moveSelectedTmuxGroup(1)}
                        onDelete={deleteSelectedTmuxGroup}
                      />
                    ) : null}

                    {editingPane && !selectedTmuxGroup ? (
                      <PaneSchedulingActions
                        canMoveUp={canMoveSelectedPaneUp}
                        canMoveDown={canMoveSelectedPaneDown}
                        onSplitRight={() => splitSelectedPane("horizontal")}
                        onSplitDown={() => splitSelectedPane("vertical")}
                        onDuplicate={duplicatePane}
                        onMoveUp={() => movePane(-1)}
                        onMoveDown={() => movePane(1)}
                      />
                    ) : null}

                    {editingPane && selectedMovablePane && slots.length > 1 ? (
                      <MoveToTabActions
                        options={moveTargetOptions}
                        value={moveTarget}
                        onChange={setMoveTarget}
                        onMove={movePaneToTab}
                        canMove={canMovePaneToSelectedTab}
                      />
                    ) : null}

                    {editingPane && !selectedTmuxGroup ? (
                      <RemovePaneAction onDelete={deletePane} />
                    ) : null}
                  </div>
                </aside>
              )}
            </div>
          )}
    </section>
  );
}
