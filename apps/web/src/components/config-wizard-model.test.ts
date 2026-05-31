import { describe, expect, it } from "vitest";
import YAML from "js-yaml";
import {
  cloneTemplate,
  configDataForTemplate,
  loadUserTemplates,
  projectNameFromPath,
  saveUserTemplates,
  selectedAgentForPane,
  templateSpecs,
  templateStats,
  yamlForTemplate,
  type TemplateSpec,
} from "./config-wizard-model";
import { parseConfigYaml } from "./ConfigEditor/yaml-utils";

const mixedSpec: TemplateSpec = {
  id: "mixed",
  tabs: [
    {
      name: 'dev "main"',
      layoutBackend: "tmux",
      panes: [
        { name: "frontend:ui", preferredAgents: ["codex", "claude"] },
        { name: "docs #1", preferredAgents: ["claude"] },
      ],
    },
    {
      name: "scratch",
      layoutBackend: "direct",
      panes: [],
    },
  ],
};

describe("config wizard model", () => {
  it("persists custom templates for the template center", () => {
    localStorage.clear();
    const custom = {
      ...cloneTemplate(templateSpecs.minimal),
      id: "custom-review",
      name: "Review loop",
    };

    saveUserTemplates([custom]);

    expect(loadUserTemplates()).toEqual([custom]);
  });

  it("derives a stable project name from paths", () => {
    expect(projectNameFromPath("/Users/me/code/cli-workspace/")).toBe("cli-workspace");
    expect(projectNameFromPath("C:\\Users\\me\\repo")).toBe("repo");
    expect(projectNameFromPath()).toBe("workspace");
  });

  it("selects available preferred agents before falling back", () => {
    expect(selectedAgentForPane({ name: "x", preferredAgents: ["codex", "claude"] }, ["claude"])).toBe("claude");
    expect(selectedAgentForPane({ name: "x", preferredAgents: ["codex"] }, [])).toBe("codex");
    expect(selectedAgentForPane({ name: "x", preferredAgents: ["codex"], agent: "gemini" }, ["codex"])).toBe("gemini");
  });

  it("counts direct tabs as one pane and tmux tabs by configured panes", () => {
    expect(templateStats(mixedSpec)).toEqual({
      tabs: 2,
      panes: 3,
      tmuxTabs: 1,
      directTabs: 1,
    });
  });

  it("clones templates without sharing nested pane arrays", () => {
    const cloned = cloneTemplate(mixedSpec);
    cloned.tabs[0].panes[0].preferredAgents.push("gemini");

    expect(mixedSpec.tabs[0].panes[0].preferredAgents).toEqual(["codex", "claude"]);
  });

  it("builds config data through the same model used by the editor", () => {
    const data = configDataForTemplate(mixedSpec, "demo", ["claude"]);

    expect(data.openWith).toBe("vscode");
    expect(data.display.dashboard).toBe(true);
    expect(data.slots[0].runtime).toBe("tmux");
    expect(data.slots[0].windows.map((pane) => pane.agent)).toEqual(["claude", "claude"]);
    expect(data.slots[1].runtime).toBe("terminal");
    expect(data.slots[1].windows[0].command).toBe("$SHELL");
  });

  it("fills the default development workspace with four Codex panes when Codex is the detected agent", () => {
    const data = configDataForTemplate(templateSpecs.development, "demo", ["codex"]);

    expect(data.slots[0].runtime).toBe("terminal");
    expect(data.slots[0].windows.map((pane) => pane.name)).toEqual(["frontend", "backend", "algorithm", "docs"]);
    expect(data.slots[0].windows.map((pane) => pane.layoutBackend)).toEqual(["direct", "direct", "direct", "direct"]);
    expect(data.slots[0].windows.map((pane) => pane.agent)).toEqual(["codex", "codex", "codex", "codex"]);
  });

  it("fills the default development workspace with four Claude panes when Claude is the detected agent", () => {
    const data = configDataForTemplate(templateSpecs.development, "demo", ["claude"]);

    expect(data.slots[0].windows.map((pane) => pane.name)).toEqual(["frontend", "backend", "algorithm", "docs"]);
    expect(data.slots[0].windows.map((pane) => pane.agent)).toEqual(["claude", "claude", "claude", "claude"]);
  });

  it("splits the default development workspace across Codex and Claude when both are detected", () => {
    const data = configDataForTemplate(templateSpecs.development, "demo", ["codex", "claude"]);

    expect(data.slots[0].windows.map((pane) => pane.name)).toEqual(["frontend", "backend", "algorithm", "docs"]);
    expect(data.slots[0].windows.map((pane) => pane.agent)).toEqual(["codex", "codex", "claude", "claude"]);
  });

  it("serializes the default development workspace as one direct tab with four parallel panes", () => {
    const yaml = yamlForTemplate(templateSpecs.development, "demo", ["codex", "claude"]);
    const raw = YAML.load(yaml) as {
      tabs?: Array<{ name?: string; layoutBackend?: string; panes?: Array<Record<string, unknown>> }>;
    };

    expect(raw.tabs).toHaveLength(1);
    expect(raw.tabs?.[0]?.name).toBe("development");
    expect(raw.tabs?.[0]?.layoutBackend).toBeUndefined();
    expect(raw.tabs?.[0]?.panes?.map((pane) => pane.name)).toEqual(["frontend", "backend", "algorithm", "docs"]);
    expect(raw.tabs?.[0]?.panes?.map((pane) => pane.agent)).toEqual(["codex", "codex", "claude", "claude"]);
    expect(raw.tabs?.[0]?.panes?.some((pane) => "windows" in pane)).toBe(false);
  });

  it("serializes valid YAML even when names contain YAML-sensitive characters", () => {
    const yaml = yamlForTemplate(mixedSpec, 'demo: "quoted"', ["claude"]);
    const raw = YAML.load(yaml) as Record<string, unknown>;
    const parsed = parseConfigYaml(yaml);

    expect(raw.project).toBe('demo: "quoted"');
    expect(parsed.project).toBe('demo: "quoted"');
    expect(parsed.slots[0].name).toBe('dev "main"');
    expect(parsed.slots[0].windows[0].name).toBe("frontend:ui");
    expect(parsed.slots[1].windows[0].command).toBe("$SHELL");
  });
});
