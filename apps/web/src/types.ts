/**
 * API types shared between frontend and backend.
 *
 * These types define the contract between the React UI and the
 * cc-branch HTTP API (or Tauri IPC shim).
 */

export interface WindowInfo {
  name: string;
  agent: string | null;
  command: string;
  session_id: string | null;
  label: string | null;
  cwd: string;
}

export interface SlotInfo {
  name: string;
  backend: string;
  status: "running" | "stopped";
  session_name: string;
  windows: WindowInfo[];
}

export interface WorkspaceStatus {
  status?: "ready" | "needs_init" | "missing" | "invalid_config";
  project?: string;
  project_path?: string;
  project_name?: string;
  config_path: string;
  state_path: string;
  slots: SlotInfo[];
  error?: string;
}

export interface ConfigData {
  status?: "ready" | "needs_init" | "missing";
  content: string;
  path: string;
  project_path?: string;
  state_path?: string;
}

export interface DoctorReport {
  status?: "ready" | "needs_init" | "missing" | "invalid_config";
  report: string;
  error?: string;
}

export interface ActionResult {
  success: boolean;
  message: string;
}

export type WorkspaceAction = "launch" | "restart" | "stop" | "open";
export type OpenIntent = "workspace_dashboard" | "attach_target" | "project_folder";

export interface WorkspaceActionRequest {
  action: WorkspaceAction;
  target?: string;
  opener?: string;
  intent?: OpenIntent;
  projectPath?: string;
}

export interface OpenerInfo {
  id: string;
  label: string;
  kind: "terminal" | "editor";
  available: boolean;
  capabilities: string[];
  source: string;
  executable?: string;
  reason?: string;
}

export interface OpenersData {
  default: string;
  openers: OpenerInfo[];
}

export interface ProjectProbe {
  path: string;
  path_exists: boolean;
  config_exists: boolean;
  state_exists: boolean;
  project_name: string;
  slots: number;
  status: "missing" | "needs_init" | "invalid_config" | "ready";
}

export interface APIError {
  error: string;
}

export interface ApiInfo {
  port: number;
  config_path: string;
  state_path: string;
}

export interface Profile {
  id: string;
  description: string;
}

export interface InitResult {
  success: boolean;
  config_path: string;
  state_path: string;
  summary: { slots: number; windows: number; agents: number };
  agents_detected: string[];
  gitignore_created: boolean;
  gitignore_updated: boolean;
}
