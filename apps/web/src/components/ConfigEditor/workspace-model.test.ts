import { describe, expect, it } from "vitest";
import type { SlotConfig, WindowConfig } from "./types";
import {
  clampSelection,
  configuredPaneCount,
  editableWindowsForSlot,
  isLegacyTmuxSlot,
  isTmuxGroupWindow,
  slotToCanvasPanes,
  slotWithWindows,
  tmuxGroupWindowFromSlot,
  tmuxGroupWindows,
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
});
