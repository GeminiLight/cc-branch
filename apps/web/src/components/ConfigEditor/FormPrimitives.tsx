/**
 * ConfigEditor — reusable form primitives.
 */

import { useState, useCallback, type ReactNode } from "react";
import {
  ChevronDown,
  Trash2,
  Plus,
  AlertCircle,
  ChevronUp,
} from "lucide-react";

/* ── Label + HelpText ── */
export function FieldLabel({
  children,
  required,
}: {
  children: ReactNode;
  required?: boolean;
}) {
  return (
    <label className="block text-[11px] font-semibold text-secondary uppercase tracking-wide mb-1">
      {children}
      {required && <span className="text-[var(--danger)] ml-0.5">*</span>}
    </label>
  );
}

export function HelpText({ children }: { children: ReactNode }) {
  return <p className="text-[11px] text-tertiary mt-1">{children}</p>;
}

/* ── Text Input ── */
export function TextInput({
  value,
  onChange,
  placeholder,
  disabled,
  invalid,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
  invalid?: boolean;
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      className={`w-full h-8 px-2.5 rounded-md border text-[13px] bg-[var(--bg-card)] transition-colors focus:outline-none ${
        invalid
          ? "border-[var(--danger)] focus:border-[var(--danger)]"
          : "border-default focus:border-[var(--accent)]"
      } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    />
  );
}

/* ── Number Input ── */
export function NumberInput({
  value,
  onChange,
  min,
  max,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
}) {
  return (
    <input
      type="number"
      value={value}
      onChange={(e) => {
        const n = parseInt(e.target.value, 10);
        if (!isNaN(n)) onChange(n);
      }}
      min={min}
      max={max}
      className="w-20 h-8 px-2.5 rounded-md border border-default text-[13px] bg-[var(--bg-card)] transition-colors focus:outline-none focus:border-[var(--accent)]"
    />
  );
}

/* ── Select ── */
export function SelectInput({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-8 pl-2.5 pr-7 rounded-md border border-default text-[13px] bg-[var(--bg-card)] appearance-none transition-colors focus:outline-none focus:border-[var(--accent)] cursor-pointer"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-tertiary pointer-events-none" />
    </div>
  );
}

/* ── Toggle Switch ── */
export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full transition-colors ${
        checked ? "bg-[var(--accent)]" : "bg-[var(--border-strong)]"
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
          checked ? "translate-x-4.5" : "translate-x-0.5"
        }`}
        style={{ marginTop: 3 }}
      />
      {label && <span className="sr-only">{label}</span>}
    </button>
  );
}

/* ── Section Header (collapsible) ── */
export function SectionHeader({
  title,
  subtitle,
  icon,
  expanded,
  onToggle,
  actions,
}: {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  expanded: boolean;
  onToggle: () => void;
  actions?: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="w-full flex items-center gap-2 px-3 py-2.5 text-left group"
    >
      <ChevronDown
        className={`w-3.5 h-3.5 text-tertiary shrink-0 transition-transform ${
          expanded ? "" : "-rotate-90"
        }`}
      />
      {icon && <span className="text-tertiary">{icon}</span>}
      <div className="flex-1 min-w-0">
        <span className="text-[13px] font-semibold text-primary">{title}</span>
        {subtitle && (
          <span className="text-[11px] text-tertiary ml-2">{subtitle}</span>
        )}
      </div>
      {actions}
    </button>
  );
}

/* ── Collapsible Section wrapper ── */
export function CollapsibleSection({
  expanded,
  children,
}: {
  expanded: boolean;
  children: ReactNode;
}) {
  if (!expanded) return null;
  return (
    <div className="px-3 pb-3 animate-stagger">
      {children}
    </div>
  );
}

