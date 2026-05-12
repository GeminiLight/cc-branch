/**
 * ConfigEditor — Workspace canvas for Tab / Pane layout editing.
 *
 * The persisted schema is still slots/windows. The UI presents those as
 * tabs/panes so users edit the workspace model, not the storage model.
 */

import { useEffect, useMemo, useState, type CSSProperties, type DragEvent } from "react";
import {
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  Clock3,
  PanelsTopLeft,
  Plus,
  SquareTerminal,
  Terminal,
  Trash2,
} from "lucide-react";
import { useI18n } from "../../i18n";
import type { AgentSessionInfo, RuntimeAvailability } from "../../types";
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

type Selection = {
  slotIndex: number;
  target: "tab" | "pane";
  windowIndex: number | null;
};

type TabLayout = NonNullable<SlotConfig["layout"]>;
type PaneDragState = { slotIndex: number; paneIndex: number } | null;
type TabDragState = { slotIndex: number } | null;

function displayAgentName(agent: string | null | undefined): string {
  return agent ? agent.charAt(0).toUpperCase() + agent.slice(1) : "";
}

function runtimeLabel(t: (key: string, vars?: Record<string, string | number>) => string, runtime: SlotConfig["runtime"]): string {
  return runtime === "terminal" ? t("runtimeTerminal") : t("runtimeTmux");
}

