/**
 * ConfigEditor — YAML ↔ form data bidirectional utilities.
 *
 * Uses js-yaml for parsing/serialization. Preserves comments is NOT supported;
 * switching to raw YAML mode and back will strip comments.
 */

import YAML from "js-yaml";
import type { ConfigFormData, AgentConfig, SlotConfig, WindowConfig, ShellSpec, RemoteConfig, RemoteSetting } from "./types";
import { createDefaultConfig } from "./types";
import { validateWorkspaceNames } from "./workspace-validation";

function coerceLayoutBackend(value: unknown, fallback: "tmux" | "direct" = "direct"): "tmux" | "direct" {
  const raw = String(value ?? "").trim();
  if (raw === "tmux" || raw === "direct") return raw;
  return fallback;
}

function coerceOpenWith(value: unknown): string | null {
  if (value == null) return null;
  const raw = String(value).trim();
  if (!raw) return null;
  return raw;
}

function paneLayoutBackend(pane: Record<string, unknown>, fallback: "tmux" | "direct"): "tmux" | "direct" {
  if (pane.layoutBackend != null) return coerceLayoutBackend(pane.layoutBackend, fallback);
  return fallback;
}

function coerceShellSpec(raw: unknown): ShellSpec | null {
  if (raw == null) return null;
  if (typeof raw === "string") return raw as ShellSpec;
  if (typeof raw === "object") {
    const record = raw as Record<string, unknown>;
    const command = record.command != null ? String(record.command).trim() : "";
    if (!command) return null;
    const args = Array.isArray(record.args) ? record.args.map((arg) => String(arg)) : undefined;
    return args && args.length > 0 ? { command, args } : { command };
  }
  return null;
}

function coerceRemoteConfig(raw: unknown): RemoteSetting {
  if (raw == null) return null;
  if (raw === false) return false;
  if (typeof raw === "string") {
    const host = raw.trim();
    return host ? { host } : null;
  }
  if (typeof raw !== "object" || Array.isArray(raw)) return null;
  const r = raw as Record<string, unknown>;
  const host = String(r.host ?? "").trim();
  const remote: RemoteConfig = {};
  if (host) remote.host = host;
  if (r.user != null) remote.user = String(r.user);
  if (r.port != null && Number.isFinite(Number(r.port))) remote.port = Number(r.port);
  if (r.cwd != null) remote.cwd = String(r.cwd);
  if (Array.isArray(r.args)) remote.args = r.args.map((arg) => String(arg));
  if (r.options && typeof r.options === "object" && !Array.isArray(r.options)) {
    remote.options = Object.fromEntries(Object.entries(r.options as Record<string, unknown>));
  }
  return Object.keys(remote).length > 0 ? remote : null;
}

function coerceAgentConfig(raw: unknown): AgentConfig {
  const r = raw as Record<string, unknown>;
  return {
    command: String(r?.command ?? ""),
    resume_mode: ["none", "flag", "internal"].includes(String(r?.resume_mode))
      ? (String(r?.resume_mode) as "none" | "flag" | "internal")
      : "none",
    resume_template: String(r?.resume_template ?? ""),
    create_mode: ["none", "generated_uuid"].includes(String(r?.create_mode))
      ? (String(r?.create_mode) as "none" | "generated_uuid")
      : "none",
    create_template: String(r?.create_template ?? ""),
    label_template: String(r?.label_template ?? ""),
    label_mode: ["metadata", "internal"].includes(String(r?.label_mode))
      ? (String(r?.label_mode) as "metadata" | "internal")
      : "metadata",
    rename_template: String(r?.rename_template ?? ""),
  };
}

