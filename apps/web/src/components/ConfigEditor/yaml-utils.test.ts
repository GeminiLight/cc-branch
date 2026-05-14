import { describe, expect, it } from "vitest";
import { parseConfigYaml, serializeConfigForm, validateConfigForm } from "./yaml-utils";

describe("ConfigEditor YAML session intent", () => {
  it("validates duplicate tab names after trimming whitespace", () => {
    const data = parseConfigYaml([
      "version: 2",
      "project: demo",
      "root: .",
      "tabs:",
      "  - name: dev",
      "    panes:",
      "      - name: main",
      "  - name: \" dev \"",
      "    panes:",
      "      - name: review",
      "",
    ].join("\n"));

    expect(validateConfigForm(data)).toContain("Duplicate slot names: dev");
  });

  it("validates target separators in tab and pane names", () => {
    const data = parseConfigYaml([
      "version: 2",
      "project: demo",
      "root: .",
      "tabs:",
      "  - name: dev:ui",
      "    panes:",
      "      - name: main.shell",
      "        command: zsh",
      "",
    ].join("\n"));

    expect(validateConfigForm(data)).toContain("Names cannot contain ':' or '.': dev:ui, main.shell");
  });

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

  it("normalizes legacy opener ids to registered opener ids", () => {
    expect(parseConfigYaml("version: 2\nproject: demo\nopenWith: terminal\n").openWith).toBe("terminal-app");
    expect(parseConfigYaml("version: 2\nproject: demo\nopenWith: iterm\n").openWith).toBe("iterm2");
    expect(parseConfigYaml("version: 2\nproject: demo\ndefault_opener: terminal\n").openWith).toBe("terminal-app");
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

  it("round-trips a mixed tab with a terminal pane and a tmux window group", () => {
    const yaml = [
      "version: 2",
      "project: demo",
      "root: .",
      "tabs:",
      "  - name: dev",
      "    panes:",
      "      - name: ui",
      "        agent: codex",
      "      - name: tmux-dev",
      "        layoutBackend: tmux",
      "        windows:",
      "          - name: frontend",
      "            agent: codex",
      "          - name: backend",
      "            command: pnpm api",
      "",
    ].join("\n");

    const parsed = parseConfigYaml(yaml);
    const serialized = serializeConfigForm(parsed);
    const reparsed = parseConfigYaml(serialized);

    expect(parsed.slots).toHaveLength(1);
    expect(parsed.slots[0].windows).toHaveLength(2);
    expect(parsed.slots[0].windows[0].name).toBe("ui");
    expect(parsed.slots[0].windows[0].layoutBackend).toBe("direct");
    expect(parsed.slots[0].windows[1].name).toBe("tmux-dev");
    expect(parsed.slots[0].windows[1].layoutBackend).toBe("tmux");
    expect(parsed.slots[0].windows[1].windows?.map((window) => window.name)).toEqual([
      "frontend",
      "backend",
    ]);
    expect(serialized).toContain("layoutBackend: tmux");
    expect(serialized).toContain("windows:");
    expect(reparsed.slots[0].windows[1].windows?.map((window) => window.name)).toEqual([
      "frontend",
      "backend",
    ]);
  });

  it("parses mixed panes under a tmux default as a canvas tab container", () => {
    const yaml = [
      "version: 2",
      "project: demo",
      "root: .",
      "layoutBackend: tmux",
      "tabs:",
      "  - name: dev",
      "    panes:",
      "      - name: ui",
      "        layoutBackend: direct",
      "        agent: codex",
      "      - name: agents",
      "        layoutBackend: tmux",
      "        windows:",
      "          - name: planner",
      "            agent: codex",
      "",
    ].join("\n");

    const parsed = parseConfigYaml(yaml);
    const serialized = serializeConfigForm(parsed);

    expect(parsed.layoutBackend).toBe("tmux");
    expect(parsed.slots).toHaveLength(1);
    expect(parsed.slots[0].runtime).toBe("terminal");
    expect(parsed.slots[0].windows.map((window) => window.name)).toEqual(["ui", "agents"]);
    expect(parsed.slots[0].windows[0].layoutBackend).toBe("direct");
    expect(parsed.slots[0].windows[1].layoutBackend).toBe("tmux");
    expect(serialized).toContain("layoutBackend: tmux");
    expect(serialized).toContain("layoutBackend: direct");
    expect(serialized).toContain("windows:");
  });
});
