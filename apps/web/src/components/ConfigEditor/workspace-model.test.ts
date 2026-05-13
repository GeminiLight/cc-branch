import { describe, expect, it } from "vitest";
import type { SlotConfig, WindowConfig } from "./types";
import { configuredPaneCount, isLegacyTmuxSlot, isTmuxGroupWindow } from "./workspace-model";

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
});