function coerceWindowConfig(raw: unknown): WindowConfig {
  const r = raw as Record<string, unknown>;
  const rawLayout = String(r?.layout ?? "");
  return {
    name: String(r?.name ?? ""),
    enabled: r?.enabled === false ? false : undefined,
    layoutBackend: r?.layoutBackend != null ? coerceLayoutBackend(r.layoutBackend, "direct") : null,
    layout: ["auto", "horizontal", "vertical", "main-left", "main-top", "grid"].includes(rawLayout)
      ? (rawLayout as WindowConfig["layout"])
      : null,
    opener: r?.opener != null ? String(r.opener) : null,
    agent: r?.agent != null ? String(r.agent) : null,
    command: r?.command != null ? String(r.command) : null,
    cwd: r?.cwd != null ? String(r.cwd) : null,
    env: r?.env && typeof r.env === "object" ? Object.fromEntries(
      Object.entries(r.env as Record<string, unknown>).map(([k, v]) => [k, String(v)])
    ) : {},
    remote: coerceRemoteConfig(r?.remote),
    windows: Array.isArray(r?.windows)
      ? r.windows
          .filter((window): window is Record<string, unknown> => Boolean(window && typeof window === "object"))
          .map(coerceWindowConfig)
      : undefined,
    session: r?.session != null ? String(r.session) : null,
    shell: coerceShellSpec(r?.shell),
    label: r?.label != null ? String(r.label) : null,
    label_template: r?.label_template != null ? String(r.label_template) : null,
    resume_mode: r?.resume_mode != null ? String(r.resume_mode) : null,
    resume_template: r?.resume_template != null ? String(r.resume_template) : null,
    create_mode: r?.create_mode != null ? String(r.create_mode) : null,
    create_template: r?.create_template != null ? String(r.create_template) : null,
    label_mode: r?.label_mode != null ? String(r.label_mode) : null,
    rename_template: r?.rename_template != null ? String(r.rename_template) : null,
  };
}

function coerceTabConfig(raw: unknown, defaultLayoutBackend: "tmux" | "direct"): SlotConfig[] {
  const tab = raw as Record<string, unknown>;
  const rawLayout = String(tab?.layout ?? "auto");
  const layout = ["auto", "horizontal", "vertical", "main-left", "main-top", "grid"].includes(rawLayout)
    ? (rawLayout as SlotConfig["layout"])
    : "auto";
  const base = {
    name: String(tab?.name ?? ""),
    layout,
    opener: tab?.opener != null ? String(tab.opener) : undefined,
    cwd: String(tab?.cwd ?? "."),
    env: tab?.env && typeof tab.env === "object" ? Object.fromEntries(
      Object.entries(tab.env as Record<string, unknown>).map(([k, v]) => [k, String(v)])
    ) : {},
    remote: coerceRemoteConfig(tab?.remote),
  };
  const tabLayoutBackend = coerceLayoutBackend(tab?.layoutBackend, defaultLayoutBackend);
  const panes = Array.isArray(tab?.panes) ? tab.panes as unknown[] : [];
  const paneRecords = panes.filter((pane): pane is Record<string, unknown> => Boolean(pane && typeof pane === "object"));
  const isPlainTmuxTab =
    tabLayoutBackend === "tmux" &&
    paneRecords.length > 0 &&
    paneRecords.every((pane) => paneLayoutBackend(pane, tabLayoutBackend) === "tmux") &&
    paneRecords.every((pane) => !Array.isArray(pane.windows) && pane.layoutBackend == null);
  if (isPlainTmuxTab) {
    return [{
      ...base,
      runtime: "tmux",
      windows: paneRecords.map(coerceWindowConfig),
    }];
  }
  const windows = paneRecords.map((pane) => {
    const backend = paneLayoutBackend(pane, tabLayoutBackend);
    if (backend === "tmux") {
      const rawWindows = Array.isArray(pane.windows) ? pane.windows : [];
      return {
        ...coerceWindowConfig(pane),
        layoutBackend: "tmux" as const,
        windows: rawWindows.length > 0
          ? rawWindows
              .filter((window): window is Record<string, unknown> => Boolean(window && typeof window === "object"))
              .map(coerceWindowConfig)
          : [coerceWindowConfig({ ...pane, layoutBackend: null, windows: undefined })],
      };
    }
    return {
      ...coerceWindowConfig(pane),
      layoutBackend: "direct" as const,
      windows: undefined,
    };
  });

  return [{
    ...base,
    runtime: "terminal",
    windows,
  }];
}

function requireCurrentConfigDocument(doc: Record<string, unknown>): void {
  if (Number(doc.version) !== 2) {
    throw new Error("Configuration schema version must be 2.");
  }
  if ("slots" in doc) {
    throw new Error("Unsupported config field 'slots'. Use 'tabs' with 'panes'.");
  }
  if ("default_opener" in doc) {
    throw new Error("Unsupported config field 'default_opener'. Use 'openWith'.");
  }
  const tabs = Array.isArray(doc.tabs) ? doc.tabs : [];
  for (const rawTab of tabs) {
    if (!rawTab || typeof rawTab !== "object") continue;
    const tab = rawTab as Record<string, unknown>;
    if ("runtime" in tab) {
      throw new Error("Unsupported tab field 'runtime'. Use 'layoutBackend'.");
    }
    if ("windows" in tab) {
      throw new Error("Unsupported tab field 'windows'. Use 'panes'.");
    }
    const panes = Array.isArray(tab.panes) ? tab.panes : [];
    for (const rawPane of panes) {
      if (!rawPane || typeof rawPane !== "object") continue;
      const pane = rawPane as Record<string, unknown>;
      if ("runtime" in pane) {
        throw new Error("Unsupported pane field 'runtime'. Use 'layoutBackend'.");
      }
      if ("session_id" in pane) {
        throw new Error("Unsupported pane field 'session_id'. Use 'session'.");
      }
      const windows = Array.isArray(pane.windows) ? pane.windows : [];
      for (const rawWindow of windows) {
        if (rawWindow && typeof rawWindow === "object" && "session_id" in (rawWindow as Record<string, unknown>)) {
          throw new Error("Unsupported window field 'session_id'. Use 'session'.");
        }
      }
    }
  }
}

