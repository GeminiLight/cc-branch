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
  session_intent?: "auto" | "fresh" | "explicit" | string;
  session_binding_status?:
    | "none"
    | "bound"
    | "fresh"
    | "will_create"
    | "pending_capture"
    | "ambiguous"
    | string;
  session_binding_source?: string | null;
  session_binding_updated_at?: string | null;
  label: string | null;
  cwd: string;
  status?: "running" | "stopped" | "external";
  sync_status?: SyncStatus;
  needs_restart?: boolean;
}

export interface SlotInfo {
  name: string;
  runtime: string;
  layout?: string;
  split_group?: string | null;
  status: "running" | "stopped" | "external";
  session_name: string;
  windows: WindowInfo[];
  sync_status?: SyncStatus;
  extra_windows?: RuntimeSyncWindow[];
}

export type SyncStatus = "current" | "changed" | "missing" | "extra" | "orphaned" | "untracked" | "external";

export interface RuntimeSyncWindow {
  name: string;
  key: string;
  runtime_status: string;
  sync_status: SyncStatus;
  needs_restart: boolean;
  desired_fingerprint?: string | null;
  applied_fingerprint?: string | null;
  change_reason: string[];
}

export interface RuntimeSyncSlot {
  name: string;
  runtime: string;
  tmux_session: string;
  sync_status: SyncStatus;
  windows: RuntimeSyncWindow[];
  extra_windows: RuntimeSyncWindow[];
}

export interface RuntimeSyncReport {
  summary: Record<SyncStatus, number>;
  slots: RuntimeSyncSlot[];
  orphaned_state: Record<string, unknown>[];
  historical_sessions: Record<string, unknown>[];
}

export interface ConfigIssue {
  issue_type: string;
  severity: "error" | "warning" | "info";
  message: string;
  target: string;
  context: Record<string, unknown>;
  fixable: boolean;
}

export interface WorkspaceStatus {
  status?: "ready" | "needs_init" | "missing" | "invalid_config";
  project?: string;
  project_path?: string;
  project_name?: string;
  config_path: string;
  state_path: string;
  slots: SlotInfo[];
  runtimes?: RuntimeAvailability;
  runtime_sync?: RuntimeSyncReport;
  error?: string;
}

export interface WorkspaceScope {
  projectPath?: string;
  configPath?: string;
}

export interface ConfigOption {
  id: string;
  label: string;
  path: string;
  state_path: string;
  exists: boolean;
  is_default: boolean;
  selected: boolean;
}

export interface ConfigOptionsData {
  project_path: string;
  default_config_path: string;
  selected_config_path: string;
  state_path: string;
  configs: ConfigOption[];
}

export interface ConfigData {
  status?: "ready" | "needs_init" | "missing";
  content: string;
  path: string;
  project_path?: string;
  state_path?: string;
  mtime?: number | null;
  content_hash?: string;
  issues?: ConfigIssue[];
  runtimes?: RuntimeAvailability;
}

export interface RuntimeAvailability {
  tmux?: RuntimeAvailabilityEntry;
  terminal?: RuntimeAvailabilityEntry;
}

export interface RuntimeAvailabilityEntry {
  available: boolean;
  reason?: string;
}

export interface ConfigSaveResult {
  success: boolean;
  path: string;
  mtime?: number | null;
  content_hash?: string;
  diagnostics?: string;
  issues?: ConfigIssue[];
}

export type DoctorIssue = ConfigIssue;

export interface DoctorReportPayload {
  project: string;
  issues: DoctorIssue[];
  has_errors?: boolean;
  has_warnings?: boolean;
}

export interface DoctorReport {
  status?: "ready" | "needs_init" | "missing" | "invalid_config";
  report: string | DoctorReportPayload;
  text?: string;
  error?: string;
}

export interface ActionResult {
  success: boolean;
  message: string;
}

export type WorkspaceAction = "launch" | "restart" | "stop" | "open" | "sync" | "prune_state";
export type OpenIntent = "workspace_dashboard" | "attach_target" | "project_folder";

export interface WorkspaceActionRequest {
  action: WorkspaceAction;
  target?: string;
  opener?: string;
  intent?: OpenIntent;
  projectPath?: string;
  configPath?: string;
  stopRemoved?: boolean;
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

export interface AgentProfileInfo {
  id: string;
  command: string;
  install_hint?: string;
  resume_mode: string;
  resume_template: string;
  create_mode: string;
  create_template: string;
  label_template: string;
  label_mode: string;
  rename_template: string;
}

export interface AgentsData {
  agents: AgentProfileInfo[];
}

export interface AgentSessionInfo {
  agent: string;
  id: string;
  label: string;
  updated_at?: string | null;
  source?: string | null;
  project_path?: string | null;
}

export interface AgentSessionsData {
  sessions: AgentSessionInfo[];
}

export interface GlobalAgentsData {
  path: string;
  exists: boolean;
  content: string;
  mtime?: number | null;
  content_hash?: string;
  agents: AgentProfileInfo[];
}

export interface GlobalAgentsSaveResult extends GlobalAgentsData {
  success: boolean;
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

export interface GlobalProjectItem {
  id: string;
  name: string;
  path: string;
  selected_config_path?: string;
}

export interface ProjectsIndexData {
  version: number;
  active_project_id: string | null;
  projects: GlobalProjectItem[];
  storage_path: string;
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
