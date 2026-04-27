import { useMemo, memo } from "react";
import { AlertTriangle, CheckCircle2, RefreshCw, Stethoscope, XCircle } from "lucide-react";
import { useI18n } from "../i18n";
import { useDoctor } from "../hooks";

interface DoctorViewProps {
  projectPath?: string;
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

const StatusDot = memo(function StatusDot({ status }: { status: "ok" | "error" | "warn" }) {
  if (status === "ok")
    return <CheckCircle2 className="w-3.5 h-3.5 text-[var(--success)] shrink-0 mt-0.5" />;
  if (status === "error")
    return <XCircle className="w-3.5 h-3.5 text-[var(--danger)] shrink-0 mt-0.5" />;
  return <AlertTriangle className="w-3.5 h-3.5 text-[var(--warning)] shrink-0 mt-0.5" />;
});

export default function DoctorView({ projectPath }: DoctorViewProps) {
  const { t } = useI18n();
  const { data, error, isLoading, refetch, isFetching } = useDoctor(projectPath);

  const parsed = useMemo(() => (data?.report ? parseReport(data.report) : null), [data]);

  if (isLoading) {
    return (
      <div className="space-y-3 max-w-3xl animate-stagger">
        <div className="surface-card border border-default rounded-lg px-4 py-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-[var(--border-subtle)] animate-skeleton" />
          <div className="space-y-1.5 flex-1">
            <div className="w-24 h-3 bg-[var(--border-subtle)] rounded animate-skeleton" />
            <div className="w-16 h-2.5 bg-[var(--border-subtle)] rounded animate-skeleton" />
          </div>
        </div>
        <div className="surface-card border border-default rounded-lg divide-y divide-default">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="px-4 py-2.5 flex items-start gap-2.5">
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
      <div className="max-w-sm mx-auto text-center py-20">
        <p className="text-[13px] text-secondary">{String(error)}</p>
      </div>
    );
  }

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

  return (
    <div className="space-y-3 max-w-3xl">
      {/* Summary */}
      <div className={`surface-card border ${overallBorder} rounded-lg px-4 py-3 flex items-center gap-3 ${overallBg}`}>
        <div className="w-8 h-8 rounded-md flex items-center justify-center bg-[var(--accent-bg)]">
          <Stethoscope className="w-4 h-4 text-[var(--accent)]" />
        </div>
        <div className="flex-1">
          <h2 className="text-[13px] font-semibold text-primary">{t("healthCheck")}</h2>
          <p className={`text-[11px] font-medium mt-px ${overallColor}`}>{overallLabel}</p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="h-7 px-2 rounded text-[11px] font-medium text-secondary hover:text-primary surface-hover transition-colors flex items-center gap-1.5 disabled:opacity-50"
          aria-label={t("refresh")}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin" : ""}`} />
          {t("refresh")}
        </button>
        <StatusDot status={overall} />
      </div>

      {/* Checks */}
      <div className="surface-card border border-default rounded-lg divide-y divide-default">
        {parsed?.checks.map((check, i) => (
          <div key={i} className="px-4 py-2.5 flex items-start gap-2.5">
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
