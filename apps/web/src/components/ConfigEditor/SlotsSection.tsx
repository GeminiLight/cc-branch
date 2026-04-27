/**
 * ConfigEditor — Slots & Windows management section.
 */

import { useState } from "react";
import {
  Layers,
  Plus,
  Trash2,
  ChevronDown,
  ChevronUp,
  Terminal,
  Box,
} from "lucide-react";
import type { SlotConfig, WindowConfig } from "./types";
import {
  FieldLabel,
  TextInput,
  SelectInput,
  KeyValueList,
  AddButton,
  InlineError,
} from "./FormPrimitives";

/* ── Window Card ── */
function WindowCard({
  win,
  agents,
  onChange,
  onDelete,
  canMoveUp,
  canMoveDown,
  onMoveUp,
  onMoveDown,
}: {
  win: WindowConfig;
  agents: string[];
  onChange: (patch: Partial<WindowConfig>) => void;
  onDelete: () => void;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const agentOptions = [
    { value: "", label: "— None —" },
    ...agents.map((a) => ({ value: a, label: a })),
  ];

  return (
    <div className="border border-default rounded-md bg-[var(--bg-page)]">
      <div className="flex items-center gap-1 px-2 py-1.5">
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="p-0.5 rounded text-tertiary hover:text-primary transition-colors shrink-0"
        >
          <ChevronDown
            className={`w-3.5 h-3.5 transition-transform ${expanded ? "" : "-rotate-90"}`}
          />
        </button>
        <Box className="w-3 h-3 text-tertiary shrink-0" />
        <span className="text-[12px] font-medium text-primary flex-1 min-w-0 truncate">
          {win.name || "(unnamed)"}
        </span>
        {win.agent && (
          <span className="text-[10px] text-[var(--accent)] bg-[var(--accent-bg)] px-1.5 py-0.5 rounded shrink-0">
            {win.agent}
          </span>
        )}
        <div className="flex items-center gap-0.5 shrink-0">
          <button
            type="button"
            onClick={onMoveUp}
            disabled={!canMoveUp}
            className="p-0.5 rounded text-tertiary hover:text-primary transition-colors disabled:opacity-30"
          >
            <ChevronUp className="w-3 h-3" />
          </button>
          <button
            type="button"
            onClick={onMoveDown}
            disabled={!canMoveDown}
            className="p-0.5 rounded text-tertiary hover:text-primary transition-colors disabled:opacity-30"
          >
            <ChevronDown className="w-3 h-3" />
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="p-0.5 rounded text-tertiary hover:text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="px-3 pb-3 pt-1 space-y-2.5 border-t border-default animate-stagger">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div>
              <FieldLabel required>Name</FieldLabel>
              <TextInput
                value={win.name}
                onChange={(v) => onChange({ name: v })}
                placeholder="main"
                invalid={!win.name.trim()}
              />
            </div>
            <div>
              <FieldLabel>Agent</FieldLabel>
              <SelectInput
                value={win.agent ?? ""}
                onChange={(v) => onChange({ agent: v || null })}
                options={agentOptions}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div>
              <FieldLabel>Command override</FieldLabel>
              <TextInput
                value={win.command ?? ""}
                onChange={(v) => onChange({ command: v || null })}
                placeholder="npm run dev"
              />
            </div>
            <div>
              <FieldLabel>Working directory</FieldLabel>
              <TextInput
                value={win.cwd ?? ""}
                onChange={(v) => onChange({ cwd: v || null })}
                placeholder="relative to slot cwd"
              />
            </div>
          </div>

          <div>
            <FieldLabel>Environment variables</FieldLabel>
            <KeyValueList
              items={win.env}
              onChange={(env) => onChange({ env })}
            />
          </div>

          {/* Advanced toggles */}
          <details className="group">
            <summary className="flex items-center gap-1 text-[11px] text-tertiary cursor-pointer select-none hover:text-secondary transition-colors">
              <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" />
              Advanced overrides
            </summary>
            <div className="pt-2 space-y-2.5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <div>
                  <FieldLabel>Session ID</FieldLabel>
                  <TextInput
                    value={win.session_id ?? ""}
                    onChange={(v) => onChange({ session_id: v || null })}
                    placeholder="uuid or leave empty"
                  />
                </div>
                <div>
                  <FieldLabel>Label</FieldLabel>
                  <TextInput
                    value={win.label ?? ""}
                    onChange={(v) => onChange({ label: v || null })}
                    placeholder="override label"
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <div>
                  <FieldLabel>Resume template override</FieldLabel>
                  <TextInput
                    value={win.resume_template ?? ""}
                    onChange={(v) => onChange({ resume_template: v || null })}
                    placeholder="-r {session_id}"
                  />
                </div>
                <div>
                  <FieldLabel>Create template override</FieldLabel>
                  <TextInput
                    value={win.create_template ?? ""}
                    onChange={(v) => onChange({ create_template: v || null })}
                    placeholder="command --session-id {session_id}"
                  />
                </div>
              </div>
            </div>
          </details>
        </div>
      )}
    </div>
  );
}