function coerceConfigDocument(doc: Record<string, unknown>): ConfigFormData {
  requireCurrentConfigDocument(doc);
  const agents: Record<string, AgentConfig> = {};
  if (doc.agents && typeof doc.agents === "object" && !Array.isArray(doc.agents)) {
    for (const [key, val] of Object.entries(doc.agents as Record<string, unknown>)) {
      agents[key] = coerceAgentConfig(val);
    }
  }

  const layoutBackend = coerceLayoutBackend(doc.layoutBackend);
  const defaults = doc.defaults && typeof doc.defaults === "object" && !Array.isArray(doc.defaults)
    ? { shell: coerceShellSpec((doc.defaults as Record<string, unknown>).shell) }
    : { shell: null };

  return {
    version: Number(doc.version ?? 2),
    project: String(doc.project ?? "my-project"),
    root: String(doc.root ?? "."),
    openWith: coerceOpenWith(doc.openWith),
    layoutBackend,
    defaults,
    display: {
      mode: ["grid", "list"].includes(String((doc.display as Record<string, unknown>)?.mode))
        ? (String((doc.display as Record<string, unknown>)?.mode) as "grid" | "list")
        : "grid",
      columns: Number((doc.display as Record<string, unknown>)?.columns ?? 2),
      rows: Number((doc.display as Record<string, unknown>)?.rows ?? 2),
      dashboard: Boolean((doc.display as Record<string, unknown>)?.dashboard ?? false),
    },
    agents,
    slots: Array.isArray(doc.tabs) ? doc.tabs.flatMap((tab) => coerceTabConfig(tab, layoutBackend)) : [],
  };
}

export function parseConfigYamlStrict(yaml: string, invalidRootMessage = "Configuration YAML must be a mapping/object."): ConfigFormData {
  if (!yaml.trim()) return createDefaultConfig();
  const doc = YAML.load(yaml);
  if (!doc || typeof doc !== "object" || Array.isArray(doc)) {
    throw new Error(invalidRootMessage);
  }
  return coerceConfigDocument(doc as Record<string, unknown>);
}

export function parseConfigYaml(yaml: string): ConfigFormData {
  if (!yaml.trim()) return createDefaultConfig();
  try {
    return parseConfigYamlStrict(yaml);
  } catch {
    return createDefaultConfig();
  }
}

function cleanAgentConfig(agent: AgentConfig): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  if (agent.command) out.command = agent.command;
  if (agent.resume_mode !== "none") out.resume_mode = agent.resume_mode;
  if (agent.resume_template) out.resume_template = agent.resume_template;
  if (agent.create_mode !== "none") out.create_mode = agent.create_mode;
  if (agent.create_template) out.create_template = agent.create_template;
  if (agent.label_template) out.label_template = agent.label_template;
  if (agent.label_mode !== "metadata") out.label_mode = agent.label_mode;
  if (agent.rename_template) out.rename_template = agent.rename_template;
  // If agent is completely empty, keep at least command for identification
  if (Object.keys(out).length === 0 && agent.command === "") {
    out.command = "";
  }
  return out;
}

function cleanWindowConfig(win: WindowConfig): Record<string, unknown> {
  const out: Record<string, unknown> = { name: win.name };
  if (win.enabled === false) out.enabled = false;
  if (win.agent != null) out.agent = win.agent;
  if (win.command != null) out.command = win.command;
  if (win.cwd != null) out.cwd = win.cwd;
  if (Object.keys(win.env).length > 0) out.env = win.env;
  if (win.remote != null) out.remote = win.remote;
  if (win.session != null && win.session !== "auto") out.session = win.session;
  if (win.shell != null) out.shell = win.shell;
  if (win.label != null) out.label = win.label;
  if (win.label_template != null) out.label_template = win.label_template;
  if (win.resume_mode != null) out.resume_mode = win.resume_mode;
  if (win.resume_template != null) out.resume_template = win.resume_template;
  if (win.create_mode != null) out.create_mode = win.create_mode;
  if (win.create_template != null) out.create_template = win.create_template;
  if (win.label_mode != null) out.label_mode = win.label_mode;
  if (win.rename_template != null) out.rename_template = win.rename_template;
  return out;
}

