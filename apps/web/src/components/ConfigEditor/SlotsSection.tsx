/**
 * ConfigEditor — Workspace canvas for Tab / Pane layout editing.
 *
 * The persisted schema is still slots/windows. The UI presents those as
 * tabs/panes so users edit the workspace model, not the storage model.
 */

import { useEffect, useMemo, useRef, useState, type CSSProperties, type DragEvent } from "react";
import {
  ArrowDown,
  ArrowUp,
  ChevronDown,
  ChevronsUpDown,
  Clock3,
  Copy,
  GripVertical,
  MoveRight,
  Plus,
  SquareTerminal,
  Terminal,
  Trash2,
} from "lucide-react";
import { useI18n } from "../../i18n";
import type { AgentSessionInfo, RuntimeAvailability, WorkspaceScope } from "../../types";
import { useAgentSessions } from "../../hooks";
import claudeIconUrl from "../../assets/agent-icons/claude.svg";
import cursorIconUrl from "../../assets/agent-icons/cursor.svg";
import geminiIconUrl from "../../assets/agent-icons/gemini.svg";
import kimiIconUrl from "../../assets/agent-icons/kimi.svg";
import openaiIconUrl from "../../assets/agent-icons/openai.svg";
import Dropdown from "../ui/Dropdown";
import type { SlotConfig, WindowConfig } from "./types";
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
  configuredPaneCount,
  editableWindowsForSlot,
  emptyWindow,
  isLegacyTmuxSlot,
  isTmuxGroupWindow,
  movePaneBetweenSlots,
  moveTab as moveTabModel,
  normalizedLayout,
  slotToCanvasPanes,
  slotToPanes,
  slotWithWindows,
  tmuxGroupWindowFromSlot,
  tmuxGroupWindows,
  type Selection,
  type TabLayout,
} from "./workspace-model";

type PaneDragState = { slotIndex: number; paneIndex: number } | null;
type TabDragState = { slotIndex: number } | null;

function displayAgentName(agent: string | null | undefined): string {
  return agent ? agent.charAt(0).toUpperCase() + agent.slice(1) : "";
}

function runtimeLabel(t: (key: string, vars?: Record<string, string | number>) => string, runtime: SlotConfig["runtime"]): string {
  return runtime === "terminal" ? t("runtimeTerminal") : t("runtimeTmux");
}

function countText(
  t: (key: string, vars?: Record<string, string | number>) => string,
  singularKey: string,
  pluralKey: string,
  count: number,
): string {
  return t(count === 1 ? singularKey : pluralKey, { count });
}

function normalizeAgentKey(agent: string | null | undefined): string {
  const value = (agent || "").toLowerCase();
  const compact = value.replace(/[\s_-]+/g, "");
  if (value.includes("codex")) return "codex";
  if (compact.includes("claude") || compact.includes("cloudcode") || compact.includes("anthropic")) return "claude";
  if (compact.includes("gemini") || compact.includes("antigravity")) return "gemini";
  if (compact.includes("cursor")) return "cursor";
  if (compact.includes("kimi")) return "kimi";
  return value;
}

function agentIdentity(agent: string | null | undefined) {
  const key = normalizeAgentKey(agent);
  if (key === "codex") return { label: "Codex", initials: "Cx", iconUrl: openaiIconUrl, tone: "bg-white text-zinc-950 border-zinc-200 dark:bg-zinc-100 dark:text-zinc-950 dark:border-zinc-300" };
  if (key === "claude") return { label: "Claude", initials: "Cl", iconUrl: claudeIconUrl, tone: "bg-[#f4eee7] text-[#8a4b25] border-[#dfcabc] dark:bg-[#2a1d17] dark:text-[#f2c6a4] dark:border-[#5f3b2a]" };
  if (key === "gemini") return { label: "Gemini", initials: "G", iconUrl: geminiIconUrl, tone: "bg-[#eef4ff] text-[#2459c7] border-[#c8d9ff] dark:bg-[#101a2e] dark:text-[#9bbcff] dark:border-[#293d66]" };
  if (key === "cursor") return { label: "Cursor", initials: "Cu", iconUrl: cursorIconUrl, tone: "bg-zinc-950 text-white border-zinc-800 dark:bg-zinc-100 dark:text-zinc-950 dark:border-zinc-300" };
  if (key === "kimi") return { label: "Kimi", initials: "Ki", iconUrl: kimiIconUrl, tone: "bg-[#f2efff] text-[#5d48b1] border-[#d7cff7] dark:bg-[#191329] dark:text-[#c8bbff] dark:border-[#3e3268]" };
  if (agent) {
    const label = displayAgentName(agent);
    return {
      label,
      initials: label.slice(0, 2) || "A",
      tone: "bg-[var(--bg-elevated)] text-secondary border-default",
    };
  }
  return { label: "Shell", initials: "$", tone: "bg-[var(--accent-bg)] text-[var(--accent)] border-[var(--accent-border)]" };
}

