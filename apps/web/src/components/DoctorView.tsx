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
  const overallBg =
    overall === "ok"
      ? "bg-[var(--success-bg)]"
      : overall === "warn"
      ? "bg-[var(--warning-bg)]"
      : "bg-[var(--danger-bg)]";
  const overallBorder =
    overall === "ok"
      ? "border-[var(--success)]/10"
      : overall === "warn"
      ? "border-[var(--warning)]/10"
      : "border-[var(--danger)]/10";

  const summaryText =
    issueCount > 0
      ? t("checksActionNeeded")
      : warningCount > 0
      ? t("checksWarningsOnly")
      : t("checksAllClear");

  return (
    <div className="space-y-3 page-shell">
      {/* Summary */}
      <div className={`surface-card border ${overallBorder} rounded-lg px-4 py-4 flex flex-col sm:flex-row sm:items-center gap-3 ${overallBg}`}>
        <div className="w-10 h-10 rounded-md flex items-center justify-center bg-[var(--accent-bg)] shrink-0">
          <Stethoscope className="w-5 h-5 text-[var(--accent)]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-[15px] font-semibold text-primary">{t("healthCheck")}</h2>
            <span className={`text-[12px] font-semibold ${overallColor}`}>{overallLabel}</span>
          </div>
          <p className="text-[12px] text-secondary mt-0.5">{summaryText}</p>
          <div className="flex flex-wrap items-center gap-1.5 mt-2">
            <span className="rounded-md danger-bg px-2 py-1 text-[11px] font-semibold text-[var(--danger)]">
              {countLabel(t, "issueCount", issueCount)}
            </span>
            <span className="rounded-md warning-bg px-2 py-1 text-[11px] font-semibold text-[var(--warning)]">
              {countLabel(t, "warningCount", warningCount)}
            </span>
            <span className="rounded-md success-bg px-2 py-1 text-[11px] font-semibold text-[var(--success)]">
              {t("passedCount", { count: passedCount })}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 sm:self-start">
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="control-touch px-3 rounded-md text-[12px] font-medium text-secondary hover:text-primary surface-hover transition-colors flex items-center gap-1.5 disabled:opacity-50"
            aria-label={t("refresh")}
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
            {t("refresh")}
          </button>
          <StatusDot status={overall} />
        </div>
      </div>

      {/* Checks */}
      <div className="surface-card border border-default rounded-lg p-1.5 space-y-1">
        {checks.map((check, i) => (
          <div
            key={i}
            className={`rounded-md px-3 py-3 flex items-start gap-2.5 ${
              check.status === "error"
                ? "bg-[var(--danger-bg)]"
                : check.status === "warn"
                  ? "bg-[var(--warning-bg)]"
                  : "hover:surface-hover"
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
  );
}