/* ── Slot Card ── */
function SlotCard({
  slot,
  index,
  total,
  agents,
  onChange,
  onDelete,
  onMoveUp,
  onMoveDown,
}: {
  slot: SlotConfig;
  index: number;
  total: number;
  agents: string[];
  onChange: (patch: Partial<SlotConfig>) => void;
  onDelete: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const isShell = slot.backend === "shell";
  const agentOptions = [
    { value: "", label: "— None —" },
    ...agents.map((a) => ({ value: a, label: a })),
  ];

  function addWindow() {
    onChange({
      windows: [
        ...slot.windows,
        {
          name: `window-${slot.windows.length + 1}`,
          agent: null,
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
        },
      ],
    });
  }

  function updateWindow(i: number, patch: Partial<WindowConfig>) {
    const next = [...slot.windows];
    next[i] = { ...next[i], ...patch };
    onChange({ windows: next });
  }

  function deleteWindow(i: number) {
    const next = [...slot.windows];
    next.splice(i, 1);
    onChange({ windows: next });
  }

  function moveWindow(i: number, dir: number) {
    const next = [...slot.windows];
    const [moved] = next.splice(i, 1);
    next.splice(i + dir, 0, moved);
    onChange({ windows: next });
  }

  return (
    <div className="border border-default rounded-lg surface-card">
      <div className="flex items-center gap-1 px-2.5 py-2 border-b border-default bg-[var(--bg-hover)]/30">
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="p-0.5 rounded text-tertiary hover:text-primary transition-colors shrink-0"
        >
          <ChevronDown
            className={`w-3.5 h-3.5 transition-transform ${expanded ? "" : "-rotate-90"}`}
          />
        </button>
        <Layers className="w-3.5 h-3.5 text-tertiary shrink-0" />
        <div className="flex-1 min-w-0">
          <span className="text-[13px] font-semibold text-primary">
            {slot.name || "(unnamed)"}
          </span>
          <span className="ml-2 text-[10px] text-tertiary uppercase tracking-wide">
            {slot.backend}
          </span>
          {!isShell && (
            <span className="ml-2 text-[10px] text-tertiary">
              {slot.windows.length} window{slot.windows.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        <div className="flex items-center gap-0.5 shrink-0">
          <button
            type="button"
            onClick={onMoveUp}
            disabled={index === 0}
            className="p-1 rounded text-tertiary hover:text-primary transition-colors disabled:opacity-30"
            title="Move up"
          >
            <ChevronUp className="w-3 h-3" />
          </button>
          <button
            type="button"
            onClick={onMoveDown}
            disabled={index === total - 1}
            className="p-1 rounded text-tertiary hover:text-primary transition-colors disabled:opacity-30"
            title="Move down"
          >
            <ChevronDown className="w-3 h-3" />
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="p-1 rounded text-tertiary hover:text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors"
            title="Remove slot"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="p-3 space-y-3 animate-stagger">
          {/* Slot basics */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <div>
              <FieldLabel required>Name</FieldLabel>
              <TextInput
                value={slot.name}
                onChange={(v) => onChange({ name: v })}
                placeholder="dev"
                invalid={!slot.name.trim()}
              />
            </div>
            <div>
              <FieldLabel>Backend</FieldLabel>
              <SelectInput
                value={slot.backend}
                onChange={(v) => onChange({ backend: v as "tmux" | "shell" })}
                options={[
                  { value: "tmux", label: "Tmux" },
                  { value: "shell", label: "Shell" },
                ]}
              />
            </div>
            <div>
              <FieldLabel>Working directory</FieldLabel>
              <TextInput
                value={slot.cwd}
                onChange={(v) => onChange({ cwd: v })}
                placeholder="."
              />
            </div>
          </div>

          <div>
            <FieldLabel>Environment variables</FieldLabel>
            <KeyValueList
              items={slot.env}
              onChange={(env) => onChange({ env })}
            />
          </div>

          {/* Shell slot fields */}
          {isShell && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 p-2.5 rounded-md bg-[var(--accent-bg)]/50 border border-[var(--accent-border)]">
              <div>
                <FieldLabel>Command</FieldLabel>
                <TextInput
                  value={slot.command ?? ""}
                  onChange={(v) => onChange({ command: v || undefined })}
                  placeholder="zsh"
                />
              </div>
              <div>
                <FieldLabel>Window name</FieldLabel>
                <TextInput
                  value={slot.window_name ?? ""}
                  onChange={(v) => onChange({ window_name: v || undefined })}
                  placeholder="main"
                />
              </div>
              <div>
                <FieldLabel>Agent</FieldLabel>
                <SelectInput
                  value={slot.agent ?? ""}
                  onChange={(v) => onChange({ agent: v || undefined })}
                  options={agentOptions}
                />
              </div>
              <div>
                <FieldLabel>Session ID</FieldLabel>
                <TextInput
                  value={slot.session_id ?? ""}
                  onChange={(v) => onChange({ session_id: v || undefined })}
                  placeholder="uuid"
                />
              </div>
            </div>
          )}

          {/* Tmux windows */}
          {!isShell && (
            <div className="space-y-2">
              <p className="text-[11px] font-semibold text-secondary uppercase tracking-wide">
                Windows
              </p>
              {slot.windows.map((win, i) => (
                <WindowCard
                  key={`${slot.name}-${i}`}
                  win={win}
                  agents={agents}
                  onChange={(p) => updateWindow(i, p)}
                  onDelete={() => deleteWindow(i)}
                  canMoveUp={i > 0}
                  canMoveDown={i < slot.windows.length - 1}
                  onMoveUp={() => moveWindow(i, -1)}
                  onMoveDown={() => moveWindow(i, 1)}
                />
              ))}
              <AddButton onClick={addWindow}>Add window</AddButton>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Slots Section ── */
export default function SlotsSection({
  slots,
  agents,
  onChange,
  expanded,
  onToggle,
}: {
  slots: SlotConfig[];
  agents: string[];
  onChange: (slots: SlotConfig[]) => void;
  expanded: boolean;
  onToggle: () => void;
}) {
  function addSlot() {
    const names = new Set(slots.map((s) => s.name));
    let name = "new-slot";
    let i = 1;
    while (names.has(name)) {
      name = `new-slot-${i}`;
      i++;
    }
    onChange([
      ...slots,
      {
        name,
        backend: "tmux",
        cwd: ".",
        env: {},
        windows: [
          {
            name: "main",
            agent: agents[0] ?? null,
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
          },
        ],
      },
    ]);
  }

  function updateSlot(index: number, patch: Partial<SlotConfig>) {
    const next = [...slots];
    next[index] = { ...next[index], ...patch };
    onChange(next);
  }

  function deleteSlot(index: number) {
    const next = [...slots];
    next.splice(index, 1);
    onChange(next);
  }

  function moveSlot(index: number, dir: number) {
    const next = [...slots];
    const [moved] = next.splice(index, 1);
    next.splice(index + dir, 0, moved);
    onChange(next);
  }

  // Validation
  const dupNames = slots
    .map((s) => s.name)
    .filter((name, i, arr) => arr.indexOf(name) !== i);
  const emptyNames = slots.filter((s) => !s.name.trim());
  const emptyWindows = slots.filter(
    (s) => s.backend === "tmux" && s.windows.some((w) => !w.name.trim())
  );

  return (
    <div className="border border-default rounded-lg surface-card">
      <div className="px-3 py-2.5 border-b border-default flex items-center justify-between">
        <button
          type="button"
          onClick={onToggle}
          className="flex items-center gap-2 text-left group flex-1"
        >
          <ChevronDown
            className={`w-3.5 h-3.5 text-tertiary shrink-0 transition-transform ${
              expanded ? "" : "-rotate-90"
            }`}
          />
          <Layers className="w-3.5 h-3.5 text-tertiary" />
          <div className="min-w-0">
            <span className="text-[13px] font-semibold text-primary">Slots</span>
            <span className="text-[11px] text-tertiary ml-2">
              {slots.length} slot{slots.length !== 1 ? "s" : ""}
            </span>
          </div>
        </button>
        <button
          type="button"
          onClick={addSlot}
          className="h-7 px-2 rounded text-[11px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity flex items-center gap-1 shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          Add
        </button>
      </div>

      {expanded && (
        <div className="p-3 space-y-3 animate-stagger">
          {dupNames.length > 0 && (
            <InlineError message={`Duplicate slot names: ${[...new Set(dupNames)].join(", ")}`} />
          )}
          {emptyNames.length > 0 && (
            <InlineError message="All slots must have a name" />
          )}
          {emptyWindows.length > 0 && (
            <InlineError message="All windows must have a name" />
          )}

          {slots.map((slot, i) => (
            <SlotCard
              key={`${slot.name}-${i}`}
              slot={slot}
              index={i}
              total={slots.length}
              agents={agents}
              onChange={(p) => updateSlot(i, p)}
              onDelete={() => deleteSlot(i)}
              onMoveUp={() => moveSlot(i, -1)}
              onMoveDown={() => moveSlot(i, 1)}
            />
          ))}

          {slots.length === 0 && (
            <div className="text-center py-6 border border-dashed border-default rounded-md">
              <Terminal className="w-5 h-5 text-tertiary mx-auto mb-1.5" />
              <p className="text-[12px] text-secondary">No slots yet</p>
              <p className="text-[11px] text-tertiary mt-0.5">
                Add a slot to define workspace containers
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