function AgentMark({ agent, compact = false }: { agent: string | null | undefined; compact?: boolean }) {
  const identity = agentIdentity(agent);
  const sizeClass = compact ? "h-5 w-5" : "h-6 w-6";
  return (
    <span
      className={`${sizeClass} inline-flex shrink-0 items-center justify-center overflow-hidden rounded-md border font-bold tracking-[-0.02em] ${compact ? "text-[9px]" : "text-[10px]"} ${identity.tone}`}
      title={identity.label}
      aria-label={identity.label}
    >
      {"iconUrl" in identity && identity.iconUrl ? (
        <img src={identity.iconUrl} alt="" className={`${compact ? "h-3.5 w-3.5" : "h-4 w-4"} object-contain`} draggable={false} />
      ) : (
        identity.initials
      )}
    </span>
  );
}

function sessionDescription(session: AgentSessionInfo): string {
  const shortId = session.id.length > 12 ? `${session.id.slice(0, 8)}...${session.id.slice(-4)}` : session.id;
  if (!session.updated_at) return shortId;
  const date = new Date(session.updated_at);
  if (Number.isNaN(date.getTime())) return shortId;
  return `${shortId} · ${date.toLocaleDateString()}`;
}

function paneCount(slot: SlotConfig): number {
  return configuredPaneCount(slot);
}

function paneCountText(t: (key: string, vars?: Record<string, string | number>) => string, count: number): string {
  return t(count === 1 ? "windowCountShortOne" : "windowCountShort", { count });
}

