import { useMemo, memo } from "react";
import { AlertTriangle, CheckCircle2, RefreshCw, Stethoscope, XCircle } from "lucide-react";
import { useI18n } from "../i18n";
import { useConfig, useDoctor, useWorkspace } from "../hooks";
import type { DoctorStatus } from "./doctor-view-model";
import type { CheckItem } from "./doctor-view-model";
import { buildDoctorViewModel } from "./doctor-view-model";
import EmptyState from "./ui/EmptyState";

interface DoctorViewProps {
  projectPath?: string;
  configPath?: string;
}

const StatusDot = memo(function StatusDot({ status }: { status: DoctorStatus }) {
  if (status === "ok")
    return <CheckCircle2 className="w-4 h-4 text-[var(--success)] shrink-0 mt-0.5" />;
  if (status === "error")
    return <XCircle className="w-4 h-4 text-[var(--danger)] shrink-0 mt-0.5" />;
  return <AlertTriangle className="w-4 h-4 text-[var(--warning)] shrink-0 mt-0.5" />;
});

const METRIC_STYLES = {
  issue: {
    icon: "text-[var(--danger)]",
    active: "bg-[var(--danger-bg)]",
  },
  warning: {
    icon: "text-[var(--warning)]",
    active: "bg-[var(--warning-bg)]",
  },
  passed: {
    icon: "text-[var(--success)]",
    active: "success-bg",
  },
};

function metricCardClass(active: boolean, activeClass: string): string {
  return `rounded-md px-3 py-2 flex items-center gap-2 ${active ? activeClass : "bg-[var(--bg-hover)]/35"}`;
}

function metricIconClass(active: boolean, activeClass: string): string {
  return `w-4 h-4 shrink-0 ${active ? activeClass : "text-tertiary"}`;
}

function FindingRow({ check, compact = false }: { check: CheckItem; compact?: boolean }) {
  return (
    <div
      className={`rounded-md flex items-start gap-2.5 ${
        compact
          ? "px-2.5 py-2"
          : `px-3 py-3 ${
              check.status === "error"
                ? "bg-[var(--danger-bg)]"
                : check.status === "warn"
                  ? "bg-[var(--warning-bg)]"
                  : "hover:bg-[var(--bg-hover)]/35"
            }`
      }`}
    >
      <StatusDot status={check.status} />
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-semibold text-tertiary uppercase tracking-wide">{check.icon}</p>
        <p className={`${compact ? "text-[12px]" : "text-[13px]"} text-primary mt-px`}>{check.text}</p>
        {check.fix && (
          <p className="text-[11px] text-tertiary mt-1 font-mono bg-[var(--bg-hover)] px-2 py-1 rounded inline-block">
            → {check.fix}
          </p>
        )}
      </div>
    </div>
  );
}