function cleanPaneConfig(win: WindowConfig, defaultLayoutBackend: "tmux" | "direct"): Record<string, unknown> {
  if (win.layoutBackend === "tmux" || win.windows) {
    const out: Record<string, unknown> = { name: win.name };
    if (defaultLayoutBackend !== "tmux") out.layoutBackend = "tmux";
    if (win.layout != null && win.layout !== "auto") out.layout = win.layout;
    if (win.opener != null) out.opener = win.opener;
    if (win.cwd != null) out.cwd = win.cwd;
    if (Object.keys(win.env).length > 0) out.env = win.env;
    if (win.remote != null) out.remote = win.remote;
    out.windows = (win.windows && win.windows.length > 0 ? win.windows : [win]).map(cleanWindowConfig);
    return out;
  }
  const out = cleanWindowConfig(win);
  if (defaultLayoutBackend === "tmux") out.layoutBackend = "direct";
  if (win.opener != null) out.opener = win.opener;
  return out;
}

function cleanTabConfig(slot: SlotConfig, defaultLayoutBackend: "tmux" | "direct"): Record<string, unknown> {
  const out: Record<string, unknown> = {
    name: slot.name,
    cwd: slot.cwd,
  };
  if (slot.opener != null) out.opener = slot.opener;
  if (slot.layout != null && slot.layout !== "auto") out.layout = slot.layout;
  if (Object.keys(slot.env).length > 0) out.env = slot.env;
  if (slot.remote != null) out.remote = slot.remote;

  const hasPaneBackends = slot.windows.some((window) => window.layoutBackend === "tmux" || window.windows);
  const slotLayoutBackend = hasPaneBackends ? defaultLayoutBackend : slot.runtime === "tmux" ? "tmux" : "direct";
  if (slotLayoutBackend !== defaultLayoutBackend) out.layoutBackend = slotLayoutBackend;

  if (slot.windows.length > 0) {
    if (!hasPaneBackends && slot.runtime === "tmux" && slot.windows.length > 0) {
      out.panes = slot.windows.map(cleanWindowConfig);
    } else {
      out.panes = slot.windows.map((window) => cleanPaneConfig(window, defaultLayoutBackend));
    }
  } else {
    const pane: Record<string, unknown> = { name: slot.title || slot.name || "main" };
    if (slot.command != null) pane.command = slot.command;
    if (slot.agent != null) pane.agent = slot.agent;
    if (slot.session != null && slot.session !== "auto") pane.session = slot.session;
    if (slot.label != null) pane.label = slot.label;
    out.panes = [pane];
  }
  return out;
}

export function serializeConfigForm(data: ConfigFormData): string {
  const layoutBackend = data.layoutBackend ?? "direct";
  const defaults = data.defaults ?? { shell: null };
  const out: Record<string, unknown> = {
    version: data.version || 2,
    project: data.project,
    root: data.root,
  };
  if (data.openWith) out.openWith = data.openWith;
  if (layoutBackend !== "direct") out.layoutBackend = layoutBackend;
  if (defaults.shell != null) out.defaults = { shell: defaults.shell };

  if (data.display.mode !== "grid" || data.display.columns !== 2 || data.display.rows !== 2 || data.display.dashboard !== false) {
    const d: Record<string, unknown> = {};
    if (data.display.mode !== "grid") d.mode = data.display.mode;
    if (data.display.columns !== 2) d.columns = data.display.columns;
    if (data.display.rows !== 2 || data.display.columns !== 2) d.rows = data.display.rows;
    if (data.display.dashboard !== false) d.dashboard = data.display.dashboard;
    out.display = d;
  }

  if (Object.keys(data.agents).length > 0) {
    const agents: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(data.agents)) {
      agents[key] = cleanAgentConfig(val);
    }
    out.agents = agents;
  }

  if (data.slots.length > 0) {
    out.tabs = data.slots.map((slot) => cleanTabConfig(slot, layoutBackend));
  }

  return YAML.dump(out, {
    indent: 2,
    lineWidth: -1,
    noRefs: true,
    sortKeys: false,
  });
}

/**
 * Validate a config form. Returns array of error strings, empty if valid.
 */