function tabSummary(t: (key: string, vars?: Record<string, string | number>) => string, slot: SlotConfig): string {
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

function paneSummary(t: (key: string, vars?: Record<string, string | number>) => string, win: WindowConfig): string {
  if (win.agent) return t("paneSummaryAgent", { agent: displayAgentName(win.agent) });
  if (win.command) return t("paneSummaryCommand", { command: win.command });
  return t("paneSummaryInherited");
}

function terminalPaneSummary(t: (key: string, vars?: Record<string, string | number>) => string, slot: SlotConfig): string {
  if (slot.agent) return t("paneSummaryAgent", { agent: displayAgentName(slot.agent) });
  return t("paneSummaryCommand", { command: slot.command || "$SHELL" });
}

function LayoutGlyph({ layout }: { layout: TabLayout }) {
  const base = "rounded-[2px] border border-current bg-current/15";
  if (layout === "vertical") {
    return (
      <span className="grid h-4 w-5 grid-rows-2 gap-0.5" aria-hidden="true">
        <span className={base} />
        <span className={base} />
      </span>
    );
  }
  if (layout === "main-left") {
    return (
      <span className="grid h-4 w-5 grid-cols-[1.25fr_0.75fr] grid-rows-2 gap-0.5" aria-hidden="true">
        <span className={`${base} row-span-2`} />
        <span className={base} />
        <span className={base} />
      </span>
    );
  }
  if (layout === "main-top") {
    return (
      <span className="grid h-4 w-5 grid-cols-2 grid-rows-[1.2fr_0.8fr] gap-0.5" aria-hidden="true">
        <span className={`${base} col-span-2`} />
        <span className={base} />
        <span className={base} />
      </span>
    );
  }
  if (layout === "grid") {
    return (
      <span className="grid h-4 w-5 grid-cols-2 grid-rows-2 gap-0.5" aria-hidden="true">
        <span className={base} />
        <span className={base} />
        <span className={base} />
        <span className={base} />
      </span>
    );
  }
  if (layout === "auto") {
    return (
      <span className="grid h-4 w-5 grid-cols-[1fr_0.7fr] grid-rows-2 gap-0.5" aria-hidden="true">
        <span className={`${base} row-span-2`} />
        <span className={base} />
        <span className={base} />
      </span>
    );
  }
  return (
    <span className="grid h-4 w-5 grid-cols-2 gap-0.5" aria-hidden="true">
      <span className={base} />
      <span className={base} />
    </span>
  );
}

function paneGridStyle(slot: SlotConfig, panes: WindowConfig[]): CSSProperties {
  const count = Math.max(panes.length, 1);
  const layout = normalizedLayout(slot, count);
  if (count === 1) return { gridTemplateColumns: "minmax(0, 1fr)" };
  if (layout === "vertical") {
    return { gridTemplateRows: `repeat(${count}, minmax(72px, 1fr))` };
  }
  if (layout === "main-left") {
    return {
      gridTemplateColumns: "minmax(150px, 1.18fr) minmax(116px, 0.82fr)",
      gridTemplateRows: `repeat(${Math.max(count - 1, 1)}, minmax(70px, 1fr))`,
    };
  }
  if (layout === "main-top") {
    return {
      gridTemplateColumns: `repeat(${Math.max(count - 1, 1)}, minmax(112px, 1fr))`,
      gridTemplateRows: "minmax(82px, 1.04fr) minmax(68px, 0.96fr)",
    };
  }
  if (layout === "grid") {
    const columns = count <= 4 ? 2 : 3;
    return { gridTemplateColumns: `repeat(${columns}, minmax(112px, 1fr))` };
  }
  return { gridTemplateColumns: `repeat(${count}, minmax(112px, 1fr))` };
}

function paneCellStyle(slot: SlotConfig, panes: WindowConfig[], index: number): CSSProperties {
  const count = Math.max(panes.length, 1);
  const layout = normalizedLayout(slot, count);
  if (index !== 0 || count <= 1) return {};
  if (layout === "main-left") return { gridRow: `1 / span ${Math.max(count - 1, 1)}` };
  if (layout === "main-top") return { gridColumn: `1 / span ${Math.max(count - 1, 1)}` };
  return {};
}


function sessionIntent(value: string): "auto" | "fresh" | "resume" {
  if (!value || value === "auto") return "auto";
  if (value === "fresh") return "fresh";
  return "resume";
}

function SessionInput({
  value,
  onChange,
  agent,
  scope,
}: {
  value: string;
  onChange: (value: string) => void;
  agent?: string | null;
  scope?: WorkspaceScope;
}) {
  const { t } = useI18n();
  const agentKey = normalizeAgentKey(agent);
  const [forcedIntent, setForcedIntent] = useState<"resume" | null>(null);
  const inferredIntent = sessionIntent(value);
  const intent = forcedIntent ?? inferredIntent;
  const { data, isFetching: loading } = useAgentSessions(scope, Boolean(agentKey) && intent === "resume", agentKey);
  const sessions = data?.sessions || [];
  const matchingSessions = agentKey
    ? sessions.filter((session) => normalizeAgentKey(session.agent) === agentKey)
    : [];
  const displayAgent = displayAgentName(agent);
  const items = matchingSessions.length > 0
    ? matchingSessions.map((session) => ({
        value: session.id,
        label: session.label || session.id,
        description: sessionDescription(session),
        icon: <Clock3 className="w-3.5 h-3.5" />,
      }))
    : [{
        value: "__empty",
        label: loading ? t("loadingSessions") : t("noSessionsFound"),
        description: agent ? t("manualSessionAllowed") : t("selectAgentFirst"),
        disabled: true,
      }];
  const sessionTextValue = intent === "resume" && (value === "auto" || value === "fresh") ? "" : value;

  useEffect(() => {
    if (inferredIntent !== "resume") setForcedIntent(null);
  }, [inferredIntent]);

  function switchIntent(next: "auto" | "fresh" | "resume") {
    if (next === "auto") {
      setForcedIntent(null);
      onChange("auto");
    } else if (next === "fresh") {
      setForcedIntent(null);
      onChange("fresh");
    } else {
      setForcedIntent("resume");
      if (matchingSessions[0]?.id) onChange(matchingSessions[0].id);
    }
  }

  return (
    <div className="rounded-lg border border-default bg-[var(--bg-card)] p-1.5">
      <div className="grid grid-cols-3 gap-1">
        {(["auto", "fresh", "resume"] as const).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => switchIntent(option)}
            className={`min-h-8 rounded-md px-2 text-[11px] font-semibold transition-colors ${
              intent === option
                ? "bg-[var(--accent-bg)] text-[var(--accent)]"
                : "text-tertiary hover:bg-[var(--bg-hover)] hover:text-primary"
            }`}
            aria-pressed={intent === option}
          >
            {option === "auto" ? t("sessionAuto") : option === "fresh" ? t("sessionFresh") : t("sessionResume")}
          </button>
        ))}
      </div>

      {intent === "resume" ? (
        <div className="mt-1.5 flex items-center rounded-md border border-default bg-[var(--bg-card)] transition-all hover:border-[var(--border-strong)] focus-within:ring-2 focus-within:ring-[var(--accent-border)] focus-within:border-[var(--accent)]">
          <input
            type="text"
            value={sessionTextValue}
            onChange={(event) => onChange(event.target.value)}
            placeholder={
              displayAgent
                ? t("sessionIdPlaceholderWithAgent", { agent: displayAgent })
                : t("sessionIdPlaceholder")
            }
            className="min-w-0 flex-1 h-8 px-2.5 rounded-l-md text-[12px] bg-transparent placeholder:text-muted focus:outline-none"
          />
          <Dropdown
            align="right"
            value={matchingSessions.some((session) => session.id === value) ? value : ""}
            onChange={(nextValue) => {
              if (nextValue !== "__empty") onChange(nextValue);
            }}
            items={items}
            ariaLabel={t("sessionPicker")}
            className="shrink-0"
            triggerClassName="h-full block"
            trigger={
              <span className="h-8 min-w-8 px-2 border-l border-default text-tertiary hover:text-primary hover:bg-[var(--bg-hover)] rounded-r-md transition-colors flex items-center justify-center">
                <ChevronsUpDown className="w-3.5 h-3.5" />
              </span>
            }
          />
        </div>
      ) : (
        <p className="px-1.5 pt-1.5 text-[10px] leading-snug text-tertiary">
          {intent === "auto" ? t("sessionAutoHint") : t("sessionFreshHint")}
        </p>
      )}
    </div>
  );
}

