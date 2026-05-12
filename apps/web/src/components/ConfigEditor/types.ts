/**
 * ConfigEditor — form data types.
 *
 * Mirrors the .cc-branch/config.yaml schema for structured editing.
 */

export interface AgentConfig {
  command: string;
  resume_mode: "none" | "flag" | "internal";
  resume_template: string;
  create_mode: "none" | "generated_uuid";
  create_template: string;
  label_template: string;
  label_mode: "metadata" | "internal";
  rename_template: string;
}

export interface WindowConfig {
  name: string;
  agent: string | null;
  command: string | null;
  cwd: string | null;
  env: Record<string, string>;
  session_id: string | null;
  label: string | null;
  label_template: string | null;
  resume_mode: string | null;
  resume_template: string | null;
  create_mode: string | null;
  create_template: string | null;
  label_mode: string | null;
  rename_template: string | null;
}

export interface SlotConfig {
  name: string;
  runtime: "tmux" | "terminal";
  layout?: "auto" | "horizontal" | "vertical" | "main-left" | "main-top" | "grid";
  opener?: string;
  cwd: string;
  env: Record<string, string>;
  windows: WindowConfig[];
  // Single-window runtime fields
  command?: string;
  title?: string;
  agent?: string;
  session_id?: string;
  label?: string;
}

export interface DisplayConfig {
  mode: "grid" | "list";
  columns: number;
  dashboard: boolean;
}

export interface ConfigFormData {
  version: number;
  project: string;
  root: string;
  display: DisplayConfig;
  agents: Record<string, AgentConfig>;
  slots: SlotConfig[];
}

export const DEFAULT_AGENT: AgentConfig = {
  command: "",
  resume_mode: "none",
  resume_template: "",
  create_mode: "none",
  create_template: "",
  label_template: "",
  label_mode: "metadata",
  rename_template: "",
};

export const DEFAULT_WINDOW: WindowConfig = {
  name: "",
  agent: null,
  command: null,
  cwd: null,
  env: {},
  session_id: null,
  label: null,
  label_template: null,
  resume_mode: null,
  resume_template: null,
  create_mode: null,
  create_template: null,
  label_mode: null,
  rename_template: null,
};

export const DEFAULT_SLOT: SlotConfig = {
  name: "",
  runtime: "tmux",
  cwd: ".",
  env: {},
  windows: [{ ...DEFAULT_WINDOW, name: "main" }],
};

export const DEFAULT_DISPLAY: DisplayConfig = {
  mode: "grid",
  columns: 2,
  dashboard: false,
};

export function createDefaultConfig(): ConfigFormData {
  return {
    version: 2,
    project: "my-project",
    root: ".",
    display: { ...DEFAULT_DISPLAY },
    agents: {},
    slots: [],
  };
}
