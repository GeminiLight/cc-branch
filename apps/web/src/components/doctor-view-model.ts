import type { ConfigIssue, DoctorReport, DoctorReportPayload, WorkspaceStatus } from "../types";
import { visibleConfigIssues } from "../utils/configIssues";

export type DoctorStatus = "ok" | "error" | "warn";

export interface CheckItem {
  status: DoctorStatus;
  icon: string;
  text: string;
  fix?: string;
}

type Translate = (key: string, vars?: Record<string, string | number>) => string;

interface BuildDoctorViewModelInput {
  data: DoctorReport | undefined;
  configIssues: ConfigIssue[] | undefined | null;
  workspaceData: WorkspaceStatus | undefined;
  t: Translate;
}

export interface DoctorViewModel {
  checks: CheckItem[];
  visibleChecks: CheckItem[];
  actionableChecks: CheckItem[];
  passingChecks: CheckItem[];
  issueCount: number;
  warningCount: number;
  passedCount: number;
  issueCountLabel: string;
  warningCountLabel: string;
  passedCountLabel: string;
  overall: DoctorStatus;
  overallLabel: string;
  summaryText: string;
}

export const CHECK_STATUS_PRIORITY: Record<CheckItem["status"], number> = {
  error: 0,
  warn: 1,
  ok: 2,
};

export function parseReport(report: string): { overall: DoctorStatus; checks: CheckItem[] } {
  const lines = report.split("\n");
  const checks: CheckItem[] = [];
  let overall: DoctorStatus = "ok";
  let category = "";

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;

    if (line.endsWith(":") && !line.includes("✓") && !line.includes("✗") && !line.includes("⚠")) {
      category = line.replace(":", "").trim();
      continue;
    }

    let status: DoctorStatus;
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
      if (checks.length > 0 && checks[checks.length - 1].status !== "ok") checks[checks.length - 1].fix = fix;
      continue;
    } else continue;

    const iconMatch = text.match(/^([\w\s-]+):\s*(.+)$/);
    const icon = iconMatch ? iconMatch[1].trim() : category;
    const displayText = iconMatch ? iconMatch[2].trim() : text;
    checks.push({ status, icon, text: displayText });
  }

  return { overall, checks };
}

function reportText(data: DoctorReport | undefined): string {
  if (!data) return "";
  if (typeof data.report !== "string") return "";
  if (typeof data.report === "string") return data.report;
  return data.text ?? "";
}

function structuredIssueIcon(issue: ConfigIssue, t: Translate): string {
  if (issue.issue_type === "orphaned_state") return t("runtimeState");
  return issue.target || issue.issue_type;
}

function structuredReportChecks(data: DoctorReport | undefined, t: Translate): CheckItem[] {
  if (!data || typeof data.report === "string") return [];
  return (data.report as DoctorReportPayload).issues.map((issue) => ({
    status: issue.severity === "error" ? "error" : issue.severity === "warning" ? "warn" : "ok",
    icon: structuredIssueIcon(issue, t),
    text: issue.message,
    fix:
      issue.severity !== "info" && typeof issue.context?.hint === "string"
        ? issue.context.hint
        : undefined,
  }));
}

function reportIncludesIssue(data: DoctorReport | undefined, issueType: string): boolean {
  if (!data || typeof data.report === "string") return false;
  return (data.report as DoctorReportPayload).issues.some((issue) => issue.issue_type === issueType);
}

function countLabel(t: Translate, key: string, count: number): string {
  return t(count === 1 ? key : `${key}_plural`, { count });
}

function actionableRuntimeDrift(workspaceData: WorkspaceStatus | undefined): {
  changed: number;
  missing: number;
  untracked: number;
  extra: number;
  orphaned: number;
} {
  const summary = workspaceData?.runtime_sync?.summary;
  return {
    changed: summary?.changed || 0,
    missing: summary?.missing || 0,
    untracked: summary?.untracked || 0,
    extra: summary?.extra || 0,
    orphaned: Math.max(summary?.orphaned || 0, workspaceData?.runtime_sync?.orphaned_state?.length || 0),
  };
}

