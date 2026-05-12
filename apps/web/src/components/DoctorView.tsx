import { useMemo, memo } from "react";
import { AlertTriangle, CheckCircle2, RefreshCw, Stethoscope, XCircle } from "lucide-react";
import { useI18n } from "../i18n";
import { useDoctor } from "../hooks";
import type { DoctorReportPayload } from "../types";
import EmptyState from "./ui/EmptyState";

interface DoctorViewProps {
  projectPath?: string;
  configPath?: string;
}

interface CheckItem {
  status: "ok" | "error" | "warn";
  icon: string;
  text: string;
  fix?: string;
}

function parseReport(report: string): { overall: "ok" | "error" | "warn"; checks: CheckItem[] } {
  const lines = report.split("\n");
  const checks: CheckItem[] = [];
  let overall: "ok" | "error" | "warn" = "ok";
  let category = "";

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;

    if (line.endsWith(":") && !line.includes("✓") && !line.includes("✗") && !line.includes("⚠")) {
      category = line.replace(":", "").trim();
      continue;
    }

    let status: "ok" | "error" | "warn";
    let text: string;
    let fix: string | undefined;

    if (line.startsWith("✓")) {
      status = "ok";
      text = line.substring(1).trim();
    } else if (line.startsWith("✗")) {
      status = "error";
      text = line.substring(1).trim();
      overall = overall === "ok" ? "error" : overall;
    } else if (line.startsWith("⚠")) {
      status = "warn";
      text = line.substring(1).trim();
      overall = overall === "ok" ? "warn" : overall;
    } else if (line.startsWith("→")) {
      fix = line.substring(1).trim();
      if (checks.length > 0) checks[checks.length - 1].fix = fix;
      continue;
    } else continue;

    const iconMatch = text.match(/^([\w\s-]+):\s*(.+)$/);
    const icon = iconMatch ? iconMatch[1].trim() : category;
    const displayText = iconMatch ? iconMatch[2].trim() : text;
    checks.push({ status, icon, text: displayText });
  }

  return { overall, checks };
}

function reportText(data: { report: string | DoctorReportPayload; text?: string } | undefined): string {
  if (!data) return "";
  if (typeof data.report === "string") return data.report;
  return data.text ?? "";
}

function countLabel(
  t: (key: string, vars?: Record<string, string | number>) => string,
  key: string,
  count: number,
): string {
  return t(count === 1 ? key : `${key}_plural`, { count });
}

const StatusDot = memo(function StatusDot({ status }: { status: "ok" | "error" | "warn" }) {
  if (status === "ok")
    return <CheckCircle2 className="w-4 h-4 text-[var(--success)] shrink-0 mt-0.5" />;
  if (status === "error")
    return <XCircle className="w-4 h-4 text-[var(--danger)] shrink-0 mt-0.5" />;
  return <AlertTriangle className="w-4 h-4 text-[var(--warning)] shrink-0 mt-0.5" />;
});

export default function DoctorView({ projectPath, configPath }: DoctorViewProps) {
  const { t } = useI18n();
  const { data, error, isLoading, refetch, isFetching } = useDoctor({ projectPath, configPath });

  const parsed = useMemo(() => {
    const text = reportText(data);
    return text ? parseReport(text) : null;
  }, [data]);

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

  const checks = parsed?.checks ?? [];
  const issueCount = checks.filter((check) => check.status === "error").length;
  const warningCount = checks.filter((check) => check.status === "warn").length;
  const passedCount = checks.filter((check) => check.status === "ok").length;
  const overall = parsed?.overall ?? "ok";
  const overallLabel =
    overall === "ok"
      ? t("checksPassed")
      : overall === "warn"
      ? t("checksWarnings")
      : t("checksIssues");
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

  const summaryText =
    issueCount > 0
      ? t("checksActionNeeded")
      : warningCount > 0
      ? t("checksWarningsOnly")
      : t("checksAllClear");

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

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <div className="rounded-md bg-[var(--bg-hover)]/45 px-3 py-2 flex items-center gap-2">
            <XCircle className="w-4 h-4 text-[var(--danger)] shrink-0" />
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("checksIssues")}</p>
              <p className="text-[13px] font-semibold text-primary">{countLabel(t, "issueCount", issueCount)}</p>
            </div>
          </div>
          <div className="rounded-md bg-[var(--bg-hover)]/45 px-3 py-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-[var(--warning)] shrink-0" />
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("checksWarnings")}</p>
              <p className="text-[13px] font-semibold text-primary">{countLabel(t, "warningCount", warningCount)}</p>
            </div>
          </div>
          <div className="rounded-md bg-[var(--bg-hover)]/45 px-3 py-2 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-[var(--success)] shrink-0" />
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("checksPassed")}</p>
              <p className="text-[13px] font-semibold text-primary">{t("passedCount", { count: passedCount })}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Checks */}
      <div className="surface-card border border-default rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-subtle bg-[var(--bg-card)] flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <StatusDot status={overall} />
            <p className="text-[13px] font-semibold text-primary">{t("doctorChecks")}</p>
          </div>
          <span className={`text-[11px] font-semibold ${overallColor}`}>{overallLabel}</span>
        </div>
        <div className="p-1.5 space-y-1">
        {checks.map((check, i) => (
          <div
            key={i}
            className={`rounded-md px-3 py-3 flex items-start gap-2.5 ${
              check.status === "error"
                ? "bg-[var(--danger-bg)]"
                : check.status === "warn"
                  ? "bg-[var(--warning-bg)]"
              : "hover:bg-[var(--bg-hover)]/35"
            }`}
          >
            <StatusDot status={check.status} />
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-semibold text-tertiary uppercase tracking-wide">{check.icon}</p>
              <p className="text-[13px] text-primary mt-px">{check.text}</p>
              {check.fix && (
                <p className="text-[11px] text-tertiary mt-1 font-mono bg-[var(--bg-hover)] px-2 py-1 rounded inline-block">
                  → {check.fix}
                </p>
              )}
            </div>
          </div>
        ))}
        </div>
      </div>
    </div>
  );
}
