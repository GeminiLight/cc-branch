import { describe, expect, it } from "vitest";
import type { SlotConfig, WindowConfig } from "./types";
import {
  dropAxisForSlot,
  isPointerAfterDropMidpoint,
} from "./workspace-drag";

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
    windows: [windowConfig({ name: "ui" }), windowConfig({ name: "api" })],
    ...patch,
  };
}

describe("workspace drag helpers", () => {
  it("uses vertical midpoint checks for vertical and main-top layouts", () => {
    expect(dropAxisForSlot(slotConfig({ layout: "vertical" }))).toBe("vertical");
    expect(dropAxisForSlot(slotConfig({ layout: "main-top" }))).toBe("vertical");
  });

  it("uses horizontal midpoint checks for horizontal, main-left, grid, and auto layouts", () => {
    expect(dropAxisForSlot(slotConfig({ layout: "horizontal" }))).toBe("horizontal");
    expect(dropAxisForSlot(slotConfig({ layout: "main-left" }))).toBe("horizontal");
    expect(dropAxisForSlot(slotConfig({ layout: "grid" }))).toBe("horizontal");
    expect(dropAxisForSlot(slotConfig({ layout: "auto" }))).toBe("horizontal");
  });

  it("detects whether a pointer lands after a pane midpoint on the active axis", () => {
    const rect = { left: 10, top: 20, width: 100, height: 80 };

    expect(isPointerAfterDropMidpoint("horizontal", { clientX: 61, clientY: 20 }, rect)).toBe(true);
    expect(isPointerAfterDropMidpoint("horizontal", { clientX: 59, clientY: 100 }, rect)).toBe(false);
    expect(isPointerAfterDropMidpoint("vertical", { clientX: 10, clientY: 61 }, rect)).toBe(true);
    expect(isPointerAfterDropMidpoint("vertical", { clientX: 110, clientY: 59 }, rect)).toBe(false);
  });
});
