import { describe, expect, it } from "vitest";
import type { SlotConfig } from "./types";
import { validateWorkspaceNames } from "./workspace-validation";

function slot(name: string, windows: string[] = ["main"]): SlotConfig {
  return {
    name,
    runtime: "terminal",
    cwd: ".",
    env: {},
    windows: windows.map((windowName) => ({
      name: windowName,
      agent: null,
      command: null,
      cwd: null,
      env: {},
      session: null,
      session_id: null,
      shell: null,
      label: null,
      label_template: null,
      resume_mode: null,
      resume_template: null,
      create_mode: null,
      create_template: null,
      label_mode: null,
      rename_template: null,
    })),
  };
}

describe("validateWorkspaceNames", () => {
  it("detects duplicate tab names after trimming whitespace", () => {
    expect(validateWorkspaceNames([slot("dev"), slot(" dev "), slot("review")])).toMatchObject({
      duplicateTabNames: ["dev"],
      hasEmptyTabNames: false,
      hasEmptyPaneNames: false,
      reservedTargetNames: [],
    });
  });

  it("detects empty tab and pane names", () => {
    expect(validateWorkspaceNames([slot("  "), slot("dev", ["main", "  "])])).toMatchObject({
      duplicateTabNames: [],
      hasEmptyTabNames: true,
      hasEmptyPaneNames: true,
      reservedTargetNames: [],
    });
  });

  it("detects empty names inside nested tmux group windows", () => {
    const workspace = slot("dev", ["agents"]);
    workspace.windows[0].layoutBackend = "tmux";
    workspace.windows[0].windows = [
      {
        name: "frontend",
        agent: null,
        command: "zsh",
        cwd: null,
        env: {},
        session: null,
        session_id: null,
        shell: null,
        label: null,
        label_template: null,
        resume_mode: null,
        resume_template: null,
        create_mode: null,
        create_template: null,
        label_mode: null,
        rename_template: null,
      },
      {
        name: " ",
        agent: null,
        command: "zsh",
        cwd: null,
        env: {},
        session: null,
        session_id: null,
        shell: null,
        label: null,
        label_template: null,
        resume_mode: null,
        resume_template: null,
        create_mode: null,
        create_template: null,
        label_mode: null,
        rename_template: null,
      },
    ];

    expect(validateWorkspaceNames([workspace])).toMatchObject({
      duplicateTabNames: [],
      hasEmptyTabNames: false,
      hasEmptyPaneNames: true,
      reservedTargetNames: [],
    });
  });

  it("detects target separators in tab, pane, and nested tmux window names", () => {
    const workspace = slot("dev:ui", ["main.shell", "agents"]);
    workspace.windows[1].layoutBackend = "tmux";
    workspace.windows[1].windows = [
      {
        name: "worker:1",
        agent: null,
        command: "zsh",
        cwd: null,
        env: {},
        session: null,
        session_id: null,
        shell: null,
        label: null,
        label_template: null,
        resume_mode: null,
        resume_template: null,
        create_mode: null,
        create_template: null,
        label_mode: null,
        rename_template: null,
      },
    ];

    expect(validateWorkspaceNames([workspace])).toMatchObject({
      duplicateTabNames: [],
      hasEmptyTabNames: false,
      hasEmptyPaneNames: false,
      reservedTargetNames: ["dev:ui", "main.shell", "worker:1"],
    });
  });
});
