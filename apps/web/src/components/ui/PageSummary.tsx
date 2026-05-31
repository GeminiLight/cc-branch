import type { ReactNode } from "react";

type SummaryTone = "neutral" | "accent" | "success" | "warning" | "danger";

const metricToneClasses: Record<SummaryTone, string> = {
  neutral: "bg-[var(--bg-hover)]/45 text-tertiary",
  accent: "bg-[var(--accent-bg)] text-[var(--accent)]",
  success: "success-bg text-[var(--success)]",
  warning: "bg-[var(--warning-bg)] text-[var(--warning)]",
  danger: "bg-[var(--danger-bg)] text-[var(--danger)]",
};

export function PageSummaryMetric({
  icon,
  label,
  value,
  tone = "neutral",
}: {
  icon: ReactNode;
  label: ReactNode;
  value: ReactNode;
  tone?: SummaryTone;
}) {
  return (
    <div className={`rounded-md px-3 py-2 flex items-center gap-2 min-w-0 ${metricToneClasses[tone]}`}>
      <span className="w-4 h-4 shrink-0 flex items-center justify-center">
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{label}</p>
        <div className="mt-0.5 text-[13px] font-semibold text-primary min-w-0">{value}</div>
      </div>
    </div>
  );
}

export function PageSummaryCard({
  icon,
  title,
  badge,
  description,
  meta,
  actions,
  metrics,
  children,
  className = "",
}: {
  icon: ReactNode;
  title: ReactNode;
  badge?: ReactNode;
  description?: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
  metrics?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`surface-command border border-default rounded-lg px-4 sm:px-5 py-4 flex flex-col gap-3 ${className}`}>
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div className="w-10 h-10 rounded-md bg-[var(--accent-bg)] border border-[var(--accent-border)] flex items-center justify-center shrink-0 text-[var(--accent)]">
            {icon}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 min-w-0">
              <h2 className="text-[16px] font-semibold text-primary leading-tight truncate">
                {title}
              </h2>
              {badge}
            </div>
            {description && <p className="text-[12px] text-secondary mt-1">{description}</p>}
            {meta && <div className="mt-1 text-[11px] text-tertiary min-w-0">{meta}</div>}
          </div>
        </div>
        {actions && (
          <div className="w-full xl:w-auto xl:min-w-[500px] flex flex-col items-stretch sm:items-end gap-2">
            {actions}
          </div>
        )}
      </div>
      {metrics && (
        <div className="grid grid-cols-1 sm:grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-2">
          {metrics}
        </div>
      )}
      {children}
    </div>
  );
}
