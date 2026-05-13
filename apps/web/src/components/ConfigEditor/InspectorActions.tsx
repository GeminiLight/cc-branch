import type { ReactNode } from "react";
import { ArrowDown, ArrowUp, Copy, MoveRight, Plus, Trash2 } from "lucide-react";
import { useI18n } from "../../i18n";
import { SelectInput } from "./FormPrimitives";

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
      className={`min-h-10 rounded-md border border-default bg-[var(--bg-card)] px-2 text-left text-[12px] text-secondary hover:text-primary hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] transition-colors disabled:opacity-35 disabled:hover:bg-[var(--bg-card)] ${className}`}
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
  onDelete,
}: {
  canMoveUp: boolean;
  canMoveDown: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onDelete: () => void;
}) {
  const { t } = useI18n();
  return (
    <section className="space-y-3 pt-3 border-t border-default">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("groupPosition")}</p>
        <p className="mt-0.5 text-[11px] text-tertiary">{t("groupPositionHint")}</p>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        <ActionButton onClick={onMoveUp} disabled={!canMoveUp}>
          <ActionLabel icon={<ArrowUp className="h-3.5 w-3.5 text-tertiary" />}>{t("moveUp")}</ActionLabel>
        </ActionButton>
        <ActionButton onClick={onMoveDown} disabled={!canMoveDown}>
          <ActionLabel icon={<ArrowDown className="h-3.5 w-3.5 text-tertiary" />}>{t("moveDown")}</ActionLabel>
        </ActionButton>
      </div>
      <button
        type="button"
        onClick={onDelete}
        className="w-full control-touch rounded-md border border-[var(--danger)]/20 text-[12px] text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors flex items-center justify-center gap-1.5"
      >
        <Trash2 className="w-3.5 h-3.5" />
        {t("removeGroup")}
      </button>
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
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("scheduling")}</p>
        <p className="mt-0.5 text-[11px] text-tertiary">{t("canvasSchedulingHint")}</p>
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
  value,
  onChange,
  onMove,
  canMove,
}: {
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  onMove: () => void;
  canMove: boolean;
}) {
  const { t } = useI18n();
  return (
    <section className="space-y-3 pt-3 border-t border-default">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("moveToTab")}</p>
        <p className="mt-0.5 text-[11px] text-tertiary">{t("moveToTabHint")}</p>
      </div>
      {options.length > 0 ? (
        <div className="space-y-2">
          <SelectInput
            value={value}
            onChange={onChange}
            options={options}
            ariaLabel={t("moveToTab")}
          />
          <button
            type="button"
            onClick={onMove}
            disabled={!canMove}
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
  );
}

export function RemovePaneAction({ onDelete }: { onDelete: () => void }) {
  const { t } = useI18n();
  return (
    <section className="space-y-2.5 pt-3 border-t border-default">
      <button
        type="button"
        onClick={onDelete}
        className="w-full control-touch rounded-md border border-[var(--danger)]/20 text-[12px] text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors flex items-center justify-center gap-1.5"
      >
        <Trash2 className="w-3.5 h-3.5" />
        {t("removePane")}
      </button>
    </section>
  );
}
