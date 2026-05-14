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
  AgentSessionsData,
  ConfigSaveResult,
  ConfigIssue,
  ConfigOptionsData,
  WorkspaceScope,
  ProjectsIndexData,
  GlobalAgentsData,
  GlobalAgentsSaveResult,
} from "../types";

export interface APIClient {
  getStatus(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<WorkspaceStatus>;
  getConfig(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<ConfigData>;
  getConfigs(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<ConfigOptionsData>;
  getDoctor(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<DoctorReport>;
  probeProject(projectPath: string, signal?: AbortSignal): Promise<ProjectProbe>;
  supportsNativeProjectDirectoryPicker(): boolean;
  pickProjectDirectory(startingDir?: string): Promise<string | null>;
  getOpeners(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<OpenersData>;
  getAgents(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<AgentsData>;
  getGlobalAgents(signal?: AbortSignal): Promise<GlobalAgentsData>;
  saveGlobalAgents(content: string, baseMtime?: number | null, baseContentHash?: string | null): Promise<GlobalAgentsSaveResult>;
  getAgentSessions(scope?: WorkspaceScope | string, agent?: string, signal?: AbortSignal): Promise<AgentSessionsData>;
  runAction(action: WorkspaceAction, target?: string, scope?: WorkspaceScope | string): Promise<ActionResult>;
  runWorkspaceAction(request: WorkspaceActionRequest): Promise<ActionResult>;
  stopSlot(sessionName: string, scope?: WorkspaceScope | string): Promise<ActionResult>;
  getApiInfo(signal?: AbortSignal): Promise<{ port: number; config_path: string; state_path: string }>;
  getProjectsIndex(signal?: AbortSignal): Promise<ProjectsIndexData>;
  addProject(path: string, name?: string): Promise<ProjectsIndexData>;
  removeProject(id: string): Promise<ProjectsIndexData>;
  activateProject(id: string): Promise<ProjectsIndexData>;
  injectCurrentProject(scope?: WorkspaceScope | string): Promise<ProjectsIndexData>;
  setProjectConfig(projectPath: string, configPath: string): Promise<ProjectsIndexData>;
  createWorkspaceConfig(projectPath: string, name: string, sourceConfigPath?: string): Promise<ConfigOptionsData>;
  renameWorkspaceConfig(projectPath: string, configPath: string, name: string): Promise<ConfigOptionsData>;
  deleteWorkspaceConfig(projectPath: string, configPath: string): Promise<ConfigOptionsData>;
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

function qsWith(scope?: WorkspaceScope | string, values?: Record<string, string | undefined>): string {
  const { projectPath, configPath } = normalizeScope(scope);
  const params = new URLSearchParams();
  if (projectPath) params.set("project_path", projectPath);
  if (configPath) params.set("config_path", configPath);
  Object.entries(values || {}).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

// API endpoints return different payload shapes; callers cast after checking HTTP status.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type JsonResponse = Record<string, any>;

async function fetchApi(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") throw error;
    throw new Error(
      "Cannot reach cc-branch API. Make sure the backend server is running and try again.",
      { cause: error },
    );
  }
}

function abortErrorFrom(signal: AbortSignal): Error {
  if (signal.reason instanceof Error) return signal.reason;
  if (typeof DOMException !== "undefined") {
    return new DOMException("The operation was aborted", "AbortError");
  }
  const error = new Error("The operation was aborted");
  error.name = "AbortError";
  return error;
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw abortErrorFrom(signal);
}

async function readJsonResponse(res: Response): Promise<JsonResponse> {
  if (typeof res.text !== "function" && typeof res.json === "function") {
    try {
      return await res.json() as JsonResponse;
    } catch {
      if (!res.ok || res.status === 204) return {};
      throw new Error(`Invalid JSON response from API (${res.status})`);
    }
  }
  const text = await res.text();
  if (!text.trim()) return {};
  try {
    return JSON.parse(text) as JsonResponse;
  } catch {
    throw new Error(`Invalid JSON response from API (${res.status})`);
  }
}

function normalizeWorkspaceStatus(data: JsonResponse): WorkspaceStatus {
  const slots = Array.isArray(data.slots)
    ? data.slots.map((slot: JsonResponse) => ({
        ...slot,
        windows: Array.isArray(slot?.windows) ? slot.windows : [],
        extra_windows: Array.isArray(slot?.extra_windows) ? slot.extra_windows : [],
      }))
    : [];
  return { ...data, slots } as WorkspaceStatus;
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
    const res = await fetchApi(`${this.baseUrl}/api/status${qs(scope)}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return normalizeWorkspaceStatus(data);
  }

  async getConfig(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<ConfigData> {
    const res = await fetchApi(`${this.baseUrl}/api/config${qs(scope)}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigData;
  }

  async getConfigs(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<ConfigOptionsData> {
    const res = await fetchApi(`${this.baseUrl}/api/configs${qs(scope)}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigOptionsData;
  }

  async getDoctor(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<DoctorReport> {
    const res = await fetchApi(`${this.baseUrl}/api/doctor${qs(scope)}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as DoctorReport;
  }

  async probeProject(projectPath: string, signal?: AbortSignal): Promise<ProjectProbe> {
    const res = await fetchApi(`${this.baseUrl}/api/project/probe${qs(projectPath)}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectProbe;
  }

  supportsNativeProjectDirectoryPicker(): boolean {
    return true;
  }

  async pickProjectDirectory(startingDir?: string): Promise<string | null> {
    const res = await fetchApi(`${this.baseUrl}/api/project/pick-directory`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ starting_dir: startingDir }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(typeof data.error === "string" ? data.error : `HTTP ${res.status}`);
    return typeof data.path === "string" && data.path ? data.path : null;
  }

  async getOpeners(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<OpenersData> {
    const res = await fetchApi(`${this.baseUrl}/api/openers${qs(scope)}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as OpenersData;
  }

  async getAgents(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<AgentsData> {
    const res = await fetchApi(`${this.baseUrl}/api/agents${qs(scope)}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as AgentsData;
  }

  async getGlobalAgents(signal?: AbortSignal): Promise<GlobalAgentsData> {
    const res = await fetchApi(`${this.baseUrl}/api/agents/global`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as GlobalAgentsData;
  }

  async saveGlobalAgents(content: string, baseMtime?: number | null, baseContentHash?: string | null): Promise<GlobalAgentsSaveResult> {
    const res = await fetchApi(`${this.baseUrl}/api/agents/global`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        base_mtime: baseMtime,
        base_content_hash: baseContentHash,
      }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new APIRequestError(res.status, data);
    return data as GlobalAgentsSaveResult;
  }

  async getAgentSessions(scope?: WorkspaceScope | string, agent?: string, signal?: AbortSignal): Promise<AgentSessionsData> {
    const res = await fetchApi(`${this.baseUrl}/api/agent-sessions${qsWith(scope, { agent })}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as AgentSessionsData;
  }

  async runAction(action: WorkspaceAction, target?: string, scope?: WorkspaceScope | string): Promise<ActionResult> {
    return this.runWorkspaceAction({ action, target, ...normalizeScope(scope) });
  }

  async runWorkspaceAction(request: WorkspaceActionRequest): Promise<ActionResult> {
    const { projectPath, configPath, stopRemoved, ...body } = request;
    const res = await fetchApi(`${this.baseUrl}/api/action${qs({ projectPath, configPath })}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, stop_removed: stopRemoved }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ActionResult;
  }

  async stopSlot(sessionName: string, scope?: WorkspaceScope | string): Promise<ActionResult> {
    return this.runAction("stop", sessionName, scope);
  }

  async getApiInfo(signal?: AbortSignal): Promise<{ port: number; config_path: string; state_path: string }> {
    const res = await fetchApi(`${this.baseUrl}/api/info`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as { port: number; config_path: string; state_path: string };
  }

  async getProjectsIndex(signal?: AbortSignal): Promise<ProjectsIndexData> {
    const res = await fetchApi(`${this.baseUrl}/api/projects`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectsIndexData;
  }

  async addProject(path: string, name?: string): Promise<ProjectsIndexData> {
    const res = await fetchApi(`${this.baseUrl}/api/projects/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, name }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(typeof data.error === "string" ? data.error : `HTTP ${res.status}`);
    return data as unknown as ProjectsIndexData;
  }

  async removeProject(id: string): Promise<ProjectsIndexData> {
    const res = await fetchApi(`${this.baseUrl}/api/projects/remove`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectsIndexData;
  }

  async activateProject(id: string): Promise<ProjectsIndexData> {
    const res = await fetchApi(`${this.baseUrl}/api/projects/activate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectsIndexData;
  }

  async injectCurrentProject(scope?: WorkspaceScope | string): Promise<ProjectsIndexData> {
    const res = await fetchApi(`${this.baseUrl}/api/projects/current${qs(scope)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectsIndexData;
  }

  async setProjectConfig(projectPath: string, configPath: string): Promise<ProjectsIndexData> {
    const res = await fetchApi(`${this.baseUrl}/api/projects/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_path: projectPath, config_path: configPath }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectsIndexData;
  }

  async createWorkspaceConfig(projectPath: string, name: string, sourceConfigPath?: string): Promise<ConfigOptionsData> {
    const res = await fetchApi(`${this.baseUrl}/api/configs/create${qs(projectPath)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, source_config_path: sourceConfigPath }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigOptionsData;
  }

  async renameWorkspaceConfig(projectPath: string, configPath: string, name: string): Promise<ConfigOptionsData> {
    const res = await fetchApi(`${this.baseUrl}/api/configs/rename${qs(projectPath)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config_path: configPath, name }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigOptionsData;
  }

  async deleteWorkspaceConfig(projectPath: string, configPath: string): Promise<ConfigOptionsData> {
    const res = await fetchApi(`${this.baseUrl}/api/configs/delete${qs(projectPath)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config_path: configPath }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigOptionsData;
  }

  async getProfiles(signal?: AbortSignal): Promise<Profile[]> {
    const res = await fetchApi(`${this.baseUrl}/api/profiles`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data.profiles as Profile[];
  }

  async initWorkspace(profile: string, bootstrapSessions: boolean, scope?: WorkspaceScope | string): Promise<InitResult> {
    const res = await fetchApi(`${this.baseUrl}/api/init${qs(scope)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile, bootstrap_sessions: bootstrapSessions }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as InitResult;
  }

  async saveConfig(
    content: string,
    scope?: WorkspaceScope | string,
    baseMtime?: number | null,
    baseContentHash?: string | null
  ): Promise<ConfigSaveResult> {
    const res = await fetchApi(`${this.baseUrl}/api/config${qs(scope)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        base_mtime: baseMtime,
        base_content_hash: baseContentHash,
      }),
    });
    const data = await readJsonResponse(res);
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

  private async _baseUrl(signal?: AbortSignal): Promise<string> {
    const info = await this.getApiInfo(signal);
    return `http://127.0.0.1:${info.port}`;
  }

  async getStatus(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<WorkspaceStatus> {
    const baseUrl = await this._baseUrl(signal);
    const res = await fetchApi(`${baseUrl}/api/status${qs(scope)}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return normalizeWorkspaceStatus(data);
  }

  async getConfig(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<ConfigData> {
    const baseUrl = await this._baseUrl(signal);
    const res = await fetchApi(`${baseUrl}/api/config${qs(scope)}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigData;
  }

  async getConfigs(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<ConfigOptionsData> {
    const baseUrl = await this._baseUrl(signal);
    const res = await fetchApi(`${baseUrl}/api/configs${qs(scope)}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigOptionsData;
  }

  async getDoctor(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<DoctorReport> {
    const baseUrl = await this._baseUrl(signal);
    const res = await fetchApi(`${baseUrl}/api/doctor${qs(scope)}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as DoctorReport;
  }

  async probeProject(projectPath: string, signal?: AbortSignal): Promise<ProjectProbe> {
    const baseUrl = await this._baseUrl(signal);
    const res = await fetchApi(`${baseUrl}/api/project/probe${qs(projectPath)}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectProbe;
  }

  supportsNativeProjectDirectoryPicker(): boolean {
    return true;
  }

  async pickProjectDirectory(startingDir?: string): Promise<string | null> {
    const args = startingDir ? { starting_dir: startingDir } : undefined;
    return this._invoke("pick_project_directory", args) as Promise<string | null>;
  }

  async getOpeners(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<OpenersData> {
    const baseUrl = await this._baseUrl(signal);
    const res = await fetchApi(`${baseUrl}/api/openers${qs(scope)}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as OpenersData;
  }

  async getAgents(scope?: WorkspaceScope | string, signal?: AbortSignal): Promise<AgentsData> {
    const baseUrl = await this._baseUrl(signal);
    const res = await fetchApi(`${baseUrl}/api/agents${qs(scope)}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as AgentsData;
  }

  async getGlobalAgents(signal?: AbortSignal): Promise<GlobalAgentsData> {
    const baseUrl = await this._baseUrl(signal);
    const res = await fetchApi(`${baseUrl}/api/agents/global`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as GlobalAgentsData;
  }

  async saveGlobalAgents(content: string, baseMtime?: number | null, baseContentHash?: string | null): Promise<GlobalAgentsSaveResult> {
    const baseUrl = await this._baseUrl();
    const res = await fetchApi(`${baseUrl}/api/agents/global`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        base_mtime: baseMtime,
        base_content_hash: baseContentHash,
      }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new APIRequestError(res.status, data);
    return data as GlobalAgentsSaveResult;
  }

  async getAgentSessions(scope?: WorkspaceScope | string, agent?: string, signal?: AbortSignal): Promise<AgentSessionsData> {
    const baseUrl = await this._baseUrl(signal);
    const res = await fetchApi(`${baseUrl}/api/agent-sessions${qsWith(scope, { agent })}`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as AgentSessionsData;
  }

  async runAction(action: WorkspaceAction, target?: string, scope?: WorkspaceScope | string): Promise<ActionResult> {
    return this.runWorkspaceAction({ action, target, ...normalizeScope(scope) });
  }

  async runWorkspaceAction(request: WorkspaceActionRequest): Promise<ActionResult> {
    const { projectPath, configPath, stopRemoved, ...body } = request;
    const baseUrl = await this._baseUrl();
    const res = await fetchApi(`${baseUrl}/api/action${qs({ projectPath, configPath })}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, stop_removed: stopRemoved }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ActionResult;
  }

  async stopSlot(sessionName: string, scope?: WorkspaceScope | string): Promise<ActionResult> {
    return this.runAction("stop", sessionName, scope);
  }

  async getApiInfo(signal?: AbortSignal): Promise<{ port: number; config_path: string; state_path: string }> {
    throwIfAborted(signal);
    const info = await this._invoke("get_api_info") as { port: number; config_path: string; state_path: string };
    throwIfAborted(signal);
    return info;
  }

  async getProjectsIndex(signal?: AbortSignal): Promise<ProjectsIndexData> {
    const baseUrl = await this._baseUrl(signal);
    const res = await fetchApi(`${baseUrl}/api/projects`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectsIndexData;
  }

  async addProject(path: string, name?: string): Promise<ProjectsIndexData> {
    const baseUrl = await this._baseUrl();
    const res = await fetchApi(`${baseUrl}/api/projects/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, name }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectsIndexData;
  }

  async removeProject(id: string): Promise<ProjectsIndexData> {
    const baseUrl = await this._baseUrl();
    const res = await fetchApi(`${baseUrl}/api/projects/remove`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectsIndexData;
  }

  async activateProject(id: string): Promise<ProjectsIndexData> {
    const baseUrl = await this._baseUrl();
    const res = await fetchApi(`${baseUrl}/api/projects/activate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectsIndexData;
  }

  async injectCurrentProject(scope?: WorkspaceScope | string): Promise<ProjectsIndexData> {
    const baseUrl = await this._baseUrl();
    const res = await fetchApi(`${baseUrl}/api/projects/current${qs(scope)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectsIndexData;
  }

  async setProjectConfig(projectPath: string, configPath: string): Promise<ProjectsIndexData> {
    const baseUrl = await this._baseUrl();
    const res = await fetchApi(`${baseUrl}/api/projects/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_path: projectPath, config_path: configPath }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ProjectsIndexData;
  }

  async createWorkspaceConfig(projectPath: string, name: string, sourceConfigPath?: string): Promise<ConfigOptionsData> {
    const baseUrl = await this._baseUrl();
    const res = await fetchApi(`${baseUrl}/api/configs/create${qs(projectPath)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, source_config_path: sourceConfigPath }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigOptionsData;
  }

  async renameWorkspaceConfig(projectPath: string, configPath: string, name: string): Promise<ConfigOptionsData> {
    const baseUrl = await this._baseUrl();
    const res = await fetchApi(`${baseUrl}/api/configs/rename${qs(projectPath)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config_path: configPath, name }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigOptionsData;
  }

  async deleteWorkspaceConfig(projectPath: string, configPath: string): Promise<ConfigOptionsData> {
    const baseUrl = await this._baseUrl();
    const res = await fetchApi(`${baseUrl}/api/configs/delete${qs(projectPath)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config_path: configPath }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data as ConfigOptionsData;
  }

  async getProfiles(signal?: AbortSignal): Promise<Profile[]> {
    const baseUrl = await this._baseUrl(signal);
    const res = await fetchApi(`${baseUrl}/api/profiles`, { signal });
    const data = await readJsonResponse(res);
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data.profiles as Profile[];
  }

  async initWorkspace(profile: string, bootstrapSessions: boolean, scope?: WorkspaceScope | string): Promise<InitResult> {
    const baseUrl = await this._baseUrl();
    const res = await fetchApi(`${baseUrl}/api/init${qs(scope)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile, bootstrap_sessions: bootstrapSessions }),
    });
    const data = await readJsonResponse(res);
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
    const res = await fetchApi(`${baseUrl}/api/config${qs(scope)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        base_mtime: baseMtime,
        base_content_hash: baseContentHash,
      }),
    });
    const data = await readJsonResponse(res);
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
