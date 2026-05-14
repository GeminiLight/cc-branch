import type { DragEvent, KeyboardEvent } from "react";
import { GripVertical, Plus, SquareTerminal, Terminal, Trash2 } from "lucide-react";
import { useI18n } from "../../i18n";
import AgentMark from "../ui/AgentMark";
import { workspacePaneCellStyle, workspacePaneGridStyle } from "../workspace-layout";
import type { SlotConfig } from "./types";
import type { PaneDragState, TabDragState } from "./workspace-drag";
import {
  canDragPane,
  isLegacyTmuxSlot,
  slotToCanvasPanes,
  slotToPanes,
  tmuxGroupWindows,
  type Selection,
} from "./workspace-model";
import {
  countText,
  paneCount,
  paneCountText,
  paneSummary,
  tabSummary,
  terminalPaneSummary,
} from "./workspace-display";

type WorkspaceCanvasProps = {
  slots: SlotConfig[];
  selection: Selection;
  tabDrag: TabDragState;
  paneDrag: PaneDragState;
  onAddTab: () => void;
  onDeleteTab: (slotIndex: number) => void;
  onAddPane: (slotIndex: number, afterIndex?: number) => void;
  onSelect: (selection: Selection) => void;
  onTabDragStart: (event: DragEvent<HTMLElement>, slotIndex: number) => void;
  onTabDragOver: (event: DragEvent<HTMLElement>) => void;
  onTabDrop: (event: DragEvent<HTMLElement>, slotIndex: number) => void;
  onTabDragEnd: () => void;
  onPaneDragStart: (event: DragEvent<HTMLElement>, slotIndex: number, paneIndex: number) => void;
  onPaneDragOver: (event: DragEvent<HTMLElement>, slotIndex: number) => void;
  onPaneDrop: (event: DragEvent<HTMLElement>, slotIndex: number, paneIndex: number) => void;
  onPaneAppendDrop: (event: DragEvent<HTMLElement>, slotIndex: number) => void;
  onPaneDragEnd: () => void;
};