function RuntimeIcon({ runtime, className = "w-3.5 h-3.5" }: { runtime: SlotConfig["runtime"]; className?: string }) {
  return runtime === "terminal"
    ? <SquareTerminal className={className} aria-hidden="true" />
    : <PanelsTopLeft className={className} aria-hidden="true" />;
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

function emptyWindow(name = "main", agent: string | null = null): WindowConfig {
  return {
    name,
    agent,
    command: null,
    cwd: null,
    env: {},
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

function paneCount(slot: SlotConfig): number {
  return slot.runtime === "terminal" ? Math.max(slot.windows.length, 1) : Math.max(slot.windows.length, 0);
}

function tabSummary(t: (key: string, vars?: Record<string, string | number>) => string, slot: SlotConfig): string {
  if (slot.runtime === "terminal") {
    if (slot.windows.length > 1) return t("tabSummaryPanes", { count: slot.windows.length });
    if (slot.windows.length === 1) return paneSummary(t, slot.windows[0]);
    if (slot.agent) return t("tabSummaryTerminalAgent", { agent: displayAgentName(slot.agent) });
    return t("tabSummaryCommand", { command: slot.command || "$SHELL" });
  }
  return t("tabSummaryPanes", { count: slot.windows.length });
}

function paneSummary(t: (key: string, vars?: Record<string, string | number>) => string, win: WindowConfig): string {
  if (win.agent) return t("paneSummaryAgent", { agent: displayAgentName(win.agent) });
  if (win.command) return t("paneSummaryCommand", { command: win.command });
  return t("paneSummaryInherited");
}

function terminalPaneName(slot: SlotConfig): string {
  return slot.title || slot.name || "terminal";
}

function terminalSlotToWindow(slot: SlotConfig): WindowConfig {
  return {
    ...emptyWindow(terminalPaneName(slot), slot.agent ?? null),
    command: slot.agent ? null : slot.command ?? "$SHELL",
    cwd: slot.cwd || null,
    env: { ...slot.env },
    session_id: slot.session_id ?? null,
    label: slot.label ?? null,
  };
}

function terminalPaneSummary(t: (key: string, vars?: Record<string, string | number>) => string, slot: SlotConfig): string {
  if (slot.agent) return t("paneSummaryAgent", { agent: displayAgentName(slot.agent) });
  return t("paneSummaryCommand", { command: slot.command || "$SHELL" });
}

function normalizedLayout(slot: SlotConfig, paneLength: number): TabLayout {
  const layout = slot.layout || "auto";
  if (layout !== "auto") return layout;
  if (paneLength <= 2) return "horizontal";
  if (paneLength === 3) return "main-left";
  return "grid";
}

function layoutLabel(t: (key: string, vars?: Record<string, string | number>) => string, layout: SlotConfig["layout"]): string {
  const key = layout || "auto";
  if (key === "horizontal") return t("layoutHorizontal");
  if (key === "vertical") return t("layoutVertical");
  if (key === "main-left") return t("layoutMainLeft");
  if (key === "main-top") return t("layoutMainTop");
  if (key === "grid") return t("layoutGrid");
  return t("layoutAuto");
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

function slotToPanes(slot: SlotConfig): WindowConfig[] {
  if (slot.runtime === "tmux") {
    return slot.windows.length > 0 ? slot.windows : [emptyWindow("main")];
  }
  return slot.windows.length > 0 ? slot.windows : [terminalSlotToWindow(slot)];
}

function editableWindowsForSlot(slot: SlotConfig): WindowConfig[] {
  if (slot.windows.length > 0) return [...slot.windows];
  if (slot.runtime === "terminal") return [terminalSlotToWindow(slot)];
  return [emptyWindow("main")];
}

function slotWithWindows(slot: SlotConfig, windows: WindowConfig[], layout?: TabLayout): SlotConfig {
  const next: SlotConfig = {
    ...slot,
    windows,
    ...(layout ? { layout } : {}),
  };
  if (slot.runtime === "terminal") {
    return {
      ...next,
      command: undefined,
      title: undefined,
      agent: undefined,
      session_id: undefined,
      label: undefined,
    };
  }
  return next;
}

function canDragPane(slot: SlotConfig): boolean {
  return slot.runtime === "tmux" || slot.windows.length > 0;
}

function clampSelection(selection: Selection, slots: SlotConfig[]): Selection {
  if (slots.length === 0) return { slotIndex: 0, target: "tab", windowIndex: null };
  const slotIndex = Math.min(Math.max(selection.slotIndex, 0), slots.length - 1);
  const slot = slots[slotIndex];
  if (selection.target === "tab") return { slotIndex, target: "tab", windowIndex: null };
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

function SessionIdInput({
  value,
  onChange,
  agent,
  sessions,
  loading,
}: {
  value: string;
  onChange: (value: string) => void;
  agent?: string | null;
  sessions: AgentSessionInfo[];
  loading?: boolean;
}) {
  const { t } = useI18n();
  const agentKey = normalizeAgentKey(agent);
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

  return (
    <div className="flex items-center rounded-lg border border-default bg-[var(--bg-card)] transition-all hover:border-[var(--border-strong)] focus-within:ring-2 focus-within:ring-[var(--accent-border)] focus-within:border-[var(--accent)]">
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={
          displayAgent
            ? t("sessionIdPlaceholderWithAgent", { agent: displayAgent })
            : t("sessionIdPlaceholder")
        }
        className="min-w-0 flex-1 control-touch px-3 rounded-l-lg text-[13px] bg-transparent placeholder:text-muted focus:outline-none"
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
          <span className="control-touch min-w-9 px-2 border-l border-default text-tertiary hover:text-primary hover:bg-[var(--bg-hover)] rounded-r-lg transition-colors flex items-center justify-center">
            <ChevronsUpDown className="w-3.5 h-3.5" />
          </span>
        }
      />
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
  agentSessions,
  agentSessionsLoading,
  onChange,
  runtimeAvailability,
}: {
  slots: SlotConfig[];
  agents: string[];
  agentSessions: AgentSessionInfo[];
  agentSessionsLoading?: boolean;
  onChange: (slots: SlotConfig[]) => void;
  runtimeAvailability?: RuntimeAvailability;
}) {
  const { t } = useI18n();
  const defaultRuntime = runtimeAvailability?.tmux?.available === false ? "terminal" : "tmux";
  const tmuxUnavailable = runtimeAvailability?.tmux?.available === false;
  const [selection, setSelection] = useState<Selection>({ slotIndex: 0, target: "tab", windowIndex: null });
  const [moveTarget, setMoveTarget] = useState("0");
  const [paneDrag, setPaneDrag] = useState<PaneDragState>(null);
  const [tabDrag, setTabDrag] = useState<TabDragState>(null);

  const normalizedSelection = useMemo(() => clampSelection(selection, slots), [selection, slots]);
  const selectedSlot = slots[normalizedSelection.slotIndex];
  const selectedWindow =
    normalizedSelection.target === "pane" && selectedSlot?.windows.length
      ? selectedSlot.windows[normalizedSelection.windowIndex ?? 0]
      : null;
  const selectedTerminalPane =
    normalizedSelection.target === "pane" &&
    selectedSlot?.runtime === "terminal" &&
    selectedSlot.windows.length === 0;
  const selectedTerminalWindow = selectedSlot?.runtime === "terminal" ? selectedWindow : null;
  const editingPane = Boolean(selectedWindow || selectedTerminalPane);

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

  useEffect(() => {
    if (slots.length > 1) {
      const selectedRuntime = slots[normalizedSelection.slotIndex]?.runtime;
      const runtimeFallback = slots.findIndex((slot, index) => index !== normalizedSelection.slotIndex && slot.runtime === selectedRuntime);
      setMoveTarget(String(runtimeFallback >= 0 ? runtimeFallback : normalizedSelection.slotIndex));
    } else {
      setMoveTarget("0");
    }
  }, [normalizedSelection.slotIndex, slots]);

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

  const tabOptions = slots.map((slot, index) => ({
    value: String(index),
    label: `${slot.name || t("unnamed")} ${slot.runtime === "tmux" ? "" : `(${t("runtimeTerminal")})`}`,
    disabled: slot.runtime !== selectedSlot?.runtime || index === normalizedSelection.slotIndex,
  }));
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

  function moveTab(index: number, dir: number) {
    const next = [...slots];
    const [moved] = next.splice(index, 1);
    next.splice(index + dir, 0, moved);
    replaceSlots(next, {
      slotIndex: index + dir,
      target: normalizedSelection.target,
      windowIndex: normalizedSelection.windowIndex,
    });
  }

  function moveTabByDrag(fromSlotIndex: number, toSlotIndex: number) {
    if (fromSlotIndex < 0 || fromSlotIndex >= slots.length) return;
    const next = [...slots];
    const selectedBeforeMove = slots[normalizedSelection.slotIndex];
    const [moved] = next.splice(fromSlotIndex, 1);
    if (!moved) return;
    const insertIndex = Math.min(
      Math.max(fromSlotIndex < toSlotIndex ? toSlotIndex - 1 : toSlotIndex, 0),
      next.length
    );
    next.splice(insertIndex, 0, moved);
    const nextSelectedIndex = selectedBeforeMove ? Math.max(next.indexOf(selectedBeforeMove), 0) : insertIndex;
    replaceSlots(next, {
      slotIndex: nextSelectedIndex,
      target: normalizedSelection.target,
      windowIndex: normalizedSelection.windowIndex,
    });
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

  function setRuntime(runtime: SlotConfig["runtime"]) {
    if (!selectedSlot) return;
    if (runtime === selectedSlot.runtime) return;
    if (runtime === "tmux") {
      updateSlot(normalizedSelection.slotIndex, {
        runtime,
        windows: [
          emptyWindow(
            selectedSlot.title || selectedSlot.name || "main",
            selectedSlot.agent ?? null
          ),
        ].map((win) => ({
          ...win,
          command: selectedSlot.command ?? null,
          session_id: selectedSlot.session_id ?? null,
          label: selectedSlot.label ?? null,
        })),
        command: undefined,
        title: undefined,
        agent: undefined,
        session_id: undefined,
        label: undefined,
      });
      setSelection({ slotIndex: normalizedSelection.slotIndex, target: "tab", windowIndex: null });
    } else {
      const first = selectedSlot.windows[normalizedSelection.windowIndex ?? 0] || selectedSlot.windows[0];
      updateSlot(normalizedSelection.slotIndex, {
        runtime,
        windows: [],
        title: first?.name || selectedSlot.name,
        agent: first?.agent ?? undefined,
        command: first?.agent ? undefined : first?.command ?? "$SHELL",
        session_id: first?.session_id ?? undefined,
        label: first?.label ?? undefined,
      });
      setSelection({ slotIndex: normalizedSelection.slotIndex, target: "tab", windowIndex: null });
    }
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
    const windows = editableWindowsForSlot(slot);
    const insertAt = afterIndex == null ? windows.length : Math.min(afterIndex + 1, windows.length);
    windows.splice(insertAt, 0, emptyWindow(`pane-${windows.length + 1}`, agents[0] ?? null));
    const next = [...slots];
    next[slotIndex] = slotWithWindows(slot, windows, layout || slot.layout || "auto");
    replaceSlots(next, { slotIndex, target: "pane", windowIndex: insertAt });
  }

  function setSlotLayout(index: number, layout: TabLayout) {
    const slot = slots[index];
    if (!slot) return;
    updateSlot(index, { layout });
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
    replaceSlots(next, { slotIndex, target: "pane", windowIndex: Math.max(0, targetIndex - 1) });
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
    replaceSlots(next, { slotIndex, target: "pane", windowIndex: targetIndex });
  }

  function movePaneByDrag(fromSlotIndex: number, fromPaneIndex: number, toSlotIndex: number, toPaneIndex: number) {
    const source = slots[fromSlotIndex];
    const target = slots[toSlotIndex];
    if (!source || !target || source.runtime !== target.runtime) return;
    if (source.runtime === "terminal" && source.windows.length === 0) return;
    if (fromSlotIndex === toSlotIndex && fromPaneIndex === toPaneIndex) return;

    const next = [...slots];
    const sourceWindows = editableWindowsForSlot(source);
    const [moved] = sourceWindows.splice(fromPaneIndex, 1);
    if (!moved) return;

    if (fromSlotIndex === toSlotIndex) {
      const insertIndex = Math.min(
        Math.max(fromPaneIndex < toPaneIndex ? toPaneIndex - 1 : toPaneIndex, 0),
        sourceWindows.length
      );
      sourceWindows.splice(insertIndex, 0, moved);
      next[fromSlotIndex] = slotWithWindows(source, sourceWindows);
      replaceSlots(next, { slotIndex: toSlotIndex, target: "pane", windowIndex: insertIndex });
      return;
    }

    const targetWindows = editableWindowsForSlot(target);
    const insertIndex = Math.min(Math.max(toPaneIndex, 0), targetWindows.length);
    targetWindows.splice(insertIndex, 0, moved);
    if (sourceWindows.length === 0) {
      next.splice(fromSlotIndex, 1);
      const adjustedTargetIndex = fromSlotIndex < toSlotIndex ? toSlotIndex - 1 : toSlotIndex;
      next[adjustedTargetIndex] = slotWithWindows(target, targetWindows);
      replaceSlots(next, { slotIndex: adjustedTargetIndex, target: "pane", windowIndex: insertIndex });
      return;
    }
    next[fromSlotIndex] = slotWithWindows(source, sourceWindows);
    next[toSlotIndex] = slotWithWindows(target, targetWindows);
    replaceSlots(next, { slotIndex: toSlotIndex, target: "pane", windowIndex: insertIndex });
  }

  function handlePaneDragStart(event: DragEvent<HTMLElement>, slotIndex: number, paneIndex: number) {
    const slot = slots[slotIndex];
    if (!slot || !canDragPane(slot)) return;
    event.stopPropagation();
    setPaneDrag({ slotIndex, paneIndex });
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", `${slotIndex}:${paneIndex}`);
  }

  function handlePaneDragOver(event: DragEvent<HTMLElement>, slotIndex: number) {
    const target = slots[slotIndex];
    const source = paneDrag ? slots[paneDrag.slotIndex] : null;
    if (!paneDrag || !target || !source || target.runtime !== source.runtime) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }

  function handlePaneDrop(event: DragEvent<HTMLElement>, slotIndex: number, paneIndex: number) {
    event.preventDefault();
    event.stopPropagation();
    if (!paneDrag) return;
    const target = slots[slotIndex];
    const rect = event.currentTarget.getBoundingClientRect();
    const layout = target ? normalizedLayout(target, slotToPanes(target).length) : "horizontal";
    const verticalDrop = layout === "vertical" || layout === "main-top";
    const after =
      verticalDrop
        ? event.clientY > rect.top + rect.height / 2
        : event.clientX > rect.left + rect.width / 2;
    movePaneByDrag(paneDrag.slotIndex, paneDrag.paneIndex, slotIndex, paneIndex + (after ? 1 : 0));
    setPaneDrag(null);
  }

  function handlePaneAppendDrop(event: DragEvent<HTMLElement>, slotIndex: number) {
    event.preventDefault();
    event.stopPropagation();
    const target = slots[slotIndex];
    const source = paneDrag ? slots[paneDrag.slotIndex] : null;
    if (!paneDrag || !target || !source || target.runtime !== source.runtime) return;
    movePaneByDrag(paneDrag.slotIndex, paneDrag.paneIndex, slotIndex, slotToPanes(target).length);
    setPaneDrag(null);
  }

  function movePaneToTab() {
    if (!selectedSlot || !selectedWindow) return;
    const targetIndex = Number(moveTarget);
    const target = slots[targetIndex];
    if (!target || target.runtime !== selectedSlot.runtime || targetIndex === normalizedSelection.slotIndex) return;
    const next = [...slots];
    const sourceWindows = editableWindowsForSlot(selectedSlot);
    const [moved] = sourceWindows.splice(normalizedSelection.windowIndex ?? 0, 1);
    if (!moved) return;
    const targetWindows = editableWindowsForSlot(target);
    if (sourceWindows.length === 0) {
      next.splice(normalizedSelection.slotIndex, 1);
      const adjustedTargetIndex = normalizedSelection.slotIndex < targetIndex ? targetIndex - 1 : targetIndex;
      next[adjustedTargetIndex] = slotWithWindows(target, [...targetWindows, moved]);
      replaceSlots(next, { slotIndex: adjustedTargetIndex, target: "pane", windowIndex: targetWindows.length });
      return;
    }
    next[normalizedSelection.slotIndex] = slotWithWindows(selectedSlot, sourceWindows);
    next[targetIndex] = slotWithWindows(target, [...targetWindows, moved]);
    replaceSlots(next, { slotIndex: targetIndex, target: "pane", windowIndex: targetWindows.length });
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
              <div className="min-w-0 rounded-lg border border-default bg-[var(--bg-card)] overflow-hidden">
                <div className="px-3 py-2 border-b border-subtle flex items-center justify-between gap-3 bg-[var(--bg-card)]">
                  <div className="min-w-0">
                    <p className="text-[12px] font-semibold text-primary">{t("matrixCanvas")}</p>
                    <p className="text-[11px] text-tertiary truncate">{t("matrixCanvasHint")}</p>
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
                <div className="workspace-matrix-surface relative p-2 min-h-[300px]">
                  <div
                    className="absolute inset-0 opacity-[0.10] pointer-events-none"
                    style={{
                      backgroundImage:
                        "linear-gradient(var(--border-subtle) 1px, transparent 1px), linear-gradient(90deg, var(--border-subtle) 1px, transparent 1px)",
                      backgroundSize: "28px 28px",
                    }}
                  />
                  <div className="relative space-y-2">
                    {slots.map((slot, slotIndex) => {
                      const selectedTab = slotIndex === normalizedSelection.slotIndex;
                      const slotName = slot.name || t("unnamed");
                      const panes = slotToPanes(slot);
                      const layout = slot.layout || "auto";
                      const tabAgent = slot.runtime === "terminal" && slot.windows.length === 0
                        ? slot.agent ?? null
                        : panes.find((pane) => pane.agent)?.agent ?? null;
                      return (
                        <section
                          key={`${slot.name}-${slotIndex}`}
                          draggable
                          onDragStart={(event) => handleTabDragStart(event, slotIndex)}
                          onDragOver={handleTabDragOver}
                          onDrop={(event) => handleTabDrop(event, slotIndex)}
                          onDragEnd={() => setTabDrag(null)}
                          className={`rounded-md border bg-[var(--bg-card)] transition-all overflow-hidden ${
                            selectedTab
                              ? "border-[var(--accent-border)] shadow-[inset_3px_0_0_var(--accent)]"
                              : "border-default hover:border-[var(--border-strong)]"
                          } ${
                            tabDrag?.slotIndex === slotIndex ? "opacity-55" : ""
                          }`}
                        >
                          <div className="grid grid-cols-1 lg:grid-cols-[132px_minmax(0,1fr)]">
                            <button
                              type="button"
                              onClick={() => setSelection({ slotIndex, target: "tab", windowIndex: null })}
                              className="workspace-tab-rail text-left p-2.5 border-b lg:border-b-0 lg:border-r border-subtle hover:bg-[var(--bg-hover)]/55 transition-colors"
                              aria-label={selectedTab ? t("collapseSlot", { name: slotName }) : t("expandSlot", { name: slotName })}
                            >
                              <span className="block text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("tab")}</span>
                              <span className="mt-0.5 flex items-center gap-1.5 text-[13px] font-semibold text-primary">
                                <AgentMark agent={tabAgent} compact />
                                <span className="truncate">{slotName}</span>
                              </span>
                              <span className="block mt-0.5 text-[10px] text-tertiary truncate">{tabSummary(t, slot)}</span>
                              <span className="mt-1.5 flex items-center justify-between gap-2">
                                <span className="inline-flex rounded-md border border-default bg-[var(--bg-card)] px-1.5 py-0.5 text-[10px] font-semibold text-tertiary">
                                  {layoutLabel(t, layout)}
                                </span>
                                <ChevronsUpDown className="w-3.5 h-3.5 text-muted cursor-grab active:cursor-grabbing" aria-hidden="true" />
                              </span>
                            </button>

                            <div className="min-w-0 p-2">
                              <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                                <div className="flex items-center gap-1.5 min-w-0">
                                  <span className="inline-flex items-center gap-1.5 rounded-md bg-[var(--bg-hover)]/70 px-2 py-1 text-[10px] font-semibold text-tertiary">
                                    <RuntimeIcon runtime={slot.runtime} className="w-3 h-3 text-[var(--accent)]" />
                                    {runtimeLabel(t, slot.runtime)}
                                  </span>
                                  <span className="text-[11px] text-tertiary truncate">{t("tabSummaryPanes", { count: paneCount(slot) })}</span>
                                </div>
                                <div className="flex items-center gap-1.5 shrink-0">
                                  <button
                                    type="button"
                                    onClick={() => addPaneToSlot(slotIndex, slotToPanes(slot).length - 1)}
                                    className="icon-touch sm:min-h-8 sm:min-w-8 rounded-md text-tertiary hover:text-primary hover:surface-hover flex items-center justify-center"
                                    aria-label={t("addPane")}
                                    title={t("addPane")}
                                  >
                                    <Plus className="w-3.5 h-3.5" />
                                  </button>
                                  {(slot.runtime === "tmux" || panes.length > 1) && (
                                    <LayoutPicker
                                      value={layout}
                                      options={layoutOptions}
                                      onChange={(value) => setSlotLayout(slotIndex, value)}
                                      compact
                                    />
                                  )}
                                  <button
                                    type="button"
                                    onClick={() => moveTab(slotIndex, -1)}
                                    disabled={slotIndex === 0}
                                    className="icon-touch sm:min-h-8 sm:min-w-8 rounded-md text-tertiary hover:text-primary hover:surface-hover disabled:opacity-30 flex items-center justify-center"
                                    aria-label={t("moveSlotUp", { name: slotName })}
                                    title={t("moveSlotUp", { name: slotName })}
                                  >
                                    <ChevronUp className="w-3 h-3" />
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => moveTab(slotIndex, 1)}
                                    disabled={slotIndex === slots.length - 1}
                                    className="icon-touch sm:min-h-8 sm:min-w-8 rounded-md text-tertiary hover:text-primary hover:surface-hover disabled:opacity-30 flex items-center justify-center"
                                    aria-label={t("moveSlotDown", { name: slotName })}
                                    title={t("moveSlotDown", { name: slotName })}
                                  >
                                    <ChevronDown className="w-3 h-3" />
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
                                {slot.runtime === "tmux" && (
                                  <div className="rounded-md border border-subtle bg-[var(--bg-hover)]/35 px-2.5 py-2">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                      <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-tertiary">
                                        <PanelsTopLeft className="w-3 h-3 text-[var(--accent)]" />
                                        {t("tmuxWindowStack")}
                                      </span>
                                      <span className="text-[10px] text-tertiary">{t("tmuxWindowCount", { count: panes.length })}</span>
                                    </div>
                                    <div className="mt-1.5 flex flex-wrap gap-1">
                                      {panes.map((pane, paneIndex) => (
                                        <span
                                          key={`${pane.name}-${paneIndex}-chip`}
                                          className="inline-flex items-center gap-1 rounded-md border border-default bg-[var(--bg-card)] px-1.5 py-0.5 text-[10px] text-secondary"
                                        >
                                          <AgentMark agent={pane.agent} compact />
                                          <span className="truncate max-w-[120px]">{pane.name || t("unnamed")}</span>
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                <div
                                  className="grid gap-1.5 min-h-[78px]"
                                  style={paneGridStyle(slot, panes)}
                                  onDragOver={(event) => handlePaneDragOver(event, slotIndex)}
                                  onDrop={(event) => handlePaneAppendDrop(event, slotIndex)}
                                >
                                  {panes.map((pane, paneIndex) => {
                                    const selectedPane =
                                      selectedTab &&
                                      normalizedSelection.target === "pane" &&
                                      (slot.runtime === "terminal" && slot.windows.length === 0
                                        ? normalizedSelection.windowIndex === null
                                        : normalizedSelection.windowIndex === paneIndex);
                                    const paneName = slot.runtime === "terminal" && slot.windows.length === 0
                                      ? terminalPaneName(slot)
                                      : pane.name || t("unnamed");
                                    const cwdLabel = pane.cwd || slot.cwd || "";
                                    const paneAgent = slot.runtime === "terminal" && slot.windows.length === 0 ? slot.agent ?? null : pane.agent ?? null;
                                    const paneIsDraggable = canDragPane(slot);
                                    return (
                                      <div
                                        role="button"
                                        tabIndex={0}
                                        key={`${pane.name}-${paneIndex}`}
                                        onClick={() => setSelection({
                                          slotIndex,
                                          target: "pane",
                                          windowIndex: slot.windows.length > 0 || slot.runtime === "tmux" ? paneIndex : null,
                                        })}
                                        draggable={paneIsDraggable}
                                        onDragStart={(event) => handlePaneDragStart(event, slotIndex, paneIndex)}
                                        onDragOver={(event) => handlePaneDragOver(event, slotIndex)}
                                        onDrop={(event) => handlePaneDrop(event, slotIndex, paneIndex)}
                                        onDragEnd={() => setPaneDrag(null)}
                                        onKeyDown={(event) => {
                                          if (event.key === "Enter" || event.key === " ") {
                                            event.preventDefault();
                                            setSelection({
                                              slotIndex,
                                              target: "pane",
                                              windowIndex: slot.windows.length > 0 || slot.runtime === "tmux" ? paneIndex : null,
                                            });
                                          }
                                        }}
                                        className={`workspace-pane-card group/pane relative min-h-[72px] rounded-md border p-2.5 text-left transition-all ${
                                          selectedPane
                                            ? "border-[var(--accent-border)] bg-[var(--accent-bg)]"
                                            : "border-default hover:border-[var(--border-strong)]"
                                        } ${
                                          paneDrag?.slotIndex === slotIndex && paneDrag.paneIndex === paneIndex
                                            ? "opacity-55"
                                            : ""
                                        }`}
                                        style={paneCellStyle(slot, panes, paneIndex)}
                                        aria-label={t("expandWindow", { name: paneName })}
                                      >
                                      <span className="flex items-start justify-between gap-2 pr-14">
                                        <span className="flex min-w-0 items-start gap-2">
                                          <AgentMark agent={paneAgent} />
                                          <span className="min-w-0">
                                            <span className="block text-[10px] font-semibold uppercase tracking-wide text-tertiary">
                                              {slot.runtime === "tmux" ? t("tmuxWindow") : t("pane")}
                                            </span>
                                            <span className="block mt-0.5 text-[13px] font-semibold text-primary truncate">{paneName}</span>
                                          </span>
                                        </span>
                                        {!paneIsDraggable ? (
                                          <SquareTerminal className="w-4 h-4 text-[var(--accent)] shrink-0" aria-hidden="true" />
                                        ) : (
                                          <ChevronsUpDown className="w-4 h-4 text-tertiary shrink-0 cursor-grab active:cursor-grabbing" aria-label={t("dragPane")} />
                                        )}
                                      </span>
                                      <span className="mt-2 block text-[12px] text-secondary truncate">
                                        {slot.runtime === "terminal" && slot.windows.length === 0 ? terminalPaneSummary(t, slot) : paneSummary(t, pane)}
                                      </span>
                                      {cwdLabel && cwdLabel !== "." && (
                                        <span className="mt-0.5 block text-[10px] text-tertiary font-mono truncate">
                                          {cwdLabel}
                                        </span>
                                      )}
                                      {canDragPane(slot) && (
                                        <span className="absolute right-2 top-2 flex items-center gap-1 rounded-md border border-default bg-[var(--bg-card)]/95 p-0.5 opacity-0 shadow-sm transition-opacity group-hover/pane:opacity-100 group-focus-within/pane:opacity-100">
                                          <button
                                            type="button"
                                            onClick={(event) => {
                                              event.stopPropagation();
                                              addPaneToSlot(slotIndex, paneIndex);
                                            }}
                                            className="icon-touch sm:min-h-6 sm:min-w-6 rounded text-[11px] text-secondary hover:text-primary hover:bg-[var(--bg-hover)] flex items-center justify-center"
                                            aria-label={t("splitPane")}
                                            title={t("splitPane")}
                                          >
                                            +
                                          </button>
                                          <button
                                            type="button"
                                            onClick={(event) => {
                                              event.stopPropagation();
                                              movePaneAtSlot(slotIndex, paneIndex, -1);
                                            }}
                                            disabled={paneIndex === 0}
                                            className="icon-touch sm:min-h-6 sm:min-w-6 rounded text-[11px] text-secondary hover:text-primary hover:bg-[var(--bg-hover)] flex items-center justify-center disabled:opacity-35"
                                            aria-label={t("moveWindowUp", { name: paneName })}
                                            title={t("moveWindowUp", { name: paneName })}
                                          >
                                            ↑
                                          </button>
                                          <button
                                            type="button"
                                            onClick={(event) => {
                                              event.stopPropagation();
                                              movePaneAtSlot(slotIndex, paneIndex, 1);
                                            }}
                                            disabled={paneIndex === panes.length - 1}
                                            className="icon-touch sm:min-h-6 sm:min-w-6 rounded text-[11px] text-secondary hover:text-primary hover:bg-[var(--bg-hover)] flex items-center justify-center disabled:opacity-35"
                                            aria-label={t("moveWindowDown", { name: paneName })}
                                            title={t("moveWindowDown", { name: paneName })}
                                          >
                                            ↓
                                          </button>
                                          <button
                                            type="button"
                                            onClick={(event) => {
                                              event.stopPropagation();
                                              duplicatePaneAtSlot(slotIndex, paneIndex);
                                            }}
                                            className="icon-touch sm:min-h-6 sm:min-w-6 rounded text-[11px] text-secondary hover:text-primary hover:bg-[var(--bg-hover)] flex items-center justify-center"
                                            aria-label={t("duplicatePane")}
                                            title={t("duplicatePane")}
                                          >
                                            ⧉
                                          </button>
                                          <button
                                            type="button"
                                            onClick={(event) => {
                                              event.stopPropagation();
                                              deletePaneAtSlot(slotIndex, paneIndex);
                                            }}
                                            className="icon-touch sm:min-h-6 sm:min-w-6 rounded text-[11px] text-[var(--danger)] hover:bg-[var(--danger-bg)] flex items-center justify-center"
                                            aria-label={t("removeWindow", { name: paneName })}
                                            title={t("removeWindow", { name: paneName })}
                                          >
                                            ×
                                          </button>
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
                    <h3 className="mt-1 text-[15px] font-semibold text-primary">
                      {editingPane ? t("selectedPane") : t("selectedTab")}
                    </h3>
                  </div>

                  <div className="p-3 space-y-4">
                    {!editingPane && (
                    <section className="space-y-2.5">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("tab")}</p>
                        <span className="text-[10px] text-tertiary">{runtimeLabel(t, selectedSlot.runtime)}</span>
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
                          <FieldLabel>{t("runtime")}</FieldLabel>
                          <SelectInput
                            value={selectedSlot.runtime}
                            onChange={(value) => setRuntime(value as SlotConfig["runtime"])}
                            options={[
                              {
                                value: "tmux",
                                label: tmuxUnavailable ? `Tmux (${t("unavailable")})` : "Tmux",
                                disabled: tmuxUnavailable,
                              },
                              { value: "terminal", label: t("openTerminal") },
                            ]}
                          />
                        </div>
                        <div>
                          <FieldLabel>{t("workingDirectory")}</FieldLabel>
                          <TextInput
                            value={selectedSlot.cwd}
                            onChange={(value) => updateSlot(normalizedSelection.slotIndex, { cwd: value })}
                            placeholder="."
                          />
                        </div>
                        <div>
                          <FieldLabel>{t("tabLayout")}</FieldLabel>
                          <LayoutPicker
                            value={selectedSlot.layout || "auto"}
                            options={layoutOptions}
                            onChange={(value) => updateSlot(normalizedSelection.slotIndex, { layout: value })}
                          />
                        </div>
                      </div>
                      <details className="group rounded-md border border-default bg-[var(--bg-card)]">
                        <summary className="flex items-center gap-2 px-3 py-2 cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-tertiary hover:text-secondary">
                          <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" />
                          {t("environmentVariables")}
                        </summary>
                        <div className="px-3 pb-3 pt-1">
                          <KeyValueList
                            items={selectedSlot.env}
                            onChange={(env) => updateSlot(normalizedSelection.slotIndex, { env })}
                          />
                        </div>
                      </details>
                    </section>
                    )}

                    {editingPane && (
                    <section className="space-y-2.5 pt-3 border-t border-default">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("pane")}</p>
                      {selectedSlot.runtime === "terminal" ? (
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
                                  });
                                } else {
                                  updateSlot(normalizedSelection.slotIndex, {
                                    agent: value || undefined,
                                    command: value ? undefined : selectedSlot.command,
                                    session_id: value ? selectedSlot.session_id : undefined,
                                  });
                                }
                              }}
                              options={agentOptions}
                            />
                          </div>
                          {(selectedTerminalWindow?.agent ?? selectedSlot.agent) ? (
                            <div>
                              <FieldLabel>{t("sessionId")}</FieldLabel>
                              <SessionIdInput
                                value={selectedTerminalWindow?.session_id ?? selectedSlot.session_id ?? ""}
                                onChange={(value) => {
                                  if (selectedTerminalWindow) updateWindow(normalizedSelection.windowIndex ?? 0, { session_id: value || null });
                                  else updateSlot(normalizedSelection.slotIndex, { session_id: value || undefined });
                                }}
                                agent={selectedTerminalWindow?.agent ?? selectedSlot.agent}
                                sessions={agentSessions}
                                loading={agentSessionsLoading}
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
                              onChange={(value) => updateWindow(normalizedSelection.windowIndex ?? 0, { agent: value || null })}
                              options={agentOptions}
                            />
                          </div>
                          <div>
                            <FieldLabel>{t("sessionId")}</FieldLabel>
                            <SessionIdInput
                              value={selectedWindow.session_id ?? ""}
                              onChange={(value) => updateWindow(normalizedSelection.windowIndex ?? 0, { session_id: value || null })}
                              agent={selectedWindow.agent}
                              sessions={agentSessions}
                              loading={agentSessionsLoading}
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

                    {editingPane ? (
                    <section className="space-y-2.5 pt-3 border-t border-default">
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("scheduling")}</p>
                        <p className="mt-0.5 text-[11px] text-tertiary">{t("canvasSchedulingHint")}</p>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <button
                          type="button"
                          onClick={() => splitSelectedPane("horizontal")}
                          className="control-touch rounded-md border border-default text-[12px] text-secondary hover:text-primary hover:border-[var(--border-strong)] transition-colors"
                        >
                          {t("splitRight")}
                        </button>
                        <button
                          type="button"
                          onClick={() => splitSelectedPane("vertical")}
                          className="control-touch rounded-md border border-default text-[12px] text-secondary hover:text-primary hover:border-[var(--border-strong)] transition-colors"
                        >
                          {t("splitDown")}
                        </button>
                        <button
                          type="button"
                          onClick={duplicatePane}
                          className="control-touch rounded-md border border-default text-[12px] text-secondary hover:text-primary hover:border-[var(--border-strong)] transition-colors"
                        >
                          {t("duplicatePane")}
                        </button>
                        <button
                          type="button"
                          onClick={() => movePane(-1)}
                          disabled={!canMoveSelectedPaneUp}
                          className="control-touch rounded-md border border-default text-[12px] text-secondary hover:text-primary hover:border-[var(--border-strong)] transition-colors disabled:opacity-40"
                        >
                          {t("moveUp")}
                        </button>
                        <button
                          type="button"
                          onClick={() => movePane(1)}
                          disabled={!canMoveSelectedPaneDown}
                          className="control-touch rounded-md border border-default text-[12px] text-secondary hover:text-primary hover:border-[var(--border-strong)] transition-colors disabled:opacity-40"
                        >
                          {t("moveDown")}
                        </button>
                      </div>
                      {selectedWindow && slots.length > 1 && (
                        <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2">
                          <SelectInput
                            value={moveTarget}
                            onChange={setMoveTarget}
                            options={tabOptions}
                            ariaLabel={t("moveToTab")}
                          />
                          <button
                            type="button"
                            onClick={movePaneToTab}
                            disabled={Number(moveTarget) === normalizedSelection.slotIndex || slots[Number(moveTarget)]?.runtime !== selectedSlot.runtime}
                            className="control-touch px-3 rounded-md bg-[var(--accent-bg)] text-[var(--accent)] text-[12px] font-semibold border border-[var(--accent-border)] disabled:opacity-40"
                          >
                            {t("move")}
                          </button>
                        </div>
                      )}
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