export default function DoctorView({ projectPath, configPath }: DoctorViewProps) {
  const { t } = useI18n();
  const scope = { projectPath, configPath };
  const { data, error, isLoading, refetch, isFetching } = useDoctor(scope);
  const { data: configData } = useConfig(scope);
  const { data: workspaceData } = useWorkspace(scope, false);

  const model = useMemo(
    () => buildDoctorViewModel({ data, configIssues: configData?.issues, workspaceData, t }),
    [configData?.issues, data, t, workspaceData],
  );

  if (isLoading) {
    return (
      <div className="space-y-3 page-shell animate-stagger">
        <div className="surface-card border border-default rounded-lg px-4 py-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-[var(--border-subtle)] animate-skeleton" />
          <div className="space-y-1.5 flex-1">
            <div className="w-24 h-3 bg-[var(--border-subtle)] rounded animate-skeleton" />
            <div className="w-16 h-2.5 bg-[var(--border-subtle)] rounded animate-skeleton" />
          </div>
        </div>
        <div className="surface-card border border-default rounded-lg p-1.5 space-y-1">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="rounded-md px-3 py-2.5 flex items-start gap-2.5">
              <div className="w-3.5 h-3.5 rounded-full bg-[var(--border-subtle)] animate-skeleton mt-0.5 shrink-0" />
              <div className="flex-1 space-y-1.5">
                <div className="w-20 h-2.5 bg-[var(--border-subtle)] rounded animate-skeleton" />
                <div className="w-full h-3 bg-[var(--border-subtle)] rounded animate-skeleton" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <EmptyState
        variant="error"
        title={t("errorLoading")}
        description={String(error)}
        action={
          <button
            type="button"
            onClick={() => refetch()}
            className="h-9 px-4 rounded-lg text-[13px] font-semibold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity flex items-center gap-2 shadow-sm"
          >
            <RefreshCw className="w-4 h-4" />
            {t("refresh")}
          </button>
        }
      />
    );
  }

  const {
    issueCount,
    warningCount,
    passedCount,
    issueCountLabel,
    warningCountLabel,
    passedCountLabel,
    actionableChecks,
    passingChecks,
    overall,
    overallLabel,
    summaryText,
  } = model;
  const overallColor =
    overall === "ok"
      ? "text-[var(--success)]"
      : overall === "warn"
      ? "text-[var(--warning)]"
      : "text-[var(--danger)]";
  const overallBadgeClass =
    overall === "ok"
      ? "success-bg success"
      : overall === "warn"
      ? "bg-[var(--warning-bg)] text-[var(--warning)]"
      : "danger-bg danger";
  const hasActionableFindings = issueCount > 0 || warningCount > 0;

  return (
    <div className="page-shell space-y-4">
      {/* Summary */}
      <div className="surface-command border border-default rounded-lg px-4 sm:px-5 py-4 flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-md bg-[var(--accent-bg)] border border-[var(--accent-border)] flex items-center justify-center shrink-0">
              <Stethoscope className="w-4 h-4 text-[var(--accent)]" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-[16px] font-semibold text-primary leading-tight">{t("healthCheck")}</h2>
                <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold ${overallBadgeClass}`}>
                  {overallLabel}
                </span>
              </div>
              <p className="text-[12px] text-secondary mt-1">{summaryText}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="control-touch px-3 rounded-md text-[12px] font-medium text-secondary hover:text-primary surface-card border border-default hover:border-[var(--border-strong)] transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
            aria-label={t("refresh")}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin" : ""}`} />
            {t("refresh")}
          </button>
        </div>

        {hasActionableFindings && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <div className={metricCardClass(issueCount > 0, METRIC_STYLES.issue.active)}>
              <XCircle className={metricIconClass(issueCount > 0, METRIC_STYLES.issue.icon)} />
              <div className="min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("checksIssues")}</p>
                <p className="text-[13px] font-semibold text-primary">{issueCountLabel}</p>
              </div>
            </div>
            <div className={metricCardClass(warningCount > 0, METRIC_STYLES.warning.active)}>
              <AlertTriangle className={metricIconClass(warningCount > 0, METRIC_STYLES.warning.icon)} />
              <div className="min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("checksWarnings")}</p>
                <p className="text-[13px] font-semibold text-primary">{warningCountLabel}</p>
              </div>
            </div>
            <div className={metricCardClass(passedCount > 0, METRIC_STYLES.passed.active)}>
              <CheckCircle2 className={metricIconClass(passedCount > 0, METRIC_STYLES.passed.icon)} />
              <div className="min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("checksPassed")}</p>
                <p className="text-[13px] font-semibold text-primary">{passedCountLabel}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Checks */}
      <div className="surface-card border border-default rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-subtle bg-[var(--bg-card)] flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <StatusDot status={overall} />
            <p className="text-[13px] font-semibold text-primary">
              {hasActionableFindings ? t("doctorFindings") : t("doctorChecks")}
            </p>
          </div>
          {hasActionableFindings && (
            <span className={`text-[11px] font-semibold ${overallColor}`}>{overallLabel}</span>
          )}
        </div>
        <div className="p-1.5 space-y-1.5">
          {actionableChecks.length > 0 ? (
            actionableChecks.map((check, i) => <FindingRow key={`${check.status}-${check.icon}-${i}`} check={check} />)
          ) : passingChecks.length === 0 ? (
            <div className="rounded-md px-3 py-3 flex items-start gap-2.5 success-bg">
              <CheckCircle2 className="w-4 h-4 text-[var(--success)] shrink-0 mt-0.5" />
              <div className="min-w-0">
                <p className="text-[13px] font-semibold text-primary">{t("doctorReadyFinding")}</p>
                <p className="text-[12px] text-secondary mt-0.5">{summaryText}</p>
              </div>
            </div>
          ) : null}

          {passingChecks.length > 0 && (
            <details className="group rounded-md border border-subtle bg-[var(--bg-hover)]/25">
              <summary className="flex cursor-pointer items-center justify-between gap-3 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-tertiary hover:text-secondary">
                <span className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[var(--success)]" />
                  {passedCountLabel}
                </span>
                <span className="text-[10px] font-medium normal-case tracking-normal">{t("showDetails")}</span>
              </summary>
              <div className="border-t border-subtle p-1 space-y-1">
                {passingChecks.map((check, i) => (
                  <FindingRow key={`passed-${check.icon}-${i}`} check={check} compact />
                ))}
              </div>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}
