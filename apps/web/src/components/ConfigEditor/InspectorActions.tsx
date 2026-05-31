import type { ReactNode } from "react";
import { ArrowDown, ArrowUp, Copy, MoveRight, Plus } from "lucide-react";
import { useI18n } from "../../i18n";

type SelectOption = { value: string; label: string };

function ActionButton({
  children,
  onClick,
  disabled = false,
  className = "",
}: {
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`min-h-8 rounded-md border border-default bg-[var(--bg-card)] px-2 text-left text-[11px] font-medium text-secondary hover:text-primary hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] transition-colors disabled:opacity-35 disabled:hover:bg-[var(--bg-card)] ${className}`}
    >
      {children}
    </button>
  );
}

function ActionLabel({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      {icon}
      {children}
    </span>
  );
}

export function TmuxGroupPositionActions({
  canMoveUp,
  canMoveDown,
  onMoveUp,
  onMoveDown,
}: {
  canMoveUp: boolean;
  canMoveDown: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
}) {
  const { t } = useI18n();
  return (
    <section className="space-y-3 pt-3 border-t border-default">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("groupPosition")}</p>
        <span className="text-[10px] text-tertiary">{t("tmuxWindowStack")}</span>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        <ActionButton onClick={onMoveUp} disabled={!canMoveUp}>
          <ActionLabel icon={<ArrowUp className="h-3.5 w-3.5 text-tertiary" />}>{t("moveUp")}</ActionLabel>
        </ActionButton>
        <ActionButton onClick={onMoveDown} disabled={!canMoveDown}>
          <ActionLabel icon={<ArrowDown className="h-3.5 w-3.5 text-tertiary" />}>{t("moveDown")}</ActionLabel>
        </ActionButton>
      </div>
    </section>
  );
}

export function PaneSchedulingActions({
  canMoveUp,
  canMoveDown,
  onSplitRight,
  onSplitDown,
  onDuplicate,
  onMoveUp,
  onMoveDown,
}: {
  canMoveUp: boolean;
  canMoveDown: boolean;
  onSplitRight: () => void;
  onSplitDown: () => void;
  onDuplicate: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
}) {
  const { t } = useI18n();
  return (
    <section className="space-y-3 pt-3 border-t border-default">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("scheduling")}</p>
        <span className="text-[10px] text-tertiary">{t("pane")}</span>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        <ActionButton onClick={onSplitRight}>
          <ActionLabel icon={<Plus className="h-3.5 w-3.5 text-tertiary" />}>{t("splitRight")}</ActionLabel>
        </ActionButton>
        <ActionButton onClick={onSplitDown}>
          <ActionLabel icon={<Plus className="h-3.5 w-3.5 text-tertiary" />}>{t("splitDown")}</ActionLabel>
        </ActionButton>
        <ActionButton onClick={onDuplicate} className="col-span-2">
          <ActionLabel icon={<Copy className="h-3.5 w-3.5 text-tertiary" />}>{t("duplicatePane")}</ActionLabel>
        </ActionButton>
        <ActionButton onClick={onMoveUp} disabled={!canMoveUp}>
          <ActionLabel icon={<ArrowUp className="h-3.5 w-3.5 text-tertiary" />}>{t("moveUp")}</ActionLabel>
        </ActionButton>
        <ActionButton onClick={onMoveDown} disabled={!canMoveDown}>
          <ActionLabel icon={<ArrowDown className="h-3.5 w-3.5 text-tertiary" />}>{t("moveDown")}</ActionLabel>
        </ActionButton>
      </div>
    </section>
  );
}

export function MoveToTabActions({
  options,
  onMoveTo,
}: {
  options: SelectOption[];
  onMoveTo: (value: string) => void;
}) {
  const { t } = useI18n();
  return (
    <section className="space-y-3 pt-3 border-t border-default">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("moveToTab")}</p>
        <MoveRight className="h-3.5 w-3.5 text-tertiary" />
      </div>
      {options.length > 0 ? (
        <div className="grid gap-1.5">
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onMoveTo(option.value)}
              className="min-h-9 rounded-md border border-default bg-[var(--bg-card)] px-2.5 text-left text-[12px] font-medium text-secondary hover:border-[var(--accent-border)] hover:bg-[var(--accent-bg)] hover:text-primary transition-colors flex items-center justify-between gap-2"
            >
              <span className="min-w-0 truncate">{option.label}</span>
              <MoveRight className="h-3.5 w-3.5 shrink-0 text-tertiary" />
            </button>
          ))}
        </div>
      ) : (
        <div className="rounded-md border border-dashed border-default bg-[var(--bg-hover)]/35 px-3 py-2 text-[11px] text-tertiary">
          {t("noCompatibleTabs")}
        </div>
      )}
    </section>
  );
}
