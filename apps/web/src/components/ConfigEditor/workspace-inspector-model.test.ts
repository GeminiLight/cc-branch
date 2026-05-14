import { describe, expect, it } from "vitest";
import type { SlotConfig, WindowConfig } from "./types";
import {
  canMoveSelectedPaneToTarget,
  isSelectedPaneMovable,
  moveTargetOptionsForSelection,
  selectedMoveTargetIndex,
  selectedPaneOrderState,
  selectedTmuxGroupPositionState,
} from "./workspace-inspector-model";
import { deriveWorkspaceSelection } from "./workspace-selection";

function t(key: string, vars?: Record<string, string | number>): string {
  if (key === "unnamed") return "Unnamed";
  if (key === "tabSummaryPanes") return `${vars?.count} panes`;
  return key;
}

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

describe("workspace inspector model", () => {
  it("offers all other tabs as pane move targets", () => {
    const slots = [
      slotConfig({ name: "dev", windows: [windowConfig({ name: "ui" })] }),
      slotConfig({ name: "ops", windows: [windowConfig({ name: "shell" }), windowConfig({ name: "logs" })] }),
      slotConfig({ name: "", windows: [] }),
    ];
    const state = deriveWorkspaceSelection(slots, { slotIndex: 0, target: "pane", windowIndex: 0 });

    expect(moveTargetOptionsForSelection(slots, state, t)).toEqual([
      { value: "1", label: "ops · 2 panes" },
      { value: "2", label: "Unnamed · 1 panes" },
    ]);
  });

  it("recognizes explicit and implicit terminal panes as movable", () => {
    const explicit = deriveWorkspaceSelection(
      [slotConfig({ windows: [windowConfig({ name: "ui" })] }), slotConfig({ name: "ops" })],
      { slotIndex: 0, target: "pane", windowIndex: 0 },
    );
    const implicit = deriveWorkspaceSelection(
      [slotConfig({ name: "shell", windows: [] }), slotConfig({ name: "ops" })],
      { slotIndex: 0, target: "pane", windowIndex: null },
    );

    expect(isSelectedPaneMovable(explicit)).toBe(true);
    expect(isSelectedPaneMovable(implicit)).toBe(true);
    expect(canMoveSelectedPaneToTarget(explicit, 1)).toBe(true);
    expect(canMoveSelectedPaneToTarget(explicit, 0)).toBe(false);
    expect(selectedMoveTargetIndex("")).toBe(-1);
    expect(selectedMoveTargetIndex("2")).toBe(2);
  });

  it("derives pane order controls from the selected window index", () => {
    const state = deriveWorkspaceSelection(
      [
        slotConfig({
          windows: [
            windowConfig({ name: "ui" }),
            windowConfig({ name: "spec" }),
            windowConfig({ name: "docs" }),
          ],
        }),
      ],
      { slotIndex: 0, target: "pane", windowIndex: 1 },
    );

    expect(selectedPaneOrderState(state)).toEqual({ canMoveUp: true, canMoveDown: true });
  });

  it("moves legacy tmux groups as tabs and explicit tmux groups as panes", () => {
    const legacySlots = [
      slotConfig({ name: "dev", runtime: "terminal", windows: [windowConfig({ name: "ui" })] }),
      slotConfig({ name: "tmux", runtime: "tmux", windows: [windowConfig({ name: "worker" })] }),
    ];
    const legacy = deriveWorkspaceSelection(legacySlots, { slotIndex: 1, target: "pane", windowIndex: null });
    expect(selectedTmuxGroupPositionState(legacySlots, legacy)).toEqual({
      isLegacy: true,
      canMoveUp: true,
      canMoveDown: false,
    });

    const explicitSlots = [
      slotConfig({
        name: "dev",
        windows: [
          windowConfig({ name: "shell" }),
          windowConfig({ name: "services", layoutBackend: "tmux", windows: [windowConfig({ name: "api" })] }),
        ],
      }),
    ];
    const explicit = deriveWorkspaceSelection(explicitSlots, { slotIndex: 0, target: "pane", windowIndex: 1 });
    expect(selectedTmuxGroupPositionState(explicitSlots, explicit)).toEqual({
      isLegacy: false,
      canMoveUp: true,
      canMoveDown: false,
    });
  });
});
