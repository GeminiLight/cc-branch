/**
 * API types shared between frontend and backend.
 *
 * These types define the contract between the React UI and the
 * cc-branch HTTP API (or Tauri IPC shim).
 */

export interface WindowInfo {
  name: string;
  enabled?: boolean;
  agent: string | null;
  command: string;
  session_id: string | null;
  session_intent?: "auto" | "fresh" | "explicit" | string;
  session_binding_status?:
    | "none"
    | "bound"
    | "fresh"
    | "will_bootstrap"
    | "will_capture"
    | "will_create"
    | "pending_capture"
    | "ambiguous"
    | string;
  session_binding_source?: string | null;
  session_binding_updated_at?: string | null;
  session_hook_event?: "started" | "updated" | "exited" | "error" | string | null;
  session_hook_updated_at?: string | null;
  session_runtime_status?: "running" | "stopped" | "failed" | string | null;
  session_transcript_path?: string | null;
  session_pid?: number | null;
  session_exit_code?: number | null;
  label: string | null;
  cwd: string;
  status?: "running" | "stopped" | "external" | "disabled";
  sync_status?: SyncStatus;
  needs_restart?: boolean;
}

export interface WorkspaceAgentActivity {
  summary?: string | null;
  source?: "tmux" | "transcript" | string | null;
  path?: string | null;
}

export interface WorkspaceAgentInbox {
  unread: number;
  last_message?: string | null;
  updated_at?: string | null;
}

export interface AgentWorktreeStatus {
  target: string;
  path: string;
  branch?: string | null;
  status?: string;
  dirty?: boolean;
  changed_files?: number;
}

export interface WorkspaceAgentRemote {
  host: string;
  user?: string | null;
  port?: number | null;
  cwd?: string | null;
  target: string;
}

export interface WorkspaceAgentStatus {
  target: string;
  name: string;
  agent: string;
  cli: string;
  command: string;
  location: "local" | "ssh" | string;
  remote?: WorkspaceAgentRemote | null;
  cwd: string;
  runtime: string;
  slot: string;
  window: string;
  tmux_session?: string | null;
  tmux_window?: string | null;
  session_id?: string | null;
  transcript_path?: string | null;
  status: "busy" | "idle" | "stopped" | "stale" | "error" | "external" | "disabled" | string;
  activity?: WorkspaceAgentActivity;
  inbox?: WorkspaceAgentInbox;
  worktree?: AgentWorktreeStatus | null;
  actions?: string[];
}

export interface AgentBusEvent {
  id?: string;
  timestamp?: string;
  type: string;
  sender?: string;
  target?: string;
  message?: string;
  delivery?: string;
  status?: string;
  read?: boolean;
}

export interface AgentBusData {
  events: AgentBusEvent[];
  inbox: AgentBusEvent[];
  storage_path: string;
}

export interface WorkspaceSnapshot {
  id: string;
  name: string;
  created_at?: string;
  project?: string;
  config_path?: string;
  state_path?: string;
  git?: Record<string, unknown>;
}

export interface WorkspaceSnapshotsData {
  snapshots: WorkspaceSnapshot[];
}

export interface SessionRestoreRequest {
  target?: string;
  agent?: string;
  sessionId?: string;
  sessionScope?: "project" | "all";
  dryRun?: boolean;
  force?: boolean;
  limit?: number;
}

export interface CreateSnapshotOptions {
  includeFiles?: boolean;
}

export interface RestoreSnapshotOptions {
  restoreFiles?: boolean;
}

export interface WorktreesData {
  worktrees: AgentWorktreeStatus[];
}

export interface WorktreeSetupRequest {
  target: string;
  path?: string;
  branch?: string;
  base?: string;
  copy?: string[];
  symlink?: string[];
  setup_hook?: string;
}

export interface SlotInfo {
  name: string;
  runtime: string;
  layout?: string;
  split_group?: string | null;
  status: "running" | "stopped" | "external" | "disabled";
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
  agents?: WorkspaceAgentStatus[];
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

export interface DiagnosticBundle {
  kind: "cc-branch-diagnostic-bundle";
  generated_at: string;
  app: Record<string, unknown>;
  backend: Record<string, unknown>;
  schema: Record<string, unknown>;
  project: Record<string, unknown>;
  files: Record<string, unknown>;
  doctor: DoctorReport;
  logs: Record<string, unknown>;
}

export interface ActionResult {
  success: boolean;
  message: string;
  code?: string;
  changed_targets?: string[];
  warnings?: string[];
}

export interface WindowEnabledRequest {
  target: string;
  enabled: boolean;
  projectPath?: string;
  configPath?: string;
}

export type WorkspaceAction = "launch" | "restart" | "stop" | "open" | "send" | "sync" | "prune_state";
export type OpenIntent = "workspace_dashboard" | "attach_target" | "project_folder";

export interface WorkspaceActionRequest {
  action: WorkspaceAction;
  target?: string;
  opener?: string;
  intent?: OpenIntent;
  message?: string;
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

export interface OpenerConfigInfo {
  id: string;
  label: string;
  kind: "terminal" | "editor";
  command: string;
  args: string[];
  capabilities: string[];
}

export interface GlobalOpenersData {
  path: string;
  exists: boolean;
  content: string;
  mtime?: number | null;
  content_hash?: string;
  openers: OpenerInfo[];
  user_openers: OpenerConfigInfo[];
}

export interface GlobalOpenersSaveResult extends GlobalOpenersData {
  success: boolean;
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
  scope?: "project" | "all" | string;
  sessions: AgentSessionInfo[];
}

export interface GlobalAgentsData {
  path: string;
  exists: boolean;
  content: string;
  mtime?: number | null;
  content_hash?: string;
  agents: AgentProfileInfo[];
  builtin_agents?: AgentProfileInfo[];
  user_agents?: AgentProfileInfo[];
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

export interface RemoteProjectInput {
  host: string;
  user?: string | null;
  port?: number | null;
  cwd: string;
  args?: string[];
  options?: Record<string, unknown>;
}

export interface RemoteDirectoryEntry {
  name: string;
  path: string;
  hidden?: boolean;
}

export interface RemoteDirectoryListing {
  path: string;
  parent?: string | null;
  entries: RemoteDirectoryEntry[];
  truncated?: boolean;
}

export interface AddProjectRequest {
  path?: string;
  name?: string;
  agent?: string;
  remote?: RemoteProjectInput;
}

export interface GlobalProjectItem {
  id: string;
  name: string;
  path: string;
  display_path?: string;
  remote?: RemoteProjectInput;
  pinned?: boolean;
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

export interface SshHostInfo {
  alias: string;
  hostname?: string;
  user?: string;
  port?: number;
}

export interface ApiInfo {
  port: number;
  config_path: string;
  state_path: string;
  desktop_version?: string;
  desktop_platform?: string;
  desktop_arch?: string;
  backend_source?: string;
  backend_scope?: "project" | "app" | string;
  backend_ready?: boolean;
  startup_error?: string | null;
  default_shell?: string;
  ssh_hosts?: SshHostInfo[];
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
