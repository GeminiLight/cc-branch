import { describe, expect, it } from "vitest";
import type { SlotConfig, WindowConfig } from "./types";
import {
  addTabMutation,
  clampSelection,
  configuredPaneCount,
  deleteTabMutation,
  editableWindowsForSlot,
  isLegacyTmuxSlot,
  isTmuxGroupWindow,
  movePaneBetweenSlots,
  movePaneWithinTabMutation,
  moveTab,
  slotToCanvasPanes,
  slotWithWindows,
  tmuxGroupWindowFromSlot,
  tmuxGroupWindows,
  uniqueTabName,
} from "./workspace-model";

function windowConfig(patch: Partial<WindowConfig> = {}): WindowConfig {
  return {
    name: "main",
    agent: null,
    command: null,
    cwd: null,
    env: {},
    session: null,
    session_id: null,
    label: null,
    label_template: null,
    resume_mode: null,
    resume_template: null,
    create_mode: null,
    create_template: null,
    label_mode: null,
    rename_template: null,
    ...patch,
  };
}

function slotConfig(patch: Partial<SlotConfig> = {}): SlotConfig {
  return {
    name: "dev",
    runtime: "terminal",
    cwd: ".",
    env: {},
    windows: [],
    ...patch,
  };
}

describe("workspace model", () => {
  it("generates a stable unique tab name", () => {
    const slots = [
      slotConfig({ name: "coding" }),
      slotConfig({ name: "coding-1" }),
      slotConfig({ name: "review" }),
    ];

    expect(uniqueTabName(slots)).toBe("coding-2");
  });

  it("adds a tmux tab with a default builder window", () => {
    const mutation = addTabMutation([], "tmux", ["codex"]);

    expect(mutation.slots).toEqual([
      expect.objectContaining({
        name: "coding",
        runtime: "tmux",
        layout: "auto",
        cwd: ".",
        env: {},
        windows: [expect.objectContaining({ name: "builder", agent: "codex" })],
      }),
    ]);
    expect(mutation.selection).toEqual({ slotIndex: 0, target: "tab", windowIndex: null });
  });

  it("adds a terminal tab with the first available agent", () => {
    const mutation = addTabMutation([slotConfig({ name: "coding" })], "terminal", ["claude"]);

    expect(mutation.slots[1]).toMatchObject({
      name: "coding-1",
      runtime: "terminal",
      agent: "claude",
      windows: [],
    });
    expect(mutation.slots[1].command).toBeUndefined();
    expect(mutation.selection).toEqual({ slotIndex: 1, target: "tab", windowIndex: null });
  });

  it("adds a terminal tab with a shell command when no agent exists", () => {
    const mutation = addTabMutation([], "terminal", []);

    expect(mutation.slots[0]).toMatchObject({
      name: "coding",
      runtime: "terminal",
      command: "$SHELL",
      windows: [],
    });
    expect(mutation.slots[0].agent).toBeUndefined();
  });

  it("deletes a tab and selects the previous tab", () => {
    const mutation = deleteTabMutation([
      slotConfig({ name: "first" }),
      slotConfig({ name: "second" }),
      slotConfig({ name: "third" }),
    ], 1);

    expect(mutation?.slots.map((slot) => slot.name)).toEqual(["first", "third"]);
    expect(mutation?.selection).toEqual({ slotIndex: 0, target: "tab", windowIndex: null });
  });

  it("ignores invalid tab deletion indexes", () => {
    expect(deleteTabMutation([slotConfig()], -1)).toBeNull();
    expect(deleteTabMutation([slotConfig()], 1)).toBeNull();
  });

  it("treats legacy tmux slots as one outer pane regardless of internal windows", () => {
    const slot = slotConfig({
      runtime: "tmux",
      windows: [
        windowConfig({ name: "frontend" }),
        windowConfig({ name: "backend" }),
        windowConfig({ name: "docs" }),
      ],
    });

    expect(isLegacyTmuxSlot(slot)).toBe(true);
    expect(configuredPaneCount(slot)).toBe(1);
  });

  it("counts explicit tmux groups as panes without counting their internal windows", () => {
    const slot = slotConfig({
      windows: [
        windowConfig({ name: "ui" }),
        windowConfig({
          name: "workers",
          layoutBackend: "tmux",
          windows: [windowConfig({ name: "api" }), windowConfig({ name: "jobs" })],
        }),
      ],
    });

    expect(isTmuxGroupWindow(slot.windows[1])).toBe(true);
    expect(isLegacyTmuxSlot(slot)).toBe(false);
    expect(configuredPaneCount(slot)).toBe(2);
  });

  it("treats an explicit empty windows array as a tmux group marker", () => {
    const slot = slotConfig({
      runtime: "tmux",
      windows: [windowConfig({ name: "empty-group", windows: [] })],
    });

    expect(isTmuxGroupWindow(slot.windows[0])).toBe(true);
    expect(isLegacyTmuxSlot(slot)).toBe(false);
    expect(configuredPaneCount(slot)).toBe(1);
  });

  it("projects a legacy tmux tab as one canvas pane with internal windows hidden", () => {
    const slot = slotConfig({
      name: "dev",
      runtime: "tmux",
      windows: [
        windowConfig({ name: "frontend", agent: "codex" }),
        windowConfig({ name: "backend", agent: "claude" }),
      ],
    });

    expect(slotToCanvasPanes(slot)).toEqual([{
      name: "dev",
      agent: "codex",
      cwd: ".",
      windowIndex: null,
      kind: "tmux-group",
    }]);
  });

  it("uses a terminal slot fallback window without changing the source slot", () => {
    const slot = slotConfig({
      name: "scratch",
      runtime: "terminal",
      command: "zsh",
      windows: [],
    });

    const windows = editableWindowsForSlot(slot);

    expect(windows).toHaveLength(1);
    expect(windows[0].name).toBe("scratch");
    expect(windows[0].command).toBe("zsh");
    expect(slot.windows).toEqual([]);
  });

  it("wraps legacy tmux tabs as movable tmux group windows", () => {
    const slot = slotConfig({
      name: "dev",
      runtime: "tmux",
      cwd: "app",
      env: { NODE_ENV: "development" },
      windows: [windowConfig({ name: "api" })],
    });

    expect(tmuxGroupWindowFromSlot(slot)).toMatchObject({
      name: "dev",
      layoutBackend: "tmux",
      cwd: "app",
      env: { NODE_ENV: "development" },
      windows: [expect.objectContaining({ name: "api" })],
    });
  });

  it("falls back to a single tmux window when an explicit group has no children", () => {
    const group = windowConfig({ name: "group", agent: "codex", windows: [] });

    expect(tmuxGroupWindows(group)).toEqual([
      expect.objectContaining({ name: "group", agent: "codex" }),
    ]);
  });

  it("normalizes a slot containing a tmux group back to terminal runtime", () => {
    const slot = slotConfig({ runtime: "tmux", command: "tmux attach", agent: "codex" });
    const next = slotWithWindows(slot, [
      windowConfig({ name: "shell" }),
      windowConfig({ name: "group", layoutBackend: "tmux", windows: [windowConfig({ name: "api" })] }),
    ]);

    expect(next.runtime).toBe("terminal");
    expect(next.command).toBeUndefined();
    expect(next.agent).toBeUndefined();
    expect(next.windows).toHaveLength(2);
  });

  it("clamps pane selections to the current tab shape", () => {
    const slots = [
      slotConfig({ name: "first", windows: [windowConfig({ name: "one" })] }),
      slotConfig({
        name: "second",
        windows: [windowConfig({ name: "two" }), windowConfig({ name: "three" })],
      }),
    ];

    expect(clampSelection({ slotIndex: 9, target: "pane", windowIndex: 9 }, slots)).toEqual({
      slotIndex: 1,
      target: "pane",
      windowIndex: 1,
    });
  });

  it("moves tabs while keeping the same selected tab identity", () => {
    const first = slotConfig({ name: "first" });
    const second = slotConfig({ name: "second" });
    const third = slotConfig({ name: "third" });

    const mutation = moveTab([first, second, third], 0, 3, {
      slotIndex: 1,
      target: "tab",
      windowIndex: null,
    });

    expect(mutation?.slots.map((slot) => slot.name)).toEqual(["second", "third", "first"]);
    expect(mutation?.selection).toEqual({ slotIndex: 0, target: "tab", windowIndex: null });
  });

  it("reorders panes inside one tab without changing runtimes", () => {
    const slots = [
      slotConfig({
        name: "dev",
        runtime: "terminal",
        windows: [windowConfig({ name: "ui" }), windowConfig({ name: "api" }), windowConfig({ name: "docs" })],
      }),
    ];

    const mutation = movePaneBetweenSlots(slots, 0, 0, 0, 3);

    expect(mutation?.slots[0].runtime).toBe("terminal");
    expect(mutation?.slots[0].windows.map((window) => window.name)).toEqual(["api", "docs", "ui"]);
    expect(mutation?.selection).toEqual({ slotIndex: 0, target: "pane", windowIndex: 2 });
  });

  it("moves panes inside one tab by direction", () => {
    const slots = [
      slotConfig({
        name: "dev",
        runtime: "terminal",
        windows: [windowConfig({ name: "ui" }), windowConfig({ name: "api" }), windowConfig({ name: "docs" })],
      }),
    ];

    const mutation = movePaneWithinTabMutation(slots, 0, 1, -1);

    expect(mutation?.slots[0].runtime).toBe("terminal");
    expect(mutation?.slots[0].windows.map((window) => window.name)).toEqual(["api", "ui", "docs"]);
    expect(mutation?.selection).toEqual({ slotIndex: 0, target: "pane", windowIndex: 0 });
  });

  it("does not move an implicit terminal fallback pane", () => {
    const mutation = movePaneWithinTabMutation([slotConfig({ runtime: "terminal", windows: [] })], 0, 0, 1);

    expect(mutation).toBeNull();
  });

  it("moves panes across tabs even when their runtimes differ", () => {
    const slots = [
      slotConfig({
        name: "source",
        runtime: "terminal",
        windows: [windowConfig({ name: "frontend" }), windowConfig({ name: "backend" })],
      }),
      slotConfig({
        name: "target",
        runtime: "tmux",
        windows: [windowConfig({ name: "worker" })],
      }),
    ];

    const mutation = movePaneBetweenSlots(slots, 0, 1, 1, 1);

    expect(mutation?.slots).toHaveLength(2);
    expect(mutation?.slots[0].windows.map((window) => window.name)).toEqual(["frontend"]);
    expect(mutation?.slots[1].runtime).toBe("terminal");
    expect(mutation?.slots[1].windows.map((window) => window.name)).toEqual(["target", "backend"]);
    expect(mutation?.slots[1].windows[0]).toMatchObject({
      layoutBackend: "tmux",
      windows: [expect.objectContaining({ name: "worker" })],
    });
    expect(mutation?.selection).toEqual({ slotIndex: 1, target: "pane", windowIndex: 1 });
  });

  it("turns a legacy tmux tab into a movable tmux group when dropped into another tab", () => {
    const slots = [
      slotConfig({
        name: "tmux-dev",
        runtime: "tmux",
        windows: [windowConfig({ name: "frontend" }), windowConfig({ name: "backend" })],
      }),
      slotConfig({
        name: "terminal-dev",
        runtime: "terminal",
        windows: [windowConfig({ name: "review" })],
      }),
    ];

    const mutation = movePaneBetweenSlots(slots, 0, 0, 1, 1);

    expect(mutation?.slots).toHaveLength(1);
    expect(mutation?.slots[0].name).toBe("terminal-dev");
    expect(mutation?.slots[0].runtime).toBe("terminal");
    expect(mutation?.slots[0].windows).toHaveLength(2);
    expect(mutation?.slots[0].windows[1]).toMatchObject({
      name: "tmux-dev",
      layoutBackend: "tmux",
      windows: [expect.objectContaining({ name: "frontend" }), expect.objectContaining({ name: "backend" })],
    });
    expect(mutation?.selection).toEqual({ slotIndex: 0, target: "pane", windowIndex: 1 });
  });

  it("removes an empty source tab after moving its last explicit pane", () => {
    const slots = [
      slotConfig({
        name: "single",
        runtime: "terminal",
        windows: [windowConfig({ name: "only" })],
      }),
      slotConfig({
        name: "target",
        runtime: "terminal",
        windows: [windowConfig({ name: "existing" })],
      }),
    ];

    const mutation = movePaneBetweenSlots(slots, 0, 0, 1, 1);

    expect(mutation?.slots.map((slot) => slot.name)).toEqual(["target"]);
    expect(mutation?.slots[0].windows.map((window) => window.name)).toEqual(["existing", "only"]);
    expect(mutation?.selection).toEqual({ slotIndex: 0, target: "pane", windowIndex: 1 });
  });
});