export default function WorkspaceCanvas({
  slots,
  selection,
  tabDrag,
  paneDrag,
  onAddTab,
  onDeleteTab,
  onAddPane,
  onSelect,
  onTabDragStart,
  onTabDragOver,
  onTabDrop,
  onTabDragEnd,
  onPaneDragStart,
  onPaneDragOver,
  onPaneDrop,
  onPaneAppendDrop,
  onPaneDragEnd,
}: WorkspaceCanvasProps) {
  const { t } = useI18n();

  if (slots.length === 0) {
    return (
      <div className="text-center py-8 border border-dashed border-default rounded-lg bg-[var(--bg-card)]">
        <Terminal className="w-5 h-5 text-tertiary mx-auto mb-1.5" />
        <p className="text-[12px] text-secondary">{t("noTabsYet")}</p>
        <p className="text-[11px] text-tertiary mt-0.5">{t("addTabHint")}</p>
        <button
          type="button"
          onClick={onAddTab}
          className="mt-3 control-touch px-3 rounded-md text-[12px] font-medium surface-card border border-default hover:border-[var(--border-strong)] text-secondary hover:text-primary transition-colors inline-flex items-center gap-1.5"
        >
          <Plus className="w-3.5 h-3.5" />
          {t("addTab")}
        </button>
      </div>
    );
  }

  return (
    <div className="min-w-0 overflow-hidden rounded-lg border border-default bg-[var(--bg-elevated)]">
      <div className="workspace-matrix-surface relative p-3 min-h-[300px]">
        <div
          className="absolute inset-0 opacity-[0.10] pointer-events-none"
          style={{
            backgroundImage:
              "linear-gradient(var(--border-subtle) 1px, transparent 1px), linear-gradient(90deg, var(--border-subtle) 1px, transparent 1px)",
            backgroundSize: "28px 28px",
          }}
        />
        <div className="relative space-y-2.5">
          {slots.map((slot, slotIndex) => {
            const selectedTab = slotIndex === selection.slotIndex;
            const tabIsDragSource = tabDrag?.slotIndex === slotIndex;
            const tabDropCandidate = Boolean(tabDrag && !tabIsDragSource);
            const slotName = slot.name || t("unnamed");
            const panes = slotToPanes(slot);
            const canvasPanes = slotToCanvasPanes(slot);
            return (
              <section
                key={`${slot.name}-${slotIndex}`}
                draggable
                onDragStart={(event) => onTabDragStart(event, slotIndex)}
                onDragOver={onTabDragOver}
                onDrop={(event) => onTabDrop(event, slotIndex)}
                onDragEnd={onTabDragEnd}
                className={`group/tab rounded-lg border bg-[var(--bg-card)] transition-all overflow-hidden shadow-sm ${
                  selectedTab
                    ? "border-[var(--accent-border)] ring-1 ring-[var(--accent-border)] shadow-[inset_3px_0_0_var(--accent)]"
                    : "border-default hover:border-[var(--border-strong)]"
                } ${tabIsDragSource ? "opacity-55 scale-[0.998]" : ""} ${
                  tabDropCandidate ? "outline outline-1 outline-offset-2 outline-[var(--accent-border)]" : ""
                }`}
                data-drag-source={tabIsDragSource ? "true" : undefined}
                data-drop-candidate={tabDropCandidate ? "true" : undefined}
              >
                <div className="grid grid-cols-1 lg:grid-cols-[124px_minmax(0,1fr)]">
                  <button
                    type="button"
                    onClick={() => onSelect({ slotIndex, target: "tab", windowIndex: null })}
                    className={`workspace-tab-rail relative text-left p-2.5 border-b lg:border-b-0 lg:border-r border-subtle transition-colors ${
                      selectedTab && selection.target === "tab"
                        ? "bg-[var(--accent-bg)]/55"
                        : selectedTab
                        ? "bg-[var(--accent-bg)]/25"
                        : "hover:bg-[var(--bg-hover)]/55"
                    }`}
                    aria-label={t("editSlotNamed", { name: slotName })}
                  >
                    <span className="flex items-start justify-between gap-2">
                      <span className="min-w-0">
                        <span className="block text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("tab")}</span>
                        <span className="mt-0.5 block truncate text-[13px] font-semibold text-primary">{slotName}</span>
                      </span>
                      <span
                        className="mt-0.5 inline-flex h-6 w-5 shrink-0 items-center justify-center rounded text-muted"
                        title={t("dragTab")}
                        aria-hidden="true"
                      >
                        <GripVertical className="h-3.5 w-3.5" />
                      </span>
                    </span>
                    <span className="block mt-0.5 text-[10px] text-tertiary truncate">{tabSummary(t, slot)}</span>
                    {selectedTab && selection.target === "tab" && (
                      <span className="absolute inset-y-2 left-0 w-0.5 rounded-r-full bg-[var(--accent)]" aria-hidden="true" />
                    )}
                  </button>

                  <div className="min-w-0 p-2.5">
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className="text-[11px] font-medium text-tertiary truncate">
                          {isLegacyTmuxSlot(slot)
                            ? countText(t, "tmuxGroupCount_one", "tmuxGroupCount", 1)
                            : paneCountText(t, paneCount(slot))}
                        </span>
                        {isLegacyTmuxSlot(slot) && (
                          <span className="text-[11px] text-tertiary truncate">
                            · {countText(t, "tmuxWindowCount_one", "tmuxWindowCount", panes.length)}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0 opacity-70 transition-opacity group-hover/tab:opacity-100 focus-within:opacity-100">
                        <button
                          type="button"
                          onClick={() => onAddPane(slotIndex, slotToPanes(slot).length - 1)}
                          className="icon-touch sm:min-h-8 sm:min-w-8 rounded-md text-tertiary hover:text-primary hover:surface-hover flex items-center justify-center"
                          aria-label={t("addPane")}
                          title={t("addPane")}
                        >
                          <Plus className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => onDeleteTab(slotIndex)}
                          className="icon-touch sm:min-h-8 sm:min-w-8 rounded-md text-tertiary hover:text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors flex items-center justify-center"
                          aria-label={t("removeSlotNamed", { name: slotName })}
                          title={t("removeSlotNamed", { name: slotName })}
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div
                        className="grid gap-2 min-h-[74px]"
                        style={workspacePaneGridStyle(slot, canvasPanes.length)}
                        onDragOver={(event) => onPaneDragOver(event, slotIndex)}
                        onDrop={(event) => onPaneAppendDrop(event, slotIndex)}
                      >
                        {canvasPanes.map((pane, paneIndex) => {
                          const selectedPane =
                            selectedTab &&
                            selection.target === "pane" &&
                            (slot.runtime === "tmux"
                              ? selection.windowIndex === null
                              : slot.runtime === "terminal" && slot.windows.length === 0
                              ? selection.windowIndex === null
                              : selection.windowIndex === paneIndex);
                          const paneName = pane.name || t("unnamed");
                          const cwdLabel = pane.cwd || slot.cwd || "";
                          const paneAgent = pane.agent ?? null;
                          const paneIsDraggable = canDragPane(slot);
                          const paneIsDragSource =
                            paneDrag?.slotIndex === slotIndex && paneDrag.paneIndex === paneIndex;
                          const paneDropCandidate = Boolean(paneDrag && !paneIsDragSource);
                          return (
                            <div
                              role="button"
                              tabIndex={0}
                              key={`${pane.name}-${paneIndex}`}
                              onClick={() => onSelect({ slotIndex, target: "pane", windowIndex: pane.windowIndex })}
                              draggable={paneIsDraggable}
                              onDragStart={(event) => onPaneDragStart(event, slotIndex, paneIndex)}
                              onDragOver={(event) => onPaneDragOver(event, slotIndex)}
                              onDrop={(event) => onPaneDrop(event, slotIndex, paneIndex)}
                              onDragEnd={onPaneDragEnd}
                              onKeyDown={(event: KeyboardEvent<HTMLElement>) => {
                                if (event.key === "Enter" || event.key === " ") {
                                  event.preventDefault();
                                  onSelect({ slotIndex, target: "pane", windowIndex: pane.windowIndex });
                                }
                              }}
                              className={`workspace-pane-card group/pane relative min-h-[68px] overflow-hidden rounded-md border p-2.5 text-left transition-all ${
                                selectedPane
                                  ? "border-[var(--accent-border)] bg-[var(--accent-bg)] ring-1 ring-[var(--accent-border)] shadow-[0_0_0_3px_var(--accent-bg),0_10px_24px_rgba(15,23,42,0.08)]"
                                  : pane.kind === "tmux-group"
                                  ? "border-[var(--accent-border)] bg-[var(--accent-bg)]/35 hover:border-[var(--accent)]"
                                  : "border-default bg-[var(--bg-card)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)]/45"
                              } ${paneIsDragSource ? "opacity-55 scale-[0.99]" : ""} ${
                                paneDropCandidate ? "outline outline-1 outline-offset-1 outline-[var(--accent-border)]" : ""
                              }`}
                              style={workspacePaneCellStyle(slot, canvasPanes.length, paneIndex)}
                              aria-label={t("editWindowNamed", { name: paneName })}
                              aria-current={selectedPane ? "true" : undefined}
                              data-drag-source={paneIsDragSource ? "true" : undefined}
                              data-drop-candidate={paneDropCandidate ? "true" : undefined}
                            >
                              {selectedPane && (
                                <span
                                  className="pointer-events-none absolute inset-y-2 left-2 w-0.5 rounded-full bg-[var(--accent)]"
                                  aria-hidden="true"
                                />
                              )}
                              <span className="relative flex items-start justify-between gap-2 pl-1.5">
                                <span className="flex min-w-0 items-start gap-2">
                                  <AgentMark agent={paneAgent} />
                                  <span className="min-w-0">
                                    <span className="block text-[10px] font-semibold uppercase tracking-wide text-tertiary">
                                      {pane.kind === "tmux-group" ? t("tmuxWindowStack") : t("pane")}
                                    </span>
                                    <span className="block mt-0.5 text-[13px] font-semibold text-primary truncate">{paneName}</span>
                                  </span>
                                </span>
                                <span className="flex shrink-0 items-center gap-1.5">
                                  {!paneIsDraggable ? (
                                    <SquareTerminal className="w-4 h-4 text-[var(--accent)] shrink-0" aria-hidden="true" />
                                  ) : (
                                    <span
                                      className="inline-flex h-6 w-5 shrink-0 items-center justify-center rounded text-muted cursor-grab active:cursor-grabbing"
                                      title={t("dragPane")}
                                    >
                                      <GripVertical className="h-3.5 w-3.5" aria-hidden="true" />
                                    </span>
                                  )}
                                </span>
                              </span>
                              <span className="relative mt-2 block pl-1.5 text-[12px] text-secondary truncate">
                                {pane.kind === "tmux-group"
                                  ? countText(
                                      t,
                                      "tmuxWindowGroupSummary_one",
                                      "tmuxWindowGroupSummary",
                                      isLegacyTmuxSlot(slot)
                                        ? panes.length
                                        : tmuxGroupWindows(slot.windows[pane.windowIndex ?? paneIndex]).length
                                    )
                                  : slot.runtime === "terminal" && slot.windows.length === 0
                                  ? terminalPaneSummary(t, slot)
                                  : paneSummary(t, panes[pane.windowIndex ?? paneIndex])}
                              </span>
                              {pane.kind === "tmux-group" && (
                                <span className="relative mt-2 flex flex-wrap gap-1 pl-1.5">
                                  {(isLegacyTmuxSlot(slot)
                                    ? panes
                                    : tmuxGroupWindows(slot.windows[pane.windowIndex ?? paneIndex])
                                  ).map((window, windowIndex) => (
                                    <span
                                      key={`${window.name}-${windowIndex}-chip`}
                                      className="inline-flex min-w-0 items-center gap-1 rounded-md border border-default bg-[var(--bg-card)] px-1.5 py-0.5 text-[10px] text-secondary"
                                    >
                                      <AgentMark agent={window.agent} compact />
                                      <span className="truncate max-w-[120px]">{window.name || t("unnamed")}</span>
                                    </span>
                                  ))}
                                </span>
                              )}
                              {cwdLabel && cwdLabel !== "." && (
                                <span className="relative mt-0.5 block pl-1.5 text-[10px] text-tertiary font-mono truncate">
                                  {cwdLabel}
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              </section>
            );
          })}
          <button
            type="button"
            onClick={onAddTab}
            className="w-full min-h-11 rounded-md border border-dashed border-[var(--accent-border)] bg-[var(--accent-bg)]/45 p-2 text-center text-[12px] font-semibold text-[var(--accent)] hover:bg-[var(--accent-bg)] transition-colors"
          >
            <Plus className="w-3.5 h-3.5 inline-block mr-1.5 align-[-2px]" />
            {t("addTab")}
          </button>
        </div>
      </div>
    </div>
  );
}
