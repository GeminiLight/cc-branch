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
  name?: string;
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
        layoutBackend: "direct",
        panes: [
          { name: "frontend", preferredAgents: ["codex", "claude", "gemini"] },
          { name: "backend", preferredAgents: ["codex", "claude", "gemini"] },
          { name: "algorithm", preferredAgents: ["claude", "gemini", "codex"] },
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
const USER_TEMPLATES_STORAGE_KEY = "cc-branch-user-templates";

export function isBuiltInTemplateId(id: string): id is typeof profileOrder[number] {
  return (profileOrder as readonly string[]).includes(id);
}

export function effectiveTemplateSpecs(userTemplates: TemplateSpec[] = []): Record<string, TemplateSpec> {
  const specs: Record<string, TemplateSpec> = { ...templateSpecs };
  for (const template of userTemplates) {
    specs[template.id] = template;
  }
  return specs;
}

export function customProfileTemplates(userTemplates: TemplateSpec[] = []): TemplateSpec[] {
  return userTemplates.filter((template) => !isBuiltInTemplateId(template.id));
}

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

function directWindowForPane(pane: PreviewPane, availableAgents: string[]): WindowConfig {
  return {
    ...windowForPane(pane, availableAgents),
    layoutBackend: "direct",
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
      windows: tab.panes.length > 0
        ? tab.panes.map((pane) => directWindowForPane(pane, availableAgents))
        : [shellWindow(tab.name)],
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
    openWith: "vscode",
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
      panes: stats.panes + Math.max(tab.panes.length, 1),
      tmuxTabs: stats.tmuxTabs + (tab.layoutBackend === "tmux" ? 1 : 0),
      directTabs: stats.directTabs + (tab.layoutBackend === "direct" ? 1 : 0),
    }),
    { tabs: 0, panes: 0, tmuxTabs: 0, directTabs: 0 }
  );
}

export function cloneTemplate(spec: TemplateSpec): TemplateSpec {
  return {
    id: spec.id,
    ...(spec.name ? { name: spec.name } : {}),
    tabs: spec.tabs.map((tab) => ({
      ...tab,
      panes: tab.panes.map((pane) => ({ ...pane, preferredAgents: [...pane.preferredAgents] })),
    })),
  };
}

function isPreviewPane(value: unknown): value is PreviewPane {
  const pane = value as PreviewPane;
  return Boolean(
    pane &&
    typeof pane.name === "string" &&
    Array.isArray(pane.preferredAgents) &&
    pane.preferredAgents.every((agent) => typeof agent === "string")
  );
}

function isPreviewTab(value: unknown): value is PreviewTab {
  const tab = value as PreviewTab;
  return Boolean(
    tab &&
    typeof tab.name === "string" &&
    (tab.layoutBackend === "tmux" || tab.layoutBackend === "direct") &&
    Array.isArray(tab.panes) &&
    tab.panes.every(isPreviewPane)
  );
}

export function sanitizeUserTemplate(value: unknown): TemplateSpec | null {
  const spec = value as TemplateSpec;
  if (!spec || typeof spec.id !== "string" || !spec.id.trim() || !Array.isArray(spec.tabs) || spec.tabs.length === 0) {
    return null;
  }
  if (!spec.tabs.every(isPreviewTab)) return null;
  return cloneTemplate({
    id: spec.id.trim(),
    ...(typeof spec.name === "string" && spec.name.trim() ? { name: spec.name.trim() } : {}),
    tabs: spec.tabs,
  });
}

export function loadUserTemplates(): TemplateSpec[] {
  if (typeof localStorage === "undefined") return [];
  try {
    const raw = localStorage.getItem(USER_TEMPLATES_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    return parsed.map(sanitizeUserTemplate).filter((item): item is TemplateSpec => Boolean(item));
  } catch {
    return [];
  }
}

export function saveUserTemplates(templates: TemplateSpec[]): void {
  if (typeof localStorage === "undefined") return;
  const cleaned = templates.map(sanitizeUserTemplate).filter((item): item is TemplateSpec => Boolean(item));
  localStorage.setItem(USER_TEMPLATES_STORAGE_KEY, JSON.stringify(cleaned));
}