function LayoutPicker({
  value,
  options,
  onChange,
  compact = false,
}: {
  value: TabLayout;
  options: Array<{ value: string; label: string }>;
  onChange: (value: TabLayout) => void;
  compact?: boolean;
}) {
  return (
    <div
      className={`flex flex-wrap items-center gap-1 rounded-md border border-default bg-[var(--bg-hover)] p-1 ${
        compact ? "max-w-[230px]" : ""
      }`}
    >
      {options.map((option) => {
        const selected = option.value === value;
        const optionValue = option.value as TabLayout;
        return (
          <button
            type="button"
            key={option.value}
            onClick={() => onChange(optionValue)}
            className={`control-touch rounded text-[11px] font-semibold transition-colors ${
              compact ? "min-h-7 min-w-8 px-1.5" : "min-h-8 px-2"
            } ${
              selected
                ? "bg-[var(--bg-card)] text-[var(--accent)] shadow-sm"
                : "text-tertiary hover:text-primary hover:bg-[var(--bg-card)]/70"
            }`}
            aria-pressed={selected}
            aria-label={option.label}
            title={option.label}
          >
            {compact ? (
              <>
                <LayoutGlyph layout={optionValue} />
                <span className="sr-only">{option.label}</span>
              </>
            ) : (
              <span className="inline-flex items-center gap-1.5">
                <LayoutGlyph layout={optionValue} />
                {option.label}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
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
      configuredPaneCount(target),
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
            <div className="text-center py-8 border border-dashed border-default rounded-lg bg-[var(--bg-card)]">
              <Terminal className="w-5 h-5 text-tertiary mx-auto mb-1.5" />
              <p className="text-[12px] text-secondary">{t("noTabsYet")}</p>
              <p className="text-[11px] text-tertiary mt-0.5">
                {t("addTabHint")}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_360px] gap-3 items-start">
              <div className="min-w-0 overflow-hidden rounded-lg border border-default bg-[var(--bg-elevated)]">
                <div className="px-3 py-2.5 border-b border-subtle flex items-center justify-between gap-3 bg-[var(--bg-card)]">
                  <div className="min-w-0">
                    <p className="text-[13px] font-semibold text-primary">{t("matrixCanvas")}</p>
                    <p className="text-[11px] text-tertiary truncate">
                      {t("configSlotSummary", {
                        slots: slots.length,
                        windows: slots.reduce((count, slot) => count + paneCount(slot), 0),
                      })}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={addTab}
                    className="control-touch px-3 rounded-md text-[12px] font-medium surface-card border border-default hover:border-[var(--border-strong)] text-secondary hover:text-primary transition-colors flex items-center gap-1.5 shrink-0"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    {t("addTab")}
                  </button>
                </div>
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
                      const selectedTab = slotIndex === normalizedSelection.slotIndex;
                      const slotName = slot.name || t("unnamed");
                      const panes = slotToPanes(slot);
                      const canvasPanes = slotToCanvasPanes(slot);
                      return (
                        <section
                          key={`${slot.name}-${slotIndex}`}
                          draggable
                          onDragStart={(event) => handleTabDragStart(event, slotIndex)}
                          onDragOver={handleTabDragOver}
                          onDrop={(event) => handleTabDrop(event, slotIndex)}
                          onDragEnd={() => setTabDrag(null)}
                          className={`group/tab rounded-lg border bg-[var(--bg-card)] transition-all overflow-hidden shadow-sm ${
                            selectedTab
                              ? "border-[var(--accent-border)] shadow-[inset_3px_0_0_var(--accent)]"
                              : "border-default hover:border-[var(--border-strong)]"
                          } ${
                            tabDrag?.slotIndex === slotIndex ? "opacity-55" : ""
                          }`}
                        >
                          <div className="grid grid-cols-1 lg:grid-cols-[124px_minmax(0,1fr)]">
                            <button
                              type="button"
                              onClick={() => setSelection({ slotIndex, target: "tab", windowIndex: null })}
                              className={`workspace-tab-rail relative text-left p-2.5 border-b lg:border-b-0 lg:border-r border-subtle transition-colors ${
                                selectedTab && normalizedSelection.target === "tab"
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
                              {selectedTab && normalizedSelection.target === "tab" && (
                                <span
                                  className="absolute inset-y-2 left-0 w-0.5 rounded-r-full bg-[var(--accent)]"
                                  aria-hidden="true"
                                />
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
                                    onClick={() => addPaneToSlot(slotIndex, slotToPanes(slot).length - 1)}
                                    className="icon-touch sm:min-h-8 sm:min-w-8 rounded-md text-tertiary hover:text-primary hover:surface-hover flex items-center justify-center"
                                    aria-label={t("addPane")}
                                    title={t("addPane")}
                                  >
                                    <Plus className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => deleteTab(slotIndex)}
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
                                  style={paneGridStyle(slot, canvasPanes as unknown as WindowConfig[])}
                                  onDragOver={(event) => handlePaneDragOver(event, slotIndex)}
                                  onDrop={(event) => handlePaneAppendDrop(event, slotIndex)}
                                >
                                  {canvasPanes.map((pane, paneIndex) => {
                                    const selectedPane =
                                      selectedTab &&
                                      normalizedSelection.target === "pane" &&
                                      (slot.runtime === "tmux"
                                        ? normalizedSelection.windowIndex === null
                                        : slot.runtime === "terminal" && slot.windows.length === 0
                                        ? normalizedSelection.windowIndex === null
                                        : normalizedSelection.windowIndex === paneIndex);
                                    const paneName = pane.name || t("unnamed");
                                    const cwdLabel = pane.cwd || slot.cwd || "";
                                    const paneAgent = pane.agent ?? null;
                                    const paneIsDraggable = canDragPane(slot);
                                    return (
                                      <div
                                        role="button"
                                        tabIndex={0}
                                        key={`${pane.name}-${paneIndex}`}
                                        onClick={() => setSelection({
                                          slotIndex,
                                          target: "pane",
                                          windowIndex: pane.windowIndex,
                                        })}
                                        draggable={paneIsDraggable}
                                        onDragStart={(event) => handlePaneDragStart(event, slotIndex, paneIndex)}
                                        onDragOver={(event) => handlePaneDragOver(event, slotIndex)}
                                        onDrop={(event) => handlePaneDrop(event, slotIndex, paneIndex)}
                                        onDragEnd={() => {
                                          paneDragRef.current = null;
                                          setPaneDrag(null);
                                        }}
                                        onKeyDown={(event) => {
                                          if (event.key === "Enter" || event.key === " ") {
                                            event.preventDefault();
                                            setSelection({
                                              slotIndex,
                                              target: "pane",
                                              windowIndex: pane.windowIndex,
                                            });
                                          }
                                        }}
                                        className={`workspace-pane-card group/pane relative min-h-[68px] overflow-hidden rounded-md border p-2.5 text-left transition-all ${
                                          selectedPane
                                            ? "border-[var(--accent-border)] bg-[var(--accent-bg)] shadow-[0_0_0_3px_var(--accent-bg),0_10px_24px_rgba(15,23,42,0.08)]"
                                            : pane.kind === "tmux-group"
                                            ? "border-[var(--accent-border)] bg-[var(--accent-bg)]/35 hover:border-[var(--accent)]"
                                            : "border-default bg-[var(--bg-card)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)]/45"
                                        } ${
                                          paneDrag?.slotIndex === slotIndex && paneDrag.paneIndex === paneIndex
                                            ? "opacity-55"
                                            : ""
                                        }`}
                                        style={paneCellStyle(slot, canvasPanes as unknown as WindowConfig[], paneIndex)}
                                        aria-label={t("editWindowNamed", { name: paneName })}
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
                                          : slot.runtime === "terminal" && slot.windows.length === 0 ? terminalPaneSummary(t, slot) : paneSummary(t, panes[pane.windowIndex ?? paneIndex])}
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
                      onClick={addTab}
                      className="w-full min-h-11 rounded-md border border-dashed border-[var(--accent-border)] bg-[var(--accent-bg)]/45 p-2 text-center text-[12px] font-semibold text-[var(--accent)] hover:bg-[var(--accent-bg)] transition-colors"
                    >
                      <Plus className="w-3.5 h-3.5 inline-block mr-1.5 align-[-2px]" />
                      {t("addTab")}
                    </button>
                  </div>
                </div>
              </div>

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
                    <section className="space-y-3 pt-3 border-t border-default">
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("groupPosition")}</p>
                        <p className="mt-0.5 text-[11px] text-tertiary">{t("groupPositionHint")}</p>
                      </div>
                      <div className="grid grid-cols-2 gap-1.5">
                        <button
                          type="button"
                          onClick={() => moveSelectedTmuxGroup(-1)}
                          disabled={!canMoveSelectedGroupUp}
                          className="min-h-10 rounded-md border border-default bg-[var(--bg-card)] px-2 text-left text-[12px] text-secondary hover:text-primary hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] transition-colors disabled:opacity-35 disabled:hover:bg-[var(--bg-card)]"
                        >
                          <span className="inline-flex items-center gap-1.5">
                            <ArrowUp className="h-3.5 w-3.5 text-tertiary" />
                            {t("moveUp")}
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={() => moveSelectedTmuxGroup(1)}
                          disabled={!canMoveSelectedGroupDown}
                          className="min-h-10 rounded-md border border-default bg-[var(--bg-card)] px-2 text-left text-[12px] text-secondary hover:text-primary hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] transition-colors disabled:opacity-35 disabled:hover:bg-[var(--bg-card)]"
                        >
                          <span className="inline-flex items-center gap-1.5">
                            <ArrowDown className="h-3.5 w-3.5 text-tertiary" />
                            {t("moveDown")}
                          </span>
                        </button>
                      </div>
                      <button
                        type="button"
                        onClick={deleteSelectedTmuxGroup}
                        className="w-full control-touch rounded-md border border-[var(--danger)]/20 text-[12px] text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors flex items-center justify-center gap-1.5"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        {t("removeGroup")}
                      </button>
                    </section>
                    ) : null}

                    {editingPane && !selectedTmuxGroup ? (
                    <section className="space-y-3 pt-3 border-t border-default">
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("scheduling")}</p>
                        <p className="mt-0.5 text-[11px] text-tertiary">{t("canvasSchedulingHint")}</p>
                      </div>
                      <div className="grid grid-cols-2 gap-1.5">
                        <button
                          type="button"
                          onClick={() => splitSelectedPane("horizontal")}
                          className="min-h-10 rounded-md border border-default bg-[var(--bg-card)] px-2 text-left text-[12px] text-secondary hover:text-primary hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] transition-colors"
                        >
                          <span className="inline-flex items-center gap-1.5">
                            <Plus className="h-3.5 w-3.5 text-tertiary" />
                            {t("splitRight")}
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={() => splitSelectedPane("vertical")}
                          className="min-h-10 rounded-md border border-default bg-[var(--bg-card)] px-2 text-left text-[12px] text-secondary hover:text-primary hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] transition-colors"
                        >
                          <span className="inline-flex items-center gap-1.5">
                            <Plus className="h-3.5 w-3.5 text-tertiary" />
                            {t("splitDown")}
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={duplicatePane}
                          className="col-span-2 min-h-10 rounded-md border border-default bg-[var(--bg-card)] px-2 text-left text-[12px] text-secondary hover:text-primary hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] transition-colors"
                        >
                          <span className="inline-flex items-center gap-1.5">
                            <Copy className="h-3.5 w-3.5 text-tertiary" />
                            {t("duplicatePane")}
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={() => movePane(-1)}
                          disabled={!canMoveSelectedPaneUp}
                          className="min-h-10 rounded-md border border-default bg-[var(--bg-card)] px-2 text-left text-[12px] text-secondary hover:text-primary hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] transition-colors disabled:opacity-35 disabled:hover:bg-[var(--bg-card)]"
                        >
                          <span className="inline-flex items-center gap-1.5">
                            <ArrowUp className="h-3.5 w-3.5 text-tertiary" />
                            {t("moveUp")}
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={() => movePane(1)}
                          disabled={!canMoveSelectedPaneDown}
                          className="min-h-10 rounded-md border border-default bg-[var(--bg-card)] px-2 text-left text-[12px] text-secondary hover:text-primary hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] transition-colors disabled:opacity-35 disabled:hover:bg-[var(--bg-card)]"
                        >
                          <span className="inline-flex items-center gap-1.5">
                            <ArrowDown className="h-3.5 w-3.5 text-tertiary" />
                            {t("moveDown")}
                          </span>
                        </button>
                      </div>
                    </section>
                    ) : null}

                    {editingPane && selectedMovablePane && slots.length > 1 ? (
                    <section className="space-y-3 pt-3 border-t border-default">
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("moveToTab")}</p>
                        <p className="mt-0.5 text-[11px] text-tertiary">{t("moveToTabHint")}</p>
                      </div>
                      {moveTargetOptions.length > 0 ? (
                        <div className="space-y-2">
                          <SelectInput
                            value={moveTarget}
                            onChange={setMoveTarget}
                            options={moveTargetOptions}
                            ariaLabel={t("moveToTab")}
                          />
                          <button
                            type="button"
                            onClick={movePaneToTab}
                            disabled={!canMovePaneToSelectedTab}
                            className="w-full control-touch rounded-md bg-[var(--accent-bg)] text-[var(--accent)] text-[12px] font-semibold border border-[var(--accent-border)] disabled:opacity-40 flex items-center justify-center gap-1.5"
                          >
                            <MoveRight className="h-3.5 w-3.5" />
                            {t("move")}
                          </button>
                        </div>
                      ) : (
                        <div className="rounded-md border border-dashed border-default bg-[var(--bg-hover)]/35 px-3 py-2 text-[11px] text-tertiary">
                          {t("noCompatibleTabs")}
                        </div>
                      )}
                    </section>
                    ) : null}

                    {editingPane && !selectedTmuxGroup ? (
                    <section className="space-y-2.5 pt-3 border-t border-default">
                      <button
                        type="button"
                        onClick={deletePane}
                        className="w-full control-touch rounded-md border border-[var(--danger)]/20 text-[12px] text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors flex items-center justify-center gap-1.5"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        {t("removePane")}
                      </button>
                    </section>
                    ) : null}
                  </div>
                </aside>
              )}
            </div>
          )}
    </section>
  );
}
