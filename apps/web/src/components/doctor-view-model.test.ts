import { describe, expect, it } from "vitest";
import type { ConfigIssue, DoctorReport, WorkspaceStatus } from "../types";
import { buildDoctorViewModel, parseReport } from "./doctor-view-model";

function t(key: string, vars?: Record<string, string | number>): string {
  const messages: Record<string, string> = {
    configuration: "Configuration",
    workspaceProfileShort: "Workspace",
    errorLoading: "Failed to load",
    runtime: "Runtime",
    runtimeChangedPending: "{count} changed",
    runtimeMissingPending: "{count} missing",
    runtimeUntracked: "{count} untracked",
    runtimeExtraPanes: "{count} extra",
    checksPassed: "All checks passed",
    checksWarnings: "Warnings found",
    checksIssues: "Issues found",
    checksActionNeeded: "Action needed",
    checksWarningsOnly: "Warnings only",
    checksAllClear: "All clear",
    issueCount: "{count} issue",
    issueCount_plural: "{count} issues",
    warningCount: "{count} warning",
    warningCount_plural: "{count} warnings",
    passedCount: "{count} passed",
  };
  return (messages[key] ?? key).replace(/\{(\w+)\}/g, (_, name) => String(vars?.[name] ?? ""));
}

describe("doctor-view-model", () => {
  it("parses text reports and attaches fix lines to the previous check", () => {
    const parsed = parseReport(["Workspace:", "✓ config: found", "✗ tmux: missing", "→ install tmux"].join("\n"));

    expect(parsed.overall).toBe("error");
    expect(parsed.checks).toEqual([
      { status: "ok", icon: "config", text: "found" },
      { status: "error", icon: "tmux", text: "missing", fix: "install tmux" },
    ]);
  });

  it("does not attach text-report remediation hints to passing checks", () => {
    const parsed = parseReport(["doctor: demo", "✓ tmux ok", "→ Check your configuration"].join("\n"));

    expect(parsed.checks).toEqual([{ status: "ok", icon: "", text: "tmux ok" }]);
  });

  it("lets configuration issues and runtime drift drive the overall diagnosis", () => {
    const data: DoctorReport = {
      report: "Workspace:\n✓ config: found\n",
    };
    const configIssues: ConfigIssue[] = [
      {
        issue_type: "invalid_enum",
        severity: "error",
        message: "Invalid opener",
        target: "config",
        context: {},
        fixable: false,
      },
    ];
    const workspaceData = {
      config_path: "/tmp/demo/.cc-branch/config.yaml",
      state_path: "/tmp/demo/.cc-branch/state.yaml",
      slots: [],
      runtime_sync: {
        summary: {
          changed: 0,
          current: 0,
          external: 0,
          extra: 1,
          missing: 2,
          orphaned: 0,
          untracked: 0,
        },
        slots: [],
        orphaned_state: [],
        historical_sessions: [],
      },
    } satisfies WorkspaceStatus;

    const model = buildDoctorViewModel({ data, configIssues, workspaceData, t });

    expect(model.overall).toBe("error");
    expect(model.issueCount).toBe(1);
    expect(model.warningCount).toBe(2);
    expect(model.visibleChecks.map((check) => check.status)).toEqual(["error", "warn", "warn", "ok"]);
    expect(model.visibleChecks.map((check) => check.text)).toContain("2 missing");
    expect(model.visibleChecks.map((check) => check.text)).toContain("1 extra");
  });

  it("keeps stale canonical-field warnings out while preserving real config issues", () => {
    const configIssues: ConfigIssue[] = [
      {
        issue_type: "unknown_field",
        severity: "warning",
        message: "Unknown field 'openWith'",
        target: "config",
        context: { field: "openWith" },
        fixable: false,
      },
      {
        issue_type: "unknown_field",
        severity: "warning",
        message: "Unknown field 'openWith'",
        target: "pane:frontend",
        context: { field: "openWith" },
        fixable: false,
      },
    ];

    const model = buildDoctorViewModel({ data: undefined, configIssues, workspaceData: undefined, t });

    expect(model.warningCount).toBe(1);
    expect(model.visibleChecks).toMatchObject([
      {
        status: "warn",
        text: "Unknown field 'openWith'",
        icon: "Configuration",
      },
    ]);
  });

  it("uses structured doctor issues when a text report is not available", () => {
    const data: DoctorReport = {
      report: {
        project: "demo",
        has_errors: true,
        issues: [
          {
            issue_type: "missing_tmux",
            severity: "error",
            message: "tmux is missing",
            target: "tmux",
            context: { hint: "brew install tmux" },
            fixable: false,
          },
        ],
      },
    };

    const model = buildDoctorViewModel({ data, configIssues: undefined, workspaceData: undefined, t });

    expect(model.overall).toBe("error");
    expect(model.issueCountLabel).toBe("1 issue");
    expect(model.visibleChecks[0]).toMatchObject({
      status: "error",
      icon: "tmux",
      text: "tmux is missing",
      fix: "brew install tmux",
    });
  });

  it("does not render remediation hints for passing structured checks", () => {
    const data: DoctorReport = {
      report: {
        project: "demo",
        issues: [
          {
            issue_type: "agent_ok",
            severity: "info",
            message: "codex: ok",
            target: "agent:codex",
            context: { hint: "Check your configuration" },
            fixable: false,
          },
        ],
      },
    };

    const model = buildDoctorViewModel({ data, configIssues: undefined, workspaceData: undefined, t });

    expect(model.visibleChecks[0]).toMatchObject({
      status: "ok",
      icon: "agent:codex",
      text: "codex: ok",
      fix: undefined,
    });
  });
});
