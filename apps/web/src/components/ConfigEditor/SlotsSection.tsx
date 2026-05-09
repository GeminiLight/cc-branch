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
import { useI18n } from "../../i18n";
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
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(false);
  const agentOptions = [
    { value: "", label: t("noneOption") },
    ...agents.map((a) => ({ value: a, label: a })),
  ];

  const windowName = win.name || t("unnamed");

  return (
    <div className="rounded-md border border-default bg-[var(--bg-card)]">
      <div className="flex items-center gap-1 px-2.5 py-2">
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="icon-touch sm:min-h-8 sm:min-w-8 rounded text-tertiary hover:text-primary transition-colors shrink-0 flex items-center justify-center"
          aria-label={expanded ? t("collapseWindow", { name: windowName }) : t("expandWindow", { name: windowName })}
          title={expanded ? t("collapseWindow", { name: windowName }) : t("expandWindow", { name: windowName })}
        >
          <ChevronDown
            className={`w-3.5 h-3.5 transition-transform ${expanded ? "" : "-rotate-90"}`}
          />
        </button>
        <Box className="w-3 h-3 text-tertiary shrink-0" />
        <span className="text-[12px] font-medium text-primary flex-1 min-w-0 truncate">
          {windowName}
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
            className="icon-touch sm:min-h-8 sm:min-w-8 rounded text-tertiary hover:text-primary transition-colors disabled:opacity-30 flex items-center justify-center"
            title={t("moveWindowUp", { name: windowName })}
            aria-label={t("moveWindowUp", { name: windowName })}
          >
            <ChevronUp className="w-3 h-3" />
          </button>
          <button
            type="button"
            onClick={onMoveDown}
            disabled={!canMoveDown}
            className="icon-touch sm:min-h-8 sm:min-w-8 rounded text-tertiary hover:text-primary transition-colors disabled:opacity-30 flex items-center justify-center"
            title={t("moveWindowDown", { name: windowName })}
            aria-label={t("moveWindowDown", { name: windowName })}
          >
            <ChevronDown className="w-3 h-3" />
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="icon-touch sm:min-h-8 sm:min-w-8 rounded text-tertiary hover:text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors flex items-center justify-center"
            title={t("removeWindow", { name: windowName })}
            aria-label={t("removeWindow", { name: windowName })}
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="px-3 pb-3 pt-1 space-y-2.5 animate-stagger">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <div>
              <FieldLabel required>{t("name")}</FieldLabel>
              <TextInput
                value={win.name}
                onChange={(v) => onChange({ name: v })}
                placeholder="main"
                invalid={!win.name.trim()}
              />
            </div>
            <div>
              <FieldLabel>{t("agent")}</FieldLabel>
              <SelectInput
                value={win.agent ?? ""}
                onChange={(v) => onChange({ agent: v || null })}
                options={agentOptions}
              />
            </div>
            <div>
              <FieldLabel>{t("sessionId")}</FieldLabel>
              <TextInput
                value={win.session_id ?? ""}
                onChange={(v) => onChange({ session_id: v || null })}
                placeholder={t("sessionIdPlaceholder")}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div>
              <FieldLabel>{t("commandOverride")}</FieldLabel>
              <TextInput
                value={win.command ?? ""}
                onChange={(v) => onChange({ command: v || null })}
                placeholder="npm run dev"
              />
            </div>
            <div>
              <FieldLabel>{t("workingDirectory")}</FieldLabel>
              <TextInput
                value={win.cwd ?? ""}
                onChange={(v) => onChange({ cwd: v || null })}
                placeholder={t("relativeToSlotCwd")}
              />
            </div>
          </div>

          <div>
            <FieldLabel>{t("environmentVariables")}</FieldLabel>
            <KeyValueList
              items={win.env}
              onChange={(env) => onChange({ env })}
            />
          </div>

          {/* Agent behaviour overrides */}
          <details className="group">
            <summary className="flex items-center gap-1 text-[11px] text-tertiary cursor-pointer select-none hover:text-secondary transition-colors">
              <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" />
              {t("agentBehaviorOverrides")}
            </summary>
            <div className="pt-2 space-y-2.5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <div>
                  <FieldLabel>{t("label")}</FieldLabel>
                  <TextInput
                    value={win.label ?? ""}
                    onChange={(v) => onChange({ label: v || null })}
                    placeholder={t("overrideLabel")}
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <div>
                  <FieldLabel>{t("resumeTemplateOverride")}</FieldLabel>
                  <TextInput
                    value={win.resume_template ?? ""}
                    onChange={(v) => onChange({ resume_template: v || null })}
                    placeholder="-r {session_id}"
                  />
                </div>
                <div>
                  <FieldLabel>{t("createTemplateOverride")}</FieldLabel>
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
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(true);
  const isTerminal = slot.runtime === "terminal";
  const agentOptions = [
    { value: "", label: t("noneOption") },
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

  const slotName = slot.name || t("unnamed");

  return (
    <div className="rounded-md border border-default bg-[var(--bg-card)] shadow-sm">
      <div className="flex items-center gap-1 px-3 py-2">
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="icon-touch sm:min-h-8 sm:min-w-8 rounded text-tertiary hover:text-primary transition-colors shrink-0 flex items-center justify-center"
          aria-label={expanded ? t("collapseSlot", { name: slotName }) : t("expandSlot", { name: slotName })}
          title={expanded ? t("collapseSlot", { name: slotName }) : t("expandSlot", { name: slotName })}
        >
          <ChevronDown
            className={`w-3.5 h-3.5 transition-transform ${expanded ? "" : "-rotate-90"}`}
          />
        </button>
        <Layers className="w-3.5 h-3.5 text-tertiary shrink-0" />
        <div className="flex-1 min-w-0">
          <span className="text-[13px] font-semibold text-primary">
            {slotName}
          </span>
          <span className="ml-2 text-[10px] text-tertiary uppercase tracking-wide">
            {slot.runtime}
          </span>
          {!isTerminal && (
            <span className="ml-2 text-[10px] text-tertiary">
              {t("windowCount", { count: slot.windows.length })}
            </span>
          )}
        </div>
        <div className="flex items-center gap-0.5 shrink-0">
          <button
            type="button"
            onClick={onMoveUp}
            disabled={index === 0}
            className="icon-touch sm:min-h-8 sm:min-w-8 rounded text-tertiary hover:text-primary transition-colors disabled:opacity-30 flex items-center justify-center"
            title={t("moveSlotUp", { name: slotName })}
            aria-label={t("moveSlotUp", { name: slotName })}
          >
            <ChevronUp className="w-3 h-3" />
          </button>
          <button
            type="button"
            onClick={onMoveDown}
            disabled={index === total - 1}
            className="icon-touch sm:min-h-8 sm:min-w-8 rounded text-tertiary hover:text-primary transition-colors disabled:opacity-30 flex items-center justify-center"
            title={t("moveSlotDown", { name: slotName })}
            aria-label={t("moveSlotDown", { name: slotName })}
          >
            <ChevronDown className="w-3 h-3" />
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="icon-touch sm:min-h-8 sm:min-w-8 rounded text-tertiary hover:text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors flex items-center justify-center"
            title={t("removeSlotNamed", { name: slotName })}
            aria-label={t("removeSlotNamed", { name: slotName })}
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="px-3 pb-3 pt-1 space-y-3 animate-stagger">
          {/* Slot basics */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <div>
              <FieldLabel required>{t("name")}</FieldLabel>
              <TextInput
                value={slot.name}
                onChange={(v) => onChange({ name: v })}
                placeholder="dev"
                invalid={!slot.name.trim()}
              />
            </div>
            <div>
              <FieldLabel>{t("runtime")}</FieldLabel>
              <SelectInput
                value={slot.runtime}
                onChange={(v) => onChange({ runtime: v as "tmux" | "terminal" })}
                options={[
                  { value: "tmux", label: "Tmux" },
                  { value: "terminal", label: t("openTerminal") },
                ]}
              />
            </div>
            <div>
              <FieldLabel>{t("workingDirectory")}</FieldLabel>
              <TextInput
                value={slot.cwd}
                onChange={(v) => onChange({ cwd: v })}
                placeholder="."
              />
            </div>
          </div>

          <div>
            <FieldLabel>{t("environmentVariables")}</FieldLabel>
            <KeyValueList
              items={slot.env}
              onChange={(env) => onChange({ env })}
            />
          </div>

          {/* Terminal runtime fields */}
          {isTerminal && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 p-3 rounded-md bg-[var(--accent-bg)]/40">
              <div>
                <FieldLabel>{t("command")}</FieldLabel>
                <TextInput
                  value={slot.command ?? ""}
                  onChange={(v) => onChange({ command: v || undefined })}
                  placeholder="zsh"
                />
              </div>
              <div>
                <FieldLabel>{t("title")}</FieldLabel>
                <TextInput
                  value={slot.title ?? ""}
                  onChange={(v) => onChange({ title: v || undefined })}
                  placeholder="main"
                />
              </div>
              <div>
                <FieldLabel>{t("agent")}</FieldLabel>
                <SelectInput
                  value={slot.agent ?? ""}
                  onChange={(v) => onChange({ agent: v || undefined })}
                  options={agentOptions}
                />
              </div>
              <div>
                <FieldLabel>{t("sessionId")}</FieldLabel>
                <TextInput
                  value={slot.session_id ?? ""}
                  onChange={(v) => onChange({ session_id: v || undefined })}
                  placeholder="uuid"
                />
              </div>
            </div>
          )}

          {/* Tmux windows */}
          {!isTerminal && (
            <div className="space-y-2">
              <p className="text-[11px] font-semibold text-secondary uppercase tracking-wide">
                {t("windows")}
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
              <AddButton onClick={addWindow}>{t("addWindow")}</AddButton>
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
  const { t } = useI18n();

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
        runtime: "tmux",
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
    (s) => s.runtime === "tmux" && s.windows.some((w) => !w.name.trim())
  );

  return (
    <section className="rounded-md transition-colors">
      <div className={`px-4 py-3 flex items-center justify-between rounded-md transition-colors ${
        expanded ? "bg-[var(--bg-hover)]/45" : "hover:surface-hover"
      }`}>
        <button
          type="button"
          onClick={onToggle}
          className="flex items-center gap-2 text-left group flex-1 control-touch"
          aria-label={expanded ? t("collapseSlotsSection") : t("expandSlotsSection")}
        >
          <ChevronDown
            className={`w-3.5 h-3.5 text-tertiary shrink-0 transition-transform ${
              expanded ? "" : "-rotate-90"
            }`}
          />
          <Layers className="w-3.5 h-3.5 text-tertiary" />
          <div className="min-w-0">
            <span className="text-[13px] font-semibold text-primary">{t("slotsTitle")}</span>
            <span className="text-[11px] text-tertiary ml-2">
              {slots.length}
            </span>
          </div>
        </button>
        <button
          type="button"
          onClick={addSlot}
          className="control-touch px-3 rounded-md text-[12px] font-medium bg-[var(--accent)] text-[var(--text-on-accent)] hover:bg-[var(--accent-light)] transition-colors flex items-center gap-1.5 shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          {t("add")}
        </button>
      </div>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 animate-stagger">
          {dupNames.length > 0 && (
            <InlineError message={t("duplicateSlotNames", { names: [...new Set(dupNames)].join(", ") })} />
          )}
          {emptyNames.length > 0 && (
            <InlineError message={t("allSlotsMustHaveName")} />
          )}
          {emptyWindows.length > 0 && (
            <InlineError message={t("allWindowsMustHaveName")} />
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
              <p className="text-[12px] text-secondary">{t("noSlotsYet")}</p>
              <p className="text-[11px] text-tertiary mt-0.5">
                {t("addSlotHint")}
              </p>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
