import { describe, expect, it } from "vitest";
import type { RuntimeSyncReport, SlotInfo, WorkspaceStatus } from "../types";
import {
  actionableRuntimeDriftCount,
  buildDashboardRuntimeSummary,
  groupedSlotDisplayName,
  isActionableSyncStatus,
  paneCountLabel,
  tabPaneCount,
  tabDisplayName,
  terminalTaskSummary,
  windowSummary,
  workspaceTabCount,
  workspaceCountLabel,
} from "./dashboard-view-model";

function terminalSlot(overrides: Partial<SlotInfo> = {}): SlotInfo {
  return {
    name: "dev",
    runtime: "terminal",
    status: "running",
    session_name: "dev",
    windows: [
      {
        name: "planner",
        agent: "codex",
        command: "codex",
        session_id: null,
        label: null,
        cwd: "/tmp/demo",
      },
    ],
    ...overrides,
  };
}

function workspace(slots: SlotInfo[], summary: RuntimeSyncReport["summary"]): WorkspaceStatus {
  return {
    status: "ready",
    config_path: "/tmp/demo/.cc-branch/config.yaml",
    state_path: "/tmp/demo/.cc-branch/state.yaml",
    slots,
    runtime_sync: {
      summary,
      slots: [],
      orphaned_state: [],
      historical_sessions: [],
    },
  };
}

describe("dashboard-view-model", () => {
  const t = (key: string, vars?: Record<string, string | number>) => {
    const templates: Record<string, string> = {
      commandSummary: "command {command}",
      paneCountShortOne: "{count} pane",
      paneCountShort: "{count} panes",
      sessionBoundShort: "session {id}",
      sessionCaptureAmbiguous: "ambiguous",
      sessionFreshSummary: "fresh",
      sessionPendingCapture: "pending",
      sessionWillCreate: "will create",
      tabDisplayName: "Tab {index}",
      terminalLabel: "Terminal",
      terminalTask: "terminal task",
      tmuxPane: "Tmux group",
    };
    return (templates[key] || key).replace(/\{(\w+)\}/g, (_, name) => String(vars?.[name] ?? ""));
  };

  it("does not treat stopped missing panes as actionable drift", () => {
    expect(isActionableSyncStatus("missing", "stopped")).toBe(false);
    expect(isActionableSyncStatus("missing", "running")).toBe(true);
  });

  it("counts tmux tabs as one dashboard pane", () => {
    expect(tabPaneCount(terminalSlot({ runtime: "tmux", windows: [terminalSlot().windows[0], terminalSlot().windows[0]] }))).toBe(1);
  });

  it("counts internal split slots as one user-visible dashboard tab", () => {
    const data = workspace([
      terminalSlot({ name: "dev", runtime: "terminal", split_group: "dev", status: "running" }),
      terminalSlot({ name: "dev-agents", runtime: "tmux", split_group: "dev", status: "running" }),
      terminalSlot({ name: "docs", runtime: "terminal", split_group: "docs", status: "stopped" }),
    ], {
      changed: 0,
      current: 0,
      external: 0,
      extra: 0,
      missing: 0,
      orphaned: 0,
      untracked: 0,
    });

    expect(workspaceTabCount(data.slots)).toBe(2);
    expect(buildDashboardRuntimeSummary(data).runningCount).toBe(1);
    expect(buildDashboardRuntimeSummary(data).totalTabs).toBe(2);
  });

  it("formats dashboard workspace counts with natural singular labels", () => {
    const translateCounts = (key: string, vars?: Record<string, string | number>) => {
      const templates: Record<string, string> = {
        tabCountOne: "{count} tab",
        tabCount: "{count} tabs",
        workspacePaneCountOne: "{count} pane",
        workspacePaneCount: "{count} panes",
      };
      return (templates[key] || key).replace("{count}", String(vars?.count));
    };

    expect(workspaceCountLabel(translateCounts, 1, 1)).toBe("1 tab · 1 pane");
    expect(workspaceCountLabel(translateCounts, 2, 3)).toBe("2 tabs · 3 panes");
  });

  it("formats tab and pane labels from the shared dashboard display rules", () => {
    expect(tabDisplayName(t, 0)).toBe("Tab 1");
    expect(paneCountLabel(t, 1)).toBe("1 pane");
    expect(paneCountLabel(t, 3)).toBe("3 panes");
  });

  it("summarizes agent sessions and commands consistently", () => {
    expect(windowSummary(t, {
      ...terminalSlot().windows[0],
      agent: "codex",
      session_id: "1234567890abcdef",
      session_binding_status: undefined,
    })).toBe("session 12345678...");
    expect(windowSummary(t, {
      ...terminalSlot().windows[0],
      agent: "codex",
      session_id: null,
      session_binding_status: "fresh",
    })).toBe("fresh");
    expect(terminalTaskSummary(t, undefined)).toBe("terminal task");
    expect(terminalTaskSummary(t, {
      ...terminalSlot().windows[0],
      agent: null,
      command: "npm run dev",
    })).toBe("command npm run dev");
  });

  it("derives split-group slot names without exposing implementation prefixes", () => {
    expect(groupedSlotDisplayName(t, terminalSlot({ name: "dev", runtime: "terminal" }), "dev")).toBe("Terminal");
    expect(groupedSlotDisplayName(t, terminalSlot({ name: "dev-agents", runtime: "tmux" }), "dev")).toBe("agents");
    expect(groupedSlotDisplayName(t, terminalSlot({ name: "docs", runtime: "terminal" }), "dev")).toBe("docs");
  });

  it("counts slot-level drift only when child panes are not already counted", () => {
    const slot = terminalSlot({
      sync_status: "changed",
      windows: [
        { ...terminalSlot().windows[0], name: "planner", sync_status: "changed" },
        { ...terminalSlot().windows[0], name: "reviewer", sync_status: "untracked" },
      ],
    });

    expect(actionableRuntimeDriftCount([slot])).toBe(2);
  });

  it("uses runtime summary counts when pane-level sync status is absent", () => {
    const data = workspace([terminalSlot()], {
      changed: 1,
      current: 0,
      external: 0,
      extra: 3,
      missing: 2,
      orphaned: 0,
      untracked: 4,
    });

    const summary = buildDashboardRuntimeSummary(data);

    expect(summary.driftCount).toBe(0);
    expect(summary.syncCount).toBe(5);
    expect(summary.issueCount).toBe(8);
  });

  it("does not double count summary drift when pane-level status is richer", () => {
    const data = workspace([
      terminalSlot({ windows: [{ ...terminalSlot().windows[0], sync_status: "changed" }] }),
    ], {
      changed: 1,
      current: 0,
      external: 0,
      extra: 0,
      missing: 0,
      orphaned: 0,
      untracked: 0,
    });

    expect(buildDashboardRuntimeSummary(data).issueCount).toBe(1);
  });

  it("keeps orphaned local state separate from primary dashboard issues", () => {
    const data = workspace([terminalSlot()], {
      changed: 0,
      current: 1,
      external: 0,
      extra: 0,
      missing: 0,
      orphaned: 2,
      untracked: 0,
    });

    const summary = buildDashboardRuntimeSummary(data);

    expect(summary.orphanedCount).toBe(2);
    expect(summary.issueCount).toBe(0);
  });
});
