import { describe, expect, it } from "vitest";
import { parseConfigYaml, serializeConfigForm } from "./yaml-utils";

describe("ConfigEditor YAML session intent", () => {
  it("parses canonical workspace terms and pane shell overrides", () => {
    const data = parseConfigYaml([
      "version: 2",
      "project: demo",
      "root: .",
      "openWith: cursor",
      "layoutBackend: tmux",
      "defaults:",
      "  shell: system-default",
      "tabs:",
      "  - name: dev",
      "    panes:",
      "      - name: planner",
      "        agent: codex",
      "      - name: server",
      "        command: pnpm dev",
      "        shell: zsh",
      "",
    ].join("\n"));

    expect(data.openWith).toBe("cursor");
    expect(data.layoutBackend).toBe("tmux");
    expect(data.defaults?.shell).toBe("system-default");
    expect(data.slots[0].runtime).toBe("tmux");
    expect(data.slots[0].windows[0].name).toBe("planner");
    expect(data.slots[0].windows[0].shell).toBeNull();
    expect(data.slots[0].windows[1].shell).toBe("zsh");
  });

  it("serializes canonical workspace terms without runtime windows wrappers", () => {
    const yaml = serializeConfigForm({
      version: 2,
      project: "demo",
      root: ".",
      openWith: "warp",
      layoutBackend: "tmux",
      defaults: { shell: "system-default" },
      display: { mode: "grid", columns: 2, dashboard: false },
      agents: {},
      slots: [
        {
          name: "dev",
          runtime: "tmux",
          cwd: ".",
          env: {},
          windows: [
            {
              name: "planner",
              agent: "codex",
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
            },
            {
              name: "server",
              agent: null,
              command: "pnpm dev",
              cwd: null,
              env: {},
              session: null,
              session_id: null,
              shell: "zsh",
              label: null,
              label_template: null,
              resume_mode: null,
              resume_template: null,
              create_mode: null,
              create_template: null,
              label_mode: null,
              rename_template: null,
            },
          ],
        },
      ],
    });

    expect(yaml).toContain("openWith: warp");
    expect(yaml).toContain("layoutBackend: tmux");
    expect(yaml).toContain("defaults:");
    expect(yaml).toContain("shell: system-default");
    expect(yaml).toContain("name: planner");
    expect(yaml).toContain("name: server");
    expect(yaml).toContain("shell: zsh");
    expect(yaml).not.toContain("runtime:");
    expect(yaml).not.toContain("windows:");
  });

  it("parses session intent from panes", () => {
    const data = parseConfigYaml([
      "version: 2",
      "project: demo",
      "root: .",
      "tabs:",
      "  - name: dev",
      "    panes:",
      "      - name: planner",
      "        runtime: tmux",
      "        agent: codex",
      "        session: fresh",
      "",
    ].join("\n"));

    expect(data.slots[0].windows[0].session).toBe("fresh");
  });

  it("migrates legacy session_id into session intent", () => {
    const data = parseConfigYaml([
      "version: 2",
      "project: demo",
      "root: .",
      "tabs:",
      "  - name: dev",
      "    panes:",
      "      - name: planner",
      "        agent: codex",
      "        session_id: old-session",
      "",
    ].join("\n"));

    expect(data.slots[0].windows[0].session).toBe("old-session");
  });

  it("serializes session intent without writing session_id", () => {
    const yaml = serializeConfigForm({
      version: 2,
      project: "demo",
      root: ".",
      display: { mode: "grid", columns: 2, dashboard: false },
      agents: {},
      slots: [
        {
          name: "dev",
          runtime: "tmux",
          cwd: ".",
          env: {},
          windows: [
            {
              name: "planner",
              agent: "codex",
              command: null,
              cwd: null,
              env: {},
              session: "codex-session-123",
              session_id: null,
              label: null,
              label_template: null,
              resume_mode: null,
              resume_template: null,
              create_mode: null,
              create_template: null,
              label_mode: null,
              rename_template: null,
            },
          ],
        },
      ],
    });

    expect(yaml).toContain("session: codex-session-123");
    expect(yaml).not.toContain("session_id");
  });
});