function productChecks(
  configIssues: ConfigIssue[] | undefined | null,
  workspaceData: WorkspaceStatus | undefined,
  t: Translate,
  options: { omitOrphanedState?: boolean } = {},
): CheckItem[] {
  const checks: CheckItem[] = [];
  for (const issue of visibleConfigIssues(configIssues)) {
    checks.push({
      status: issue.severity === "error" ? "error" : issue.severity === "warning" ? "warn" : "ok",
      icon: t("configuration"),
      text: issue.message,
    });
  }

  if (workspaceData?.status === "invalid_config") {
    checks.push({
      status: "error",
      icon: t("workspaceProfileShort"),
      text: workspaceData.error || t("errorLoading"),
    });
  }

  const { changed, missing, untracked, extra, orphaned } = actionableRuntimeDrift(workspaceData);
  if (changed > 0) checks.push({ status: "warn", icon: t("runtimeState"), text: t("runtimeChangedPending", { count: changed }) });
  if (missing > 0) checks.push({ status: "warn", icon: t("runtimeState"), text: t("runtimeMissingPending", { count: missing }) });
  if (untracked > 0) checks.push({ status: "warn", icon: t("runtimeState"), text: t("runtimeUntracked", { count: untracked }) });
  if (extra > 0) checks.push({ status: "warn", icon: t("runtimeState"), text: t("runtimeExtraPanes", { count: extra }) });
  if (orphaned > 0 && !options.omitOrphanedState) checks.push({ status: "warn", icon: t("runtimeState"), text: t("runtimeOrphanedState", { count: orphaned }) });
  return checks;
}

function dedupeChecks(checks: CheckItem[]): CheckItem[] {
  const seen = new Set<string>();
  const result: CheckItem[] = [];
  for (const check of checks) {
    const key = `${check.status}:${check.icon}:${check.text}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(check);
  }
  return result;
}

export function buildDoctorViewModel({
  data,
  configIssues,
  workspaceData,
  t,
}: BuildDoctorViewModelInput): DoctorViewModel {
  const text = reportText(data);
  const parsed = text ? parseReport(text) : null;
  const checks = dedupeChecks([
    ...(parsed?.checks ?? []),
    ...structuredReportChecks(data, t),
    ...productChecks(configIssues, workspaceData, t, { omitOrphanedState: reportIncludesIssue(data, "orphaned_state") }),
  ]);
  const issueCount = checks.filter((check) => check.status === "error").length;
  const warningCount = checks.filter((check) => check.status === "warn").length;
  const passedCount = checks.filter((check) => check.status === "ok").length;
  const visibleChecks = [...checks].sort((a, b) => CHECK_STATUS_PRIORITY[a.status] - CHECK_STATUS_PRIORITY[b.status]);
  const actionableChecks = visibleChecks.filter((check) => check.status !== "ok");
  const passingChecks = visibleChecks.filter((check) => check.status === "ok");
  const overall = issueCount > 0 ? "error" : warningCount > 0 ? "warn" : parsed?.overall ?? "ok";
  const overallLabel =
    overall === "ok"
      ? t("checksPassed")
      : overall === "warn"
      ? t("checksWarnings")
      : t("checksIssues");
  const summaryText =
    issueCount > 0
      ? t("checksActionNeeded")
      : warningCount > 0
      ? t("checksWarningsOnly")
      : t("checksAllClear");

  return {
    checks,
    visibleChecks,
    actionableChecks,
    passingChecks,
    issueCount,
    warningCount,
    passedCount,
    issueCountLabel: countLabel(t, "issueCount", issueCount),
    warningCountLabel: countLabel(t, "warningCount", warningCount),
    passedCountLabel: t("passedCount", { count: passedCount }),
    overall,
    overallLabel,
    summaryText,
  };
}
