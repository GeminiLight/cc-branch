/**
 * ConfigEditor — YAML ↔ form data bidirectional utilities.
 *
 * Uses js-yaml for parsing/serialization. Preserves comments is NOT supported;
 * switching to raw YAML mode and back will strip comments.
 */

import YAML from "js-yaml";
import type { ConfigFormData, AgentConfig, SlotConfig, WindowConfig } from "./types";
import { createDefaultConfig } from "./types";

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
  return {
    name: String(r?.name ?? ""),
    agent: r?.agent != null ? String(r.agent) : null,
    command: r?.command != null ? String(r.command) : null,
    cwd: r?.cwd != null ? String(r.cwd) : null,
    env: r?.env && typeof r.env === "object" ? Object.fromEntries(
      Object.entries(r.env as Record<string, unknown>).map(([k, v]) => [k, String(v)])
    ) : {},
    session_id: r?.session_id != null ? String(r.session_id) : null,
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

function coerceSlotConfig(raw: unknown): SlotConfig {
  const r = raw as Record<string, unknown>;
  const runtime = String(r?.runtime ?? "tmux");
  const slot: SlotConfig = {
    name: String(r?.name ?? ""),
    runtime: runtime === "terminal" ? "terminal" : "tmux",
    opener: r?.opener != null ? String(r.opener) : undefined,
    cwd: String(r?.cwd ?? "."),
    env: r?.env && typeof r.env === "object" ? Object.fromEntries(
      Object.entries(r.env as Record<string, unknown>).map(([k, v]) => [k, String(v)])
    ) : {},
    windows: Array.isArray(r?.windows)
      ? r.windows.map(coerceWindowConfig)
      : [],
  };
  if (r?.command != null) slot.command = String(r.command);
  if (r?.title != null) slot.title = String(r.title);
  if (r?.agent != null) slot.agent = String(r.agent);
  if (r?.session_id != null) slot.session_id = String(r.session_id);
  if (r?.label != null) slot.label = String(r.label);
  return slot;
}

export function parseConfigYaml(yaml: string): ConfigFormData {
  if (!yaml.trim()) return createDefaultConfig();
  try {
    const doc = YAML.load(yaml) as Record<string, unknown>;
    if (!doc || typeof doc !== "object") return createDefaultConfig();

    const agents: Record<string, AgentConfig> = {};
    if (doc.agents && typeof doc.agents === "object") {
      for (const [key, val] of Object.entries(doc.agents as Record<string, unknown>)) {
        agents[key] = coerceAgentConfig(val);
      }
    }

    return {
      version: Number(doc.version ?? 1),
      project: String(doc.project ?? "my-project"),
      root: String(doc.root ?? "."),
      display: {
        mode: ["grid", "list"].includes(String((doc.display as Record<string, unknown>)?.mode))
          ? (String((doc.display as Record<string, unknown>)?.mode) as "grid" | "list")
          : "grid",
        columns: Number((doc.display as Record<string, unknown>)?.columns ?? 2),
        dashboard: Boolean((doc.display as Record<string, unknown>)?.dashboard ?? false),
      },
      agents,
      slots: Array.isArray(doc.slots) ? doc.slots.map(coerceSlotConfig) : [],
    };
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
  if (win.agent != null) out.agent = win.agent;
  if (win.command != null) out.command = win.command;
  if (win.cwd != null) out.cwd = win.cwd;
  if (Object.keys(win.env).length > 0) out.env = win.env;
  if (win.session_id != null) out.session_id = win.session_id;
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

function cleanSlotConfig(slot: SlotConfig): Record<string, unknown> {
  const out: Record<string, unknown> = {
    name: slot.name,
    runtime: slot.runtime,
    cwd: slot.cwd,
  };
  if (slot.opener != null) out.opener = slot.opener;
  if (Object.keys(slot.env).length > 0) out.env = slot.env;

  if (slot.runtime === "terminal") {
    if (slot.command != null) out.command = slot.command;
    if (slot.title != null) out.title = slot.title;
    if (slot.agent != null) out.agent = slot.agent;
    if (slot.session_id != null) out.session_id = slot.session_id;
    if (slot.label != null) out.label = slot.label;
  } else {
    if (slot.windows.length > 0) {
      out.windows = slot.windows.map(cleanWindowConfig);
    }
  }
  return out;
}

export function serializeConfigForm(data: ConfigFormData): string {
  const out: Record<string, unknown> = {
    version: data.version,
    project: data.project,
    root: data.root,
  };

  if (data.display.mode !== "grid" || data.display.columns !== 2 || data.display.dashboard !== false) {
    const d: Record<string, unknown> = {};
    if (data.display.mode !== "grid") d.mode = data.display.mode;
    if (data.display.columns !== 2) d.columns = data.display.columns;
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
    out.slots = data.slots.map(cleanSlotConfig);
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
  };
  const template = messages[key] || key;
  return template.replace(/\{(\w+)\}/g, (_, name) => String(vars?.[name] ?? `{${name}}`));
}

export function validateConfigForm(
  data: ConfigFormData,
  t: (key: string, vars?: Record<string, string | number>) => string = defaultValidationMessage
): string[] {
  const errors: string[] = [];
  if (!data.project.trim()) errors.push(t("projectNameRequired"));
  if (data.slots.some((s) => !s.name.trim())) errors.push(t("allSlotsMustHaveName"));
  if (data.slots.some((s) => s.runtime === "tmux" && s.windows.some((w) => !w.name.trim()))) {
    errors.push(t("allWindowsMustHaveName"));
  }
  // Duplicate slot names
  const slotNames = data.slots.map((s) => s.name);
  const dupSlots = slotNames.filter((name, i) => slotNames.indexOf(name) !== i);
  if (dupSlots.length > 0) {
    errors.push(t("duplicateSlotNames", { names: [...new Set(dupSlots)].join(", ") }));
  }
  return errors;
}
