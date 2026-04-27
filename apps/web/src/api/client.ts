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
} from "../types";

export interface APIClient {
  getStatus(projectPath?: string, signal?: AbortSignal): Promise<WorkspaceStatus>;
  getConfig(projectPath?: string, signal?: AbortSignal): Promise<ConfigData>;
  getDoctor(projectPath?: string, signal?: AbortSignal): Promise<DoctorReport>;
  probeProject(projectPath: string, signal?: AbortSignal): Promise<ProjectProbe>;
  getOpeners(projectPath?: string, signal?: AbortSignal): Promise<OpenersData>;
  runAction(action: WorkspaceAction, target?: string, projectPath?: string): Promise<ActionResult>;
  runWorkspaceAction(request: WorkspaceActionRequest): Promise<ActionResult>;
  stopSlot(sessionName: string, projectPath?: string): Promise<ActionResult>;
  getApiInfo(signal?: AbortSignal): Promise<{ port: number; config_path: string; state_path: string }>;
  getProfiles(signal?: AbortSignal): Promise<Profile[]>;
  initWorkspace(profile: string, bootstrapSessions: boolean, projectPath?: string): Promise<InitResult>;
  saveConfig(content: string, projectPath?: string): Promise<{ success: boolean; path: string }>;
}

function qs(projectPath?: string): string {
  return projectPath ? `?project_path=${encodeURIComponent(projectPath)}` : "";
}

/**
 * HTTP implementation — used by the web UI (cc-branch serve).
 */
export class HTTPClient implements APIClient {
  private baseUrl: string;

  constructor(baseUrl: string = "") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async getStatus(projectPath?: string, signal?: AbortSignal): Promise<WorkspaceStatus> {
    const res = await fetch(`${this.baseUrl}/api/status${qs(projectPath)}`, { signal });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as WorkspaceStatus;
  }

  async getConfig(projectPath?: string, signal?: AbortSignal): Promise<ConfigData> {
    const res = await fetch(`${this.baseUrl}/api/config${qs(projectPath)}`, { signal });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigData;
  }

  async getDoctor(projectPath?: string, signal?: AbortSignal): Promise<DoctorReport> {
    const res = await fetch(`${this.baseUrl}/api/doctor${qs(projectPath)}`, { signal });
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

  async getOpeners(projectPath?: string, signal?: AbortSignal): Promise<OpenersData> {
    const res = await fetch(`${this.baseUrl}/api/openers${qs(projectPath)}`, { signal });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as OpenersData;
  }

  async runAction(action: WorkspaceAction, target?: string, projectPath?: string): Promise<ActionResult> {
    return this.runWorkspaceAction({ action, target, projectPath });
  }

  async runWorkspaceAction(request: WorkspaceActionRequest): Promise<ActionResult> {
    const { projectPath, ...body } = request;
    const res = await fetch(`${this.baseUrl}/api/action${qs(projectPath)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ActionResult;
  }

  async stopSlot(sessionName: string, projectPath?: string): Promise<ActionResult> {
    return this.runAction("stop", sessionName, projectPath);
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

  async initWorkspace(profile: string, bootstrapSessions: boolean, projectPath?: string): Promise<InitResult> {
    const res = await fetch(`${this.baseUrl}/api/init${qs(projectPath)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile, bootstrap_sessions: bootstrapSessions }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as InitResult;
  }

  async saveConfig(content: string, projectPath?: string): Promise<{ success: boolean; path: string }> {
    const res = await fetch(`${this.baseUrl}/api/config${qs(projectPath)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as { success: boolean; path: string };
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

  async getStatus(projectPath?: string): Promise<WorkspaceStatus> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/status${qs(projectPath)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as WorkspaceStatus;
  }

  async getConfig(projectPath?: string): Promise<ConfigData> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/config${qs(projectPath)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigData;
  }

  async getDoctor(projectPath?: string): Promise<DoctorReport> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/doctor${qs(projectPath)}`);
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

  async getOpeners(projectPath?: string): Promise<OpenersData> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/openers${qs(projectPath)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as OpenersData;
  }

  async runAction(action: WorkspaceAction, target?: string, projectPath?: string): Promise<ActionResult> {
    return this.runWorkspaceAction({ action, target, projectPath });
  }

  async runWorkspaceAction(request: WorkspaceActionRequest): Promise<ActionResult> {
    const { projectPath, ...body } = request;
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/action${qs(projectPath)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ActionResult;
  }

  async stopSlot(sessionName: string, projectPath?: string): Promise<ActionResult> {
    return this.runAction("stop", sessionName, projectPath);
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

  async initWorkspace(profile: string, bootstrapSessions: boolean, projectPath?: string): Promise<InitResult> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/init${qs(projectPath)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile, bootstrap_sessions: bootstrapSessions }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as InitResult;
  }

  async saveConfig(content: string, projectPath?: string): Promise<{ success: boolean; path: string }> {
    const baseUrl = await this._baseUrl();
    const res = await fetch(`${baseUrl}/api/config${qs(projectPath)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as { success: boolean; path: string };
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