/* ── Card with drag handle ── */
export function SortableCard({
  children,
  onDelete,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
  header,
  error,
}: {
  children: ReactNode;
  onDelete?: () => void;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  canMoveUp?: boolean;
  canMoveDown?: boolean;
  header: ReactNode;
  error?: string;
}) {
  const [expanded, setExpanded] = useState(true);
  return (
    <div
      className={`border rounded-md transition-colors ${
        error ? "border-[var(--danger)]" : "border-default"
      }`}
    >
      <div className="flex items-center gap-1 px-2 py-1.5 border-b border-default bg-[var(--bg-hover)]/50">
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="shrink-0 p-0.5 rounded text-tertiary hover:text-primary transition-colors"
        >
          <ChevronDown
            className={`w-3.5 h-3.5 transition-transform ${expanded ? "" : "-rotate-90"}`}
          />
        </button>
        <div className="flex-1 min-w-0">{header}</div>
        <div className="flex items-center gap-0.5 shrink-0">
          {onMoveUp && (
            <button
              type="button"
              onClick={onMoveUp}
              disabled={!canMoveUp}
              className="p-1 rounded text-tertiary hover:text-primary hover:surface-hover transition-colors disabled:opacity-30"
              title="Move up"
            >
              <ChevronUp className="w-3 h-3" />
            </button>
          )}
          {onMoveDown && (
            <button
              type="button"
              onClick={onMoveDown}
              disabled={!canMoveDown}
              className="p-1 rounded text-tertiary hover:text-primary hover:surface-hover transition-colors disabled:opacity-30"
              title="Move down"
            >
              <ChevronDown className="w-3 h-3" />
            </button>
          )}
          {onDelete && (
            <button
              type="button"
              onClick={onDelete}
              className="p-1 rounded text-tertiary hover:text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors"
              title="Remove"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
      {expanded && (
        <div className="p-3 space-y-3 animate-stagger">{children}</div>
      )}
    </div>
  );
}

/* ── Add button ── */
export function AddButton({
  onClick,
  children,
}: {
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-center justify-center gap-1.5 h-8 rounded-md border border-dashed border-default text-[12px] font-medium text-secondary hover:text-primary hover:border-[var(--accent)] hover:bg-[var(--accent-bg)] transition-colors"
    >
      <Plus className="w-3.5 h-3.5" />
      {children}
    </button>
  );
}

/* ── Inline error ── */
export function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-1.5 text-[11px] text-[var(--danger)]">
      <AlertCircle className="w-3 h-3 shrink-0" />
      {message}
    </div>
  );
}

/* ── Key-value list editor ── */
export function KeyValueList({
  items,
  onChange,
  keyLabel = "Key",
  valueLabel = "Value",
}: {
  items: Record<string, string>;
  onChange: (items: Record<string, string>) => void;
  keyLabel?: string;
  valueLabel?: string;
}) {
  const entries = Object.entries(items);
  const update = useCallback(
    (idx: number, key: string, val: string) => {
      const next: Record<string, string> = {};
      entries.forEach(([k, v], i) => {
        if (i === idx) {
          if (key.trim()) next[key] = val;
        } else {
          next[k] = v;
        }
      });
      onChange(next);
    },
    [entries, onChange]
  );

  const remove = useCallback(
    (idx: number) => {
      const next: Record<string, string> = {};
      entries.forEach(([k, v], i) => {
        if (i !== idx) next[k] = v;
      });
      onChange(next);
    },
    [entries, onChange]
  );

  const add = useCallback(() => {
    onChange({ ...items, "": "" });
  }, [items, onChange]);

  return (
    <div className="space-y-1.5">
      {entries.map(([k, v], i) => (
        <div key={`${k}-${i}`} className="flex items-center gap-1.5">
          <TextInput value={k} onChange={(nv) => update(i, nv, v)} placeholder={keyLabel} />
          <span className="text-tertiary text-[11px]">=</span>
          <TextInput value={v} onChange={(nv) => update(i, k, nv)} placeholder={valueLabel} />
          <button
            type="button"
            onClick={() => remove(i)}
            className="p-1 rounded text-tertiary hover:text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors shrink-0"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      ))}
      <AddButton onClick={add}>Add</AddButton>
    </div>
  );
}
