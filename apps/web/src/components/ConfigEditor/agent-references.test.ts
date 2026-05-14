import { describe, expect, it } from "vitest";
import type { SlotConfig, WindowConfig } from "./types";
import { collectReferencedAgents, renameSlotAgentReferences } from "./agent-references";

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

describe("agent references", () => {
  it("renames agent references inside nested tmux group windows", () => {
    const slots = [
      slotConfig({
        agent: "codex",
        windows: [
          windowConfig({ name: "ui", agent: "claude" }),
          windowConfig({
            name: "workers",
            layoutBackend: "tmux",
            windows: [
              windowConfig({ name: "backend", agent: "claude" }),
              windowConfig({ name: "docs", agent: "codex" }),
            ],
          }),
        ],
      }),
    ];

    const renamed = renameSlotAgentReferences(slots, { from: "claude", to: "reviewer" });

    expect(renamed[0].agent).toBe("codex");
    expect(renamed[0].windows[0].agent).toBe("reviewer");
    expect(renamed[0].windows[1].windows?.[0].agent).toBe("reviewer");
    expect(renamed[0].windows[1].windows?.[1].agent).toBe("codex");
    expect(slots[0].windows[1].windows?.[0].agent).toBe("claude");
  });

  it("collects agent references recursively for dropdown options", () => {
    const slots = [
      slotConfig({
        agent: "shell-agent",
        windows: [
          windowConfig({
            name: "agents",
            layoutBackend: "tmux",
            windows: [
              windowConfig({ name: "frontend", agent: "codex" }),
              windowConfig({ name: "review", agent: "claude" }),
            ],
          }),
        ],
      }),
    ];

    expect(collectReferencedAgents(slots)).toEqual(["shell-agent", "codex", "claude"]);
  });
});
