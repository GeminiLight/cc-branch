/**
 * ConfigEditor — reusable form primitives.
 */

import { useState, useCallback, type KeyboardEvent, type ReactNode } from "react";
import {
  Trash2,
  Plus,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
} from "lucide-react";
import { useI18n } from "../../i18n";
import Dropdown from "../ui/Dropdown";

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
  ariaLabel,
  onBlur,
  onKeyDown,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
  invalid?: boolean;
  ariaLabel?: string;
  onBlur?: () => void;
  onKeyDown?: (e: KeyboardEvent<HTMLInputElement>) => void;
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
      onKeyDown={onKeyDown}
      placeholder={placeholder}
      disabled={disabled}
      aria-label={ariaLabel}
      aria-invalid={invalid}
      className={`w-full control-touch px-3 rounded-lg border text-[13px] bg-[var(--bg-card)] placeholder:text-muted transition-all focus:outline-none focus:ring-2 focus:ring-[var(--accent-border)] focus:border-[var(--accent)] ${
        invalid
          ? "border-[var(--danger)] focus:ring-[var(--danger)]/20 focus:border-[var(--danger)]"
          : "border-default hover:border-[var(--border-strong)]"
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
  ariaLabel,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  ariaLabel?: string;
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
      aria-label={ariaLabel}
      className="w-20 control-touch px-3 rounded-lg border border-default text-[13px] bg-[var(--bg-card)] transition-all focus:outline-none focus:ring-2 focus:ring-[var(--accent-border)] focus:border-[var(--accent)] hover:border-[var(--border-strong)]"
    />
  );
}

/* ── Select ── */
export function SelectInput({
  value,
  onChange,
  options,
  ariaLabel,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string; disabled?: boolean }[];
  ariaLabel?: string;
}) {
  const selected = options.find((o) => o.value === value);
  return (
    <Dropdown
      align="left"
      value={value}
      onChange={onChange}
      ariaLabel={ariaLabel}
      className="w-full block"
      triggerClassName="w-full block"
      items={options.map((option) => ({
        label: option.label,
        value: option.value,
        disabled: option.disabled,
      }))}
      trigger={
        <span
          className="w-full control-touch px-3 rounded-lg border border-default text-[13px] bg-[var(--bg-card)] transition-all hover:border-[var(--border-strong)] focus-within:ring-2 focus-within:ring-[var(--accent-border)] focus-within:border-[var(--accent)] flex items-center justify-between gap-2 text-left"
          aria-label={ariaLabel}
        >
          <span className={selected ? "truncate text-primary" : "truncate text-muted"}>
            {selected?.label || ariaLabel || "Select"}
          </span>
          <ChevronsUpDown className="w-3.5 h-3.5 text-tertiary shrink-0" />
        </span>
      }
    />
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
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-10 shrink-0 cursor-pointer rounded-full transition-colors ${
        checked ? "bg-[var(--accent)]" : "bg-[var(--border-strong)]"
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
          checked ? "translate-x-5" : "translate-x-0.5"
        }`}
        style={{ marginTop: 4 }}
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
      className={`w-full flex items-center gap-3 px-4 py-3 text-left group rounded-md transition-colors ${
        expanded ? "bg-[var(--bg-hover)]/45" : "hover:bg-[var(--bg-hover)]/35"
      }`}
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
          <span className="text-[11px] text-tertiary ml-2 truncate">{subtitle}</span>
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
    <div className="px-4 pt-2 pb-4 animate-stagger">
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
  const { t } = useI18n();
  return (
    <div
      className={`border rounded-md transition-colors surface-card ${
        error ? "border-[var(--danger)]" : "border-default"
      }`}
    >
      <div className="flex items-center gap-1 px-2 py-1.5 border-b border-default bg-[var(--bg-hover)]/40">
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="shrink-0 icon-touch sm:min-h-8 sm:min-w-8 rounded text-tertiary hover:text-primary transition-colors flex items-center justify-center"
          aria-label={expanded ? t("collapse") : t("expand")}
          title={expanded ? t("collapse") : t("expand")}
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
              className="icon-touch sm:min-h-8 sm:min-w-8 rounded text-tertiary hover:text-primary hover:surface-hover transition-colors disabled:opacity-30 flex items-center justify-center"
              title={t("moveUp")}
              aria-label={t("moveUp")}
            >
              <ChevronUp className="w-3 h-3" />
            </button>
          )}
          {onMoveDown && (
            <button
              type="button"
              onClick={onMoveDown}
              disabled={!canMoveDown}
              className="icon-touch sm:min-h-8 sm:min-w-8 rounded text-tertiary hover:text-primary hover:surface-hover transition-colors disabled:opacity-30 flex items-center justify-center"
              title={t("moveDown")}
              aria-label={t("moveDown")}
            >
              <ChevronDown className="w-3 h-3" />
            </button>
          )}
          {onDelete && (
            <button
              type="button"
              onClick={onDelete}
              className="icon-touch sm:min-h-8 sm:min-w-8 rounded text-tertiary hover:text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors flex items-center justify-center"
              title={t("remove")}
              aria-label={t("remove")}
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
      className="w-full flex items-center justify-center gap-1.5 control-touch rounded-md border border-dashed border-default text-[12px] font-medium text-secondary hover:text-primary hover:border-[var(--accent)] hover:bg-[var(--accent-bg)] transition-colors"
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
  keyLabel,
  valueLabel,
}: {
  items: Record<string, string>;
  onChange: (items: Record<string, string>) => void;
  keyLabel?: string;
  valueLabel?: string;
}) {
  const { t } = useI18n();
  const entries = Object.entries(items);
  const keyPlaceholder = keyLabel ?? t("key");
  const valuePlaceholder = valueLabel ?? t("value");
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
          <TextInput value={k} onChange={(nv) => update(i, nv, v)} placeholder={keyPlaceholder} />
          <span className="text-tertiary text-[11px]">=</span>
          <TextInput value={v} onChange={(nv) => update(i, k, nv)} placeholder={valuePlaceholder} />
          <button
            type="button"
            onClick={() => remove(i)}
            className="icon-touch sm:min-h-8 sm:min-w-8 rounded text-tertiary hover:text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors shrink-0 flex items-center justify-center"
            aria-label={t("removeEnvironmentVariable", { key: k || keyPlaceholder })}
            title={t("removeEnvironmentVariable", { key: k || keyPlaceholder })}
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      ))}
      <AddButton onClick={add}>{t("add")}</AddButton>
    </div>
  );
}
