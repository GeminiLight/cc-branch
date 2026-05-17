import { describe, expect, it } from "vitest";
import YAML from "js-yaml";
import {
  cloneTemplate,
  configDataForTemplate,
  projectNameFromPath,
  selectedAgentForPane,
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

    expect(data.openWith).toBe("auto-terminal");
    expect(data.display.dashboard).toBe(true);
    expect(data.slots[0].runtime).toBe("tmux");
    expect(data.slots[0].windows.map((pane) => pane.agent)).toEqual(["claude", "claude"]);
    expect(data.slots[1].runtime).toBe("terminal");
    expect(data.slots[1].windows[0].command).toBe("$SHELL");
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
