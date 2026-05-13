/**
 * ConfigEditor — Workspace canvas for Tab / Pane layout editing.
 *
 * The persisted schema is still slots/windows. The UI presents those as
 * tabs/panes so users edit the workspace model, not the storage model.
 */

import { useEffect, useMemo, useState } from "react";
import { useI18n } from "../../i18n";
import type { RuntimeAvailability, WorkspaceScope } from "../../types";
import type { SlotConfig, WindowConfig } from "./types";
import {
  MoveToTabActions,
  PaneSchedulingActions,
  RemovePaneAction,
  TmuxGroupPositionActions,
} from "./InspectorActions";
import TmuxGroupEditor from "./TmuxGroupEditor";
import WorkspaceCanvas from "./WorkspaceCanvas";
import {
  AgentPaneEditor,
  TabEditor,
  TerminalPaneEditor,
} from "./WorkspaceDetailEditors";
import {
  InlineError,
} from "./FormPrimitives";
import {
  addTabMutation,
  deleteTabMutation,
  editableWindowsForSlot,
  emptyWindow,
  isLegacyTmuxSlot,
  movePaneBetweenSlots,
  movePaneWithinTabMutation,
  moveTab as moveTabModel,
  slotWithWindows,
  tmuxGroupWindowFromSlot,
  tmuxGroupWindows,
  type Selection,
  type TabLayout,
} from "./workspace-model";
import { paneCount } from "./workspace-display";
import { useWorkspaceDrag } from "./workspace-drag";
import { deriveWorkspaceSelection } from "./workspace-selection";

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

  const {
    normalizedSelection,
    selectedSlot,
    selectedWindow,
    selectedTerminalWindow,
    selectedTmuxGroup,
    editingPane,
  } = useMemo(() => deriveWorkspaceSelection(slots, selection), [selection, slots]);

  useEffect(() => {
    if (
      normalizedSelection.slotIndex !== selection.slotIndex ||
      normalizedSelection.target !== selection.target ||
      normalizedSelection.windowIndex !== selection.windowIndex
    ) {
      setSelection(normalizedSelection);
    }
  }, [normalizedSelection, selection]);

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
    const mutation = addTabMutation(slots, defaultRuntime, agents);
    replaceSlots(mutation.slots, mutation.selection);
  }

  function deleteTab(index: number) {
    const mutation = deleteTabMutation(slots, index);
    if (!mutation) return;
    replaceSlots(mutation.slots, mutation.selection);
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
    const mutation = movePaneWithinTabMutation(slots, slotIndex, windowIndex, dir);
    if (!mutation) return;
    replaceSlots(mutation.slots, mutation.selection);
  }

  function movePaneByDrag(fromSlotIndex: number, fromPaneIndex: number, toSlotIndex: number, toPaneIndex: number) {
    const mutation = movePaneBetweenSlots(slots, fromSlotIndex, fromPaneIndex, toSlotIndex, toPaneIndex);
    if (!mutation) return;
    replaceSlots(mutation.slots, mutation.selection);
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
    ? selectedSlot && isLegacyTmuxSlot(selectedSlot)
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

  const workspaceDrag = useWorkspaceDrag({
    slots,
    onMoveTab: moveTabByDrag,
    onMovePane: movePaneByDrag,
  });

  const canvasProps = {
    slots,
    selection: normalizedSelection,
    tabDrag: workspaceDrag.tabDrag,
    paneDrag: workspaceDrag.paneDrag,
    onAddTab: addTab,
    onDeleteTab: deleteTab,
    onAddPane: addPaneToSlot,
    onSelect: setSelection,
    onTabDragStart: workspaceDrag.handleTabDragStart,
    onTabDragOver: workspaceDrag.handleTabDragOver,
    onTabDrop: workspaceDrag.handleTabDrop,
    onTabDragEnd: workspaceDrag.clearTabDrag,
    onPaneDragStart: workspaceDrag.handlePaneDragStart,
    onPaneDragOver: workspaceDrag.handlePaneDragOver,
    onPaneDrop: workspaceDrag.handlePaneDrop,
    onPaneAppendDrop: workspaceDrag.handlePaneAppendDrop,
    onPaneDragEnd: workspaceDrag.clearPaneDrag,
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
                      <TabEditor
                        slot={selectedSlot}
                        layoutOptions={layoutOptions}
                        onChange={(patch) => updateSlot(normalizedSelection.slotIndex, patch)}
                      />
                    )}

                    {editingPane && (
                    <section className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("pane")}</p>
                        <span className="text-[10px] text-tertiary">{runtimeLabel(t, selectedSlot.runtime)}</span>
                      </div>
                      {selectedSlot.runtime === "terminal" && !selectedTmuxGroup ? (
                        <TerminalPaneEditor
                          slot={selectedSlot}
                          window={selectedTerminalWindow}
                          agentOptions={agentOptions}
                          scope={scope}
                          onSlotChange={(patch) => updateSlot(normalizedSelection.slotIndex, patch)}
                          onWindowChange={(patch) => updateWindow(normalizedSelection.windowIndex ?? 0, patch)}
                        />
                      ) : selectedTmuxGroup ? (
                        <TmuxGroupEditor
                          groupName={isLegacyTmuxSlot(selectedSlot) ? selectedSlot.name : selectedWindow?.name ?? ""}
                          windows={selectedTmuxWindowList}
                          agentOptions={agentOptions}
                          scope={scope}
                          onGroupNameChange={updateSelectedTmuxGroupName}
                          onAddWindow={addSelectedTmuxWindow}
                          onMoveWindow={moveSelectedTmuxWindow}
                          onDeleteWindow={deleteSelectedTmuxWindow}
                          onUpdateWindow={updateSelectedTmuxWindow}
                        />
                      ) : selectedWindow ? (
                        <AgentPaneEditor
                          window={selectedWindow}
                          agentOptions={agentOptions}
                          scope={scope}
                          onChange={(patch) => updateWindow(normalizedSelection.windowIndex ?? 0, patch)}
                        />
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
