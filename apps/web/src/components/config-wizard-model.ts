import { DEFAULT_WINDOW, type ConfigFormData, type SlotConfig, type WindowConfig } from "./ConfigEditor/types";
import { serializeConfigForm } from "./ConfigEditor/yaml-utils";

export interface PreviewPane {
  name: string;
  preferredAgents: string[];
  agent?: string;
}

export interface PreviewTab {
  name: string;
  layoutBackend: "tmux" | "direct";
  panes: PreviewPane[];
}

export interface TemplateSpec {
  id: string;
  tabs: PreviewTab[];
}

export interface TemplateStats {
  tabs: number;
  panes: number;
  tmuxTabs: number;
  directTabs: number;
}

export const templateSpecs: Record<string, TemplateSpec> = {
  development: {
    id: "development",
    tabs: [
      {
        name: "development",
        layoutBackend: "tmux",
        panes: [
          { name: "frontend", preferredAgents: ["codex", "claude", "gemini"] },
          { name: "backend", preferredAgents: ["codex", "gemini", "claude"] },
          { name: "algorithm", preferredAgents: ["gemini", "codex", "claude"] },
          { name: "docs", preferredAgents: ["claude", "gemini", "codex"] },
        ],
      },
    ],
  },
  design: {
    id: "design",
    tabs: [
      {
        name: "product",
        layoutBackend: "tmux",
        panes: [
          { name: "discussion", preferredAgents: ["claude", "gemini", "codex"] },
          { name: "implementation", preferredAgents: ["codex", "claude", "gemini"] },
        ],
      },
      {
        name: "design",
        layoutBackend: "tmux",
        panes: [
          { name: "directions", preferredAgents: ["claude", "gemini", "codex"] },
          { name: "review", preferredAgents: ["claude", "codex", "gemini"] },
        ],
      },
    ],
  },
  minimal: {
    id: "minimal",
    tabs: [
      {
        name: "main",
        layoutBackend: "tmux",
        panes: [
          { name: "agent", preferredAgents: ["codex", "claude", "gemini"] },
        ],
      },
    ],
  },
};

export const profileOrder = ["development", "design", "minimal"] as const;
export const defaultProfileId = "development";

export function projectNameFromPath(projectPath?: string): string {
  return projectPath?.split(/[\\/]/).filter(Boolean).pop() || "workspace";
}

export function agentForPane(pane: PreviewPane, availableAgents: string[]): string {
  return pane.preferredAgents.find((agent) => availableAgents.includes(agent)) || pane.preferredAgents[0] || "shell";
}

export function selectedAgentForPane(pane: PreviewPane, availableAgents: string[]): string {
  return pane.agent || agentForPane(pane, availableAgents);
}

function windowForPane(pane: PreviewPane, availableAgents: string[]): WindowConfig {
  return {
    ...DEFAULT_WINDOW,
    name: pane.name,
    agent: selectedAgentForPane(pane, availableAgents),
    env: {},
  };
}

function shellWindow(name: string): WindowConfig {
  return {
    ...DEFAULT_WINDOW,
    name,
    layoutBackend: "direct",
    command: "$SHELL",
    env: {},
  };
}

function slotForTab(tab: PreviewTab, availableAgents: string[]): SlotConfig {
  if (tab.layoutBackend === "direct") {
    return {
      name: tab.name,
      runtime: "terminal",
      layout: "auto",
      cwd: ".",
      env: {},
      windows: [shellWindow(tab.name)],
    };
  }

  return {
    name: tab.name,
    runtime: "tmux",
    layout: "auto",
    cwd: ".",
    env: {},
    windows: tab.panes.map((pane) => windowForPane(pane, availableAgents)),
  };
}

export function configDataForTemplate(
  spec: TemplateSpec,
  projectName: string,
  availableAgents: string[]
): ConfigFormData {
  return {
    version: 2,
    project: projectName,
    root: ".",
    openWith: "auto-terminal",
    layoutBackend: "direct",
    defaults: { shell: null },
    display: { mode: "grid", columns: 2, dashboard: true },
    agents: {},
    slots: spec.tabs.map((tab) => slotForTab(tab, availableAgents)),
  };
}

export function yamlForTemplate(spec: TemplateSpec, projectName: string, availableAgents: string[]): string {
  return serializeConfigForm(configDataForTemplate(spec, projectName, availableAgents));
}

export function templateStats(spec: TemplateSpec): TemplateStats {
  return spec.tabs.reduce(
    (stats, tab) => ({
      tabs: stats.tabs + 1,
      panes: stats.panes + (tab.layoutBackend === "direct" ? 1 : Math.max(tab.panes.length, 1)),
      tmuxTabs: stats.tmuxTabs + (tab.layoutBackend === "tmux" ? 1 : 0),
      directTabs: stats.directTabs + (tab.layoutBackend === "direct" ? 1 : 0),
    }),
    { tabs: 0, panes: 0, tmuxTabs: 0, directTabs: 0 }
  );
}

export function cloneTemplate(spec: TemplateSpec): TemplateSpec {
  return {
    id: spec.id,
    tabs: spec.tabs.map((tab) => ({
      ...tab,
      panes: tab.panes.map((pane) => ({ ...pane, preferredAgents: [...pane.preferredAgents] })),
    })),
  };
}