function defaultValidationMessage(key: string, vars?: Record<string, string | number>): string {
  const messages: Record<string, string> = {
    projectNameRequired: "Project name is required",
    allSlotsMustHaveName: "All slots must have a name",
    allWindowsMustHaveName: "All windows must have a name",
    duplicateSlotNames: "Duplicate slot names: {names}",
    duplicatePaneNames: "Duplicate pane/window names: {names}",
    missingLaunchCommands: "These panes have nothing to launch yet: {names}. Choose an Agent, use the default Shell, or enter a command.",
    reservedTargetNameSeparators: "Names cannot contain ':' or '.': {names}",
    remoteHostRequired: "SSH host is required for: {names}",
    remotePortInvalid: "SSH port must be between 1 and 65535 for: {names}",
  };
  const template = messages[key] || key;
  return template.replace(/\{(\w+)\}/g, (_, name) => String(vars?.[name] ?? `{${name}}`));
}

function isRemoteConfig(remote: RemoteSetting | undefined): remote is RemoteConfig {
  return typeof remote === "object" && remote !== null;
}

function remoteHasHost(remote: RemoteSetting | undefined): boolean {
  return isRemoteConfig(remote) && Boolean(String(remote.host ?? "").trim());
}

function remoteHasValidPort(remote: RemoteSetting | undefined): boolean {
  if (!isRemoteConfig(remote) || remote.port == null) return true;
  return Number.isInteger(remote.port) && remote.port >= 1 && remote.port <= 65535;
}

function collectRemoteValidation(slots: SlotConfig[]): { missingHosts: string[]; invalidPorts: string[] } {
  const missingHosts: string[] = [];
  const invalidPorts: string[] = [];

  function inspectRemote(remote: RemoteSetting | undefined, inheritedRemote: RemoteSetting | undefined, target: string): RemoteSetting | undefined {
    if (remote === false) return null;
    if (isRemoteConfig(remote)) {
      if (!remoteHasHost(remote) && !remoteHasHost(inheritedRemote)) missingHosts.push(target);
      if (!remoteHasValidPort(remote)) invalidPorts.push(target);
      return remoteHasHost(remote) ? remote : inheritedRemote;
    }
    return inheritedRemote;
  }

  function inspectWindows(windows: WindowConfig[], inheritedRemote: RemoteSetting | undefined, scope: string) {
    for (const window of windows) {
      const name = window.name.trim() || "unnamed";
      const target = `${scope}/${name}`;
      const nextRemote = inspectRemote(window.remote, inheritedRemote, target);
      if (window.windows) inspectWindows(window.windows, nextRemote, target);
    }
  }

  for (const slot of slots) {
    const slotName = slot.name.trim() || "unnamed";
    const slotRemote = inspectRemote(slot.remote, null, slotName);
    inspectWindows(slot.windows, slotRemote, slotName);
  }

  return {
    missingHosts: [...new Set(missingHosts)],
    invalidPorts: [...new Set(invalidPorts)],
  };
}

export function validateConfigForm(
  data: ConfigFormData,
  t: (key: string, vars?: Record<string, string | number>) => string = defaultValidationMessage
): string[] {
  const errors: string[] = [];
  if (!data.project.trim()) errors.push(t("projectNameRequired"));
  const workspaceValidation = validateWorkspaceNames(data.slots);
  if (workspaceValidation.hasEmptyTabNames) errors.push(t("allSlotsMustHaveName"));
  if (workspaceValidation.hasEmptyPaneNames) {
    errors.push(t("allWindowsMustHaveName"));
  }
  if (workspaceValidation.duplicateTabNames.length > 0) {
    errors.push(t("duplicateSlotNames", { names: workspaceValidation.duplicateTabNames.join(", ") }));
  }
  if (workspaceValidation.duplicatePaneNames.length > 0) {
    errors.push(t("duplicatePaneNames", { names: workspaceValidation.duplicatePaneNames.join(", ") }));
  }
  if (workspaceValidation.missingLaunchTargets.length > 0) {
    errors.push(t("missingLaunchCommands", { names: workspaceValidation.missingLaunchTargets.join(", ") }));
  }
  if (workspaceValidation.reservedTargetNames.length > 0) {
    errors.push(t("reservedTargetNameSeparators", { names: workspaceValidation.reservedTargetNames.join(", ") }));
  }
  const remoteValidation = collectRemoteValidation(data.slots);
  if (remoteValidation.missingHosts.length > 0) {
    errors.push(t("remoteHostRequired", { names: remoteValidation.missingHosts.join(", ") }));
  }
  if (remoteValidation.invalidPorts.length > 0) {
    errors.push(t("remotePortInvalid", { names: remoteValidation.invalidPorts.join(", ") }));
  }
  return errors;
}
