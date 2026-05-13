import { describe, expect, it } from "vitest";
import type { SlotConfig, WindowConfig } from "./types";
import { deriveWorkspaceSelection } from "./workspace-selection";

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

describe("workspace selection", () => {
  it("returns an inert tab selection when there are no tabs", () => {
    const state = deriveWorkspaceSelection([], { slotIndex: 4, target: "pane", windowIndex: 2 });

    expect(state.normalizedSelection).toEqual({ slotIndex: 0, target: "tab", windowIndex: null });
    expect(state.selectedSlot).toBeUndefined();
    expect(state.editingPane).toBe(false);
  });

  it("treats an empty terminal tab pane selection as a single terminal pane", () => {
    const state = deriveWorkspaceSelection(
      [slotConfig({ name: "scratch", command: "zsh", windows: [] })],
      { slotIndex: 0, target: "pane", windowIndex: null },
    );

    expect(state.selectedTerminalPane).toBe(true);
    expect(state.selectedTerminalWindow).toBeNull();
    expect(state.selectedTmuxGroup).toBe(false);
    expect(state.editingPane).toBe(true);
  });

  it("recognizes a normal terminal window selection", () => {
    const ui = windowConfig({ name: "ui", command: "npm run dev" });
    const state = deriveWorkspaceSelection(
      [slotConfig({ windows: [ui] })],
      { slotIndex: 0, target: "pane", windowIndex: 0 },
    );

    expect(state.selectedWindow).toBe(ui);
    expect(state.selectedTerminalWindow).toBe(ui);
    expect(state.selectedTmuxGroup).toBe(false);
    expect(state.editingPane).toBe(true);
  });

  it("recognizes legacy tmux tabs as one selected tmux group", () => {
    const state = deriveWorkspaceSelection(
      [slotConfig({ runtime: "tmux", windows: [windowConfig({ name: "frontend" })] })],
      { slotIndex: 0, target: "pane", windowIndex: null },
    );

    expect(state.selectedWindow).toBeNull();
    expect(state.selectedTerminalWindow).toBeNull();
    expect(state.selectedTmuxGroup).toBe(true);
    expect(state.editingPane).toBe(true);
  });

  it("recognizes explicit tmux group windows without treating them as terminal panes", () => {
    const group = windowConfig({
      name: "services",
      layoutBackend: "tmux",
      windows: [windowConfig({ name: "api" })],
    });
    const state = deriveWorkspaceSelection(
      [slotConfig({ windows: [windowConfig({ name: "shell" }), group] })],
      { slotIndex: 0, target: "pane", windowIndex: 1 },
    );

    expect(state.selectedWindow).toBe(group);
    expect(state.selectedTerminalWindow).toBeNull();
    expect(state.selectedTmuxGroup).toBe(true);
    expect(state.editingPane).toBe(true);
  });
});
