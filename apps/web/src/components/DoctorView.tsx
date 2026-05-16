import { useMemo, memo } from "react";
import { AlertTriangle, CheckCircle2, RefreshCw, Stethoscope, XCircle } from "lucide-react";
import { useI18n } from "../i18n";
import { useConfig, useDoctor, useWorkspace, useWorkspaceAction } from "../hooks";
import type { DoctorStatus } from "./doctor-view-model";
import type { CheckItem } from "./doctor-view-model";
import { buildDoctorViewModel } from "./doctor-view-model";
import EmptyState from "./ui/EmptyState";
import { useToast } from "./ui/Toast";
import { PageSummaryCard, PageSummaryMetric } from "./ui/PageSummary";

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

function FindingRow({
  check,
  compact = false,
  actionLabel,
  actionPending = false,
  onAction,
}: {
  check: CheckItem;
  compact?: boolean;
  actionLabel?: string;
  actionPending?: boolean;
  onAction?: () => void;
}) {
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
      {check.action && actionLabel && onAction && !compact && (
        <button
          type="button"
          onClick={onAction}
          disabled={actionPending}
          className="control-touch shrink-0 rounded-md border border-default bg-[var(--bg-card)] px-2.5 text-[12px] font-semibold text-secondary hover:text-primary hover:border-[var(--accent-border)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

export default function DoctorView({ projectPath, configPath }: DoctorViewProps) {
  const { t } = useI18n();
  const scope = { projectPath, configPath };
  const { data, error, isLoading, refetch, isFetching } = useDoctor(scope);
  const { data: configData } = useConfig(scope);
  const { data: workspaceData } = useWorkspace(scope, false);
  const actionMutation = useWorkspaceAction();
  const toast = useToast();

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
  const runFindingAction = async (check: CheckItem) => {
    if (!projectPath || check.action !== "prune_state") return;
    try {
      await actionMutation.mutateAsync({
        action: "prune_state",
        target: undefined,
        opener: undefined,
        intent: undefined,
        projectPath,
        ...(configPath ? { configPath } : {}),
      });
      const count = check.actionCount || 0;
      toast.success(count === 1 ? t("staleStateClearedOne", { count }) : t("staleStateCleared", { count }));
      refetch();
    } catch (e: unknown) {
      toast.error(String(e));
    }
  };

  return (
    <div className="page-shell space-y-4">
      {/* Summary */}
      <PageSummaryCard
        icon={<Stethoscope className="w-4 h-4" />}
        title={t("healthCheck")}
        badge={
          <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold ${overallBadgeClass}`}>
            {overallLabel}
          </span>
        }
        description={summaryText}
        actions={
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
        }
        metrics={hasActionableFindings ? (
          <>
            <PageSummaryMetric
              icon={<XCircle className="w-4 h-4" />}
              label={t("checksIssues")}
              value={issueCountLabel}
              tone={issueCount > 0 ? "danger" : "neutral"}
            />
            <PageSummaryMetric
              icon={<AlertTriangle className="w-4 h-4" />}
              label={t("checksWarnings")}
              value={warningCountLabel}
              tone={warningCount > 0 ? "warning" : "neutral"}
            />
            <PageSummaryMetric
              icon={<CheckCircle2 className="w-4 h-4" />}
              label={t("checksPassed")}
              value={passedCountLabel}
              tone={passedCount > 0 ? "success" : "neutral"}
            />
          </>
        ) : undefined}
      />

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
            actionableChecks.map((check, i) => (
              <FindingRow
                key={`${check.status}-${check.icon}-${i}`}
                check={check}
                actionLabel={check.action === "prune_state" ? t("clearStaleState") : undefined}
                actionPending={actionMutation.isPending}
                onAction={() => void runFindingAction(check)}
              />
            ))
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
