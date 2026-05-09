/**
 * API client layer.
 *
 * Supports two backends:
 * - HTTPClient   : talks to cc-branch serve over HTTP
 * - TauriClient  : talks to Tauri Rust backend over IPC
 */

import type {
  WorkspaceStatus,
  ConfigData,
  DoctorReport,
  ActionResult,
  ProjectProbe,
  Profile,
  InitResult,
  WorkspaceAction,
  WorkspaceActionRequest,
  OpenersData,
  AgentsData,
  ConfigSaveResult,
  ConfigIssue,
  ConfigOptionsData,
  WorkspaceScope,
} from "../types";

export interface APIClient {
  getStatus(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<WorkspaceStatus>;
  getConfig(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<ConfigData>;
  getConfigs(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<ConfigOptionsData>;
  getDoctor(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<DoctorReport>;
  probeProject(projectPath: string, signal?: AbortSignal): Promise<ProjectProbe>;
  getOpeners(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<OpenersData>;
  getAgents(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<AgentsData>;
  runAction(action: WorkspaceAction, target?: string, scope?: WorkspaceScope | string): Promise<ActionResult>;
  runWorkspaceAction(request: WorkspaceActionRequest): Promise<ActionResult>;
  stopSlot(sessionName: string, scope?: WorkspaceScope | string): Promise<ActionResult>;
  getApiInfo(signal?: AbortSignal): Promise<{ port: number; config_path: string; state_path: string }>;
  getProfiles(signal?: AbortSignal): Promise<Profile[]>;
  initWorkspace(profile: string, bootstrapSessions: boolean, scope?: WorkspaceScope | string): Promise<InitResult>;
  saveConfig(
    content: string,
    scope?: WorkspaceScope | string,
    baseMtime?: number | null,
    baseContentHash?: string | null
  ): Promise<ConfigSaveResult>;
}

export class APIRequestError extends Error {
  status: number;
  code?: string;
  currentContent?: string;
  issues?: ConfigIssue[];

  constructor(status: number, data: Record<string, unknown>) {
    super(String(data.error || `HTTP ${status}`));
    this.name = "APIRequestError";
    this.status = status;
    this.code = typeof data.code === "string" ? data.code : undefined;
    this.currentContent = typeof data.current_content === "string" ? data.current_content : undefined;
    this.issues = Array.isArray(data.issues) ? (data.issues as ConfigIssue[]) : undefined;
  }
}

function normalizeScope(scope?: WorkspaceScope | string): WorkspaceScope {
  if (!scope) return {};
  if (typeof scope === "string") return { projectPath: scope };
  return scope;
}

function qs(scope?: WorkspaceScope | string): string {
  const { projectPath, configPath } = normalizeScope(scope);
  const params = new URLSearchParams();
  if (projectPath) params.set("project_path", projectPath);
  if (configPath) params.set("config_path", configPath);
  const query = params.toString();
  return query ? `?${query}` : "";
}

/**
 * HTTP implementation — used by the web UI (cc-branch serve).
 */
export class HTTPClient implements APIClient {
  private baseUrl: string;

  constructor(baseUrl: string = "") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async getStatus(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<WorkspaceStatus> {
    const res = await fetch(`${this.baseUrl}/api/status${qs(scope)}`, { signal });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as WorkspaceStatus;
  }

  async getConfig(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<ConfigData> {
    const res = await fetch(`${this.baseUrl}/api/config${qs(scope)}`, { signal });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigData;
  }

  async getConfigs(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<ConfigOptionsData> {
    const res = await fetch(`${this.baseUrl}/api/configs${qs(scope)}`, { signal });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigOptionsData;
  }

  async getDoctor(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<DoctorReport> {
    const res = await fetch(`${this.baseUrl}/api/doctor${qs(scope)}`, { signal });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as DoctorReport;
  }

  async probeProject(projectPath: string, signal?: AbortSignal): Promise<ProjectProbe> {
    const res = await fetch(`${this.baseUrl}/api/project/probe${qs(projectPath)}`, { signal });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectProbe;
  }

  async getOpeners(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<OpenersData> {
    const res = await fetch(`${this.baseUrl}/api/openers${qs(scope)}`, { signal });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as OpenersData;
  }

  async getAgents(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<AgentsData> {
    const res = await fetch(`${this.baseUrl}/api/agents${qs(scope)}`, { signal });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as AgentsData;
  }

  async runAction(action: WorkspaceAction, target?: string, scope?: WorkspaceScope | string): Promise<ActionResult> {
    return this.runWorkspaceAction({ action, target, ...normalizeScope(scope) });
  }

  async runWorkspaceAction(request: WorkspaceActionRequest): Promise<ActionResult> {
    const { projectPath, configPath, stopRemoved, ...body } = request;
    const res = await fetch(`${this.baseUrl}/api/action${qs({ projectPath, configPath })}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, stop_removed: stopRemoved }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ActionResult;
  }

  async stopSlot(sessionName: string, scope?: WorkspaceScope | string): Promise<ActionResult> {
    return this.runAction("stop", sessionName, scope);
  }

  async getApiInfo(signal?: AbortSignal): Promise<{ port: number; config_path: string; state_path: string }> {
    const res = await fetch(`${this.baseUrl}/api/info`, { signal });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as { port: number; config_path: string; state_path: string };
  }

  async getProfiles(signal?: AbortSignal): Promise<Profile[]> {
    const res = await fetch(`${this.baseUrl}/api/profiles`, { signal });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data.profiles as Profile[];
  }

  async initWorkspace(profile: string, bootstrapSessions: boolean, scope?: WorkspaceScope | string): Promise<InitResult> {
    const res = await fetch(`${this.baseUrl}/api/init${qs(scope)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile, bootstrap_sessions: bootstrapSessions }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as InitResult;
  }

  async saveConfig(
    content: string,
    scope?: WorkspaceScope | string,
    baseMtime?: number | null,
    baseContentHash?: string | null
  ): Promise<ConfigSaveResult> {
    const res = await fetch(`${this.baseUrl}/api/config${qs(scope)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        base_mtime: baseMtime,
        base_content_hash: baseContentHash,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new APIRequestError(res.status, data);
    return data as ConfigSaveResult;
  }
}

/**
 * Tauri IPC implementation — used by the desktop app.
 */
export class TauriClient implements APIClient {
  private async _invoke(cmd: string, args?: Record<string, unknown>): Promise<unknown> {
    const tauri = await import("@tauri-apps/api/core");
    return tauri.invoke(cmd, args);
  }

  private async _baseUrl(): Promise<string> {
    const info = await this.getApiInfo();
    return `http://127.0.0.1:${info.port}`;
  }

  async getStatus(scope?: WorkspaceScope | string): Promise<WorkspaceStatus> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/status${qs(scope)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as WorkspaceStatus;
  }

  async getConfig(scope?: WorkspaceScope | string): Promise<ConfigData> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/config${qs(scope)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigData;
  }

  async getConfigs(scope?: WorkspaceScope | string): Promise<ConfigOptionsData> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/configs${qs(scope)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigOptionsData;
  }

  async getDoctor(scope?: WorkspaceScope | string): Promise<DoctorReport> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/doctor${qs(scope)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as DoctorReport;
  }

  async probeProject(projectPath: string): Promise<ProjectProbe> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/project/probe${qs(projectPath)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectProbe;
  }

  async getOpeners(scope?: WorkspaceScope | string): Promise<OpenersData> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/openers${qs(scope)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as OpenersData;
  }

  async getAgents(scope?: WorkspaceScope | string): Promise<AgentsData> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/agents${qs(scope)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as AgentsData;
  }

  async runAction(action: WorkspaceAction, target?: string, scope?: WorkspaceScope | string): Promise<ActionResult> {
    return this.runWorkspaceAction({ action, target, ...normalizeScope(scope) });
  }

  async runWorkspaceAction(request: WorkspaceActionRequest): Promise<ActionResult> {
    const { projectPath, configPath, stopRemoved, ...body } = request;
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/action${qs({ projectPath, configPath })}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, stop_removed: stopRemoved }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ActionResult;
  }

  async stopSlot(sessionName: string, scope?: WorkspaceScope | string): Promise<ActionResult> {
    return this.runAction("stop", sessionName, scope);
  }

  async getApiInfo(): Promise<{ port: number; config_path: string; state_path: string }> {
    return this._invoke("get_api_info") as Promise<{ port: number; config_path: string; state_path: string }>;
  }

  async getProfiles(): Promise<Profile[]> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/profiles`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data.profiles as Profile[];
  }

  async initWorkspace(profile: string, bootstrapSessions: boolean, scope?: WorkspaceScope | string): Promise<InitResult> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/init${qs(scope)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile, bootstrap_sessions: bootstrapSessions }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as InitResult;
  }

  async saveConfig(
    content: string,
    scope?: WorkspaceScope | string,
    baseMtime?: number | null,
    baseContentHash?: string | null
  ): Promise<ConfigSaveResult> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/config${qs(scope)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        base_mtime: baseMtime,
        base_content_hash: baseContentHash,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new APIRequestError(res.status, data);
    return data as ConfigSaveResult;
  }
}

/**
 * Auto-detect the best client for the current environment.
 */
interface WindowWithTauri extends Window {
  __TAURI__?: unknown;
  __TAURI_INTERNALS__?: unknown;
}

export function createClient(): APIClient {
  const w = window as WindowWithTauri;
  if (w.__TAURI__ || w.__TAURI_INTERNALS__) {
    return new TauriClient();
  }
  return new HTTPClient();
}
