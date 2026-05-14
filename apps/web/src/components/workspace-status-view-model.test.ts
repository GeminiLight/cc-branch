import { describe, expect, it } from "vitest";
import type { SlotInfo } from "../types";
import {
  runningWorkspaceTabCount,
  tabPaneCount,
  workspaceTabCount,
  workspaceTabGroups,
} from "./workspace-status-view-model";

function slot(overrides: Partial<SlotInfo> = {}): SlotInfo {
  return {
    name: "dev",
    runtime: "terminal",
    status: "running",
    session_name: "demo-dev",
    windows: [
      {
        name: "ui",
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

describe("workspace-status-view-model", () => {
  it("counts tmux slots as one external pane while preserving internal windows", () => {
    expect(tabPaneCount(slot({ runtime: "tmux", windows: [slot().windows[0], slot().windows[0]] }))).toBe(1);
  });

  it("groups internal split slots into one user-visible tab", () => {
    const slots = [
      slot({ name: "dev", split_group: "dev", runtime: "terminal", status: "running" }),
      slot({ name: "dev-agents", split_group: "dev", runtime: "tmux", status: "running" }),
      slot({ name: "docs", split_group: "docs", runtime: "terminal", status: "stopped" }),
    ];

    expect(workspaceTabCount(slots)).toBe(2);
    expect(runningWorkspaceTabCount(slots)).toBe(1);
    expect(workspaceTabGroups(slots).map((group) => ({
      name: group.name,
      slots: group.slots.map((groupSlot) => groupSlot.name),
      paneCount: group.paneCount,
    }))).toEqual([
      { name: "dev", slots: ["dev", "dev-agents"], paneCount: 2 },
      { name: "docs", slots: ["docs"], paneCount: 1 },
    ]);
  });
});
