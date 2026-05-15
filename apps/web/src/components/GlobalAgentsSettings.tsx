import { useCallback, useEffect, useMemo, useState } from "react";
import YAML from "js-yaml";
import { AlertTriangle, Bot, ChevronDown, Loader2, Plus, RotateCcw, Save, Trash2 } from "lucide-react";
import { APIRequestError } from "../api/client";
import type { APIClient } from "../api/client";
import type { AgentProfileInfo } from "../types";
import { useI18n } from "../i18n";
import { useToast } from "./ui/Toast";
import { FieldLabel, HelpText, SelectInput, TextInput } from "./ConfigEditor/FormPrimitives";
import type { AgentConfig } from "./ConfigEditor/types";

export type GlobalAgentConfig = AgentConfig & {
  install_hint: string;
};

const DEFAULT_AGENT: GlobalAgentConfig = {
  command: "",
  install_hint: "",
  resume_mode: "none",
  resume_template: "",
  create_mode: "none",
  create_template: "",
  label_template: "{project}/{tab}/{pane}",
  label_mode: "metadata",
  rename_template: "",
};

type NormalizedAgent = {
  command: string;
  install_hint: string;
  resume_mode: string;
  resume_template: string;
  create_mode: string;
  create_template: string;
  label_template: string;
  label_mode: string;
  rename_template: string;
};

function coerceAgent(raw: unknown, name: string): GlobalAgentConfig {
  const r = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const resumeMode = String(r.resume_mode ?? "none");
  const createMode = String(r.create_mode ?? "none");
  const labelMode = String(r.label_mode ?? "metadata");
  return {
    command: String(r.command ?? name),
    install_hint: String(r.install_hint ?? ""),
    resume_mode: ["none", "flag", "internal"].includes(resumeMode)
      ? (resumeMode as GlobalAgentConfig["resume_mode"])
      : "none",
    resume_template: String(r.resume_template ?? ""),
    create_mode: ["none", "generated_uuid"].includes(createMode)
      ? (createMode as GlobalAgentConfig["create_mode"])
      : "none",
    create_template: String(r.create_template ?? ""),
    label_template: String(r.label_template ?? "{project}/{tab}/{pane}"),
    label_mode: ["metadata", "internal"].includes(labelMode)
      ? (labelMode as GlobalAgentConfig["label_mode"])
      : "metadata",
    rename_template: String(r.rename_template ?? ""),
  };
}

function agentsFromPayload(items: AgentProfileInfo[]): Record<string, GlobalAgentConfig> {
  return Object.fromEntries(
    items.map((agent) => [
      agent.id,
      coerceAgent({
        command: agent.command,
        install_hint: agent.install_hint ?? "",
        resume_mode: agent.resume_mode,
        resume_template: agent.resume_template,
        create_mode: agent.create_mode,
        create_template: agent.create_template,
        label_template: agent.label_template,
        label_mode: agent.label_mode,
        rename_template: agent.rename_template,
      }, agent.id),
    ])
  );
}

function normalizedAgent(agent: GlobalAgentConfig): NormalizedAgent {
  return {
    command: agent.command,
    install_hint: agent.install_hint,
    resume_mode: agent.resume_mode,
    resume_template: agent.resume_template,
    create_mode: agent.create_mode,
    create_template: agent.create_template,
    label_template: agent.label_template,
    label_mode: agent.label_mode,
    rename_template: agent.rename_template,
  };
}

function cleanAgent(agent: GlobalAgentConfig, baseline?: GlobalAgentConfig): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  const base = baseline ? normalizedAgent(baseline) : null;

  function includeString(key: keyof NormalizedAgent, value: string) {
    if (base) {
      if (value !== base[key]) out[key] = value;
      return;
    }
    if (value) out[key] = value;
  }

  function includeMode(
    key: "resume_mode" | "create_mode" | "label_mode",
    value: string,
    defaultValue: string,
  ) {
    if (base) {
      if (value !== base[key]) out[key] = value;
      return;
    }
    if (value !== defaultValue) out[key] = value;
  }

  includeString("command", agent.command);
  includeString("install_hint", agent.install_hint);
  includeMode("resume_mode", agent.resume_mode, "none");
  includeString("resume_template", agent.resume_template);
  includeMode("create_mode", agent.create_mode, "none");
  includeString("create_template", agent.create_template);
  includeString("label_template", agent.label_template);
  includeMode("label_mode", agent.label_mode, "metadata");
  includeString("rename_template", agent.rename_template);
  return out;
}

export function agentEquals(a: GlobalAgentConfig | undefined, b: GlobalAgentConfig | undefined): boolean {
  if (!a || !b) return false;
  return JSON.stringify(normalizedAgent(a)) === JSON.stringify(normalizedAgent(b));
}

export function removeOrResetAgent(
  agents: Record<string, GlobalAgentConfig>,
  baseline: Record<string, GlobalAgentConfig>,
  name: string,
): Record<string, GlobalAgentConfig> {
  const next = { ...agents };
  if (baseline[name]) next[name] = baseline[name];
  else delete next[name];
  return next;
}

export function serializeGlobalAgents(
  agents: Record<string, GlobalAgentConfig>,
  baseline: Record<string, GlobalAgentConfig> = {},
): string {
  const out: Record<string, unknown> = { agents: {} };
  for (const [name, agent] of Object.entries(agents)) {
    if (agentEquals(agent, baseline[name])) continue;
    (out.agents as Record<string, unknown>)[name] = cleanAgent(agent, baseline[name]);
  }
  return YAML.dump(out, {
    indent: 2,
    lineWidth: -1,
    noRefs: true,
    sortKeys: false,
  });
}

function nextAgentName(agents: Record<string, GlobalAgentConfig>): string {
  const names = new Set(Object.keys(agents));
  const preferred = ["codex", "claude", "gemini", "cursor"].find((name) => !names.has(name));
  if (preferred) return preferred;
  let index = Object.keys(agents).length + 1;
  while (names.has(`agent-${index}`)) index += 1;
  return `agent-${index}`;
}

function AgentCard({
  name,
  agent,
  expanded,
  isBuiltIn,
  isOverridden,
  onToggle,
  onPatch,
  onRename,
  onDelete,
}: {
  name: string;
  agent: GlobalAgentConfig;
  expanded: boolean;
  isBuiltIn: boolean;
  isOverridden: boolean;
  onToggle: () => void;
  onPatch: (patch: Partial<GlobalAgentConfig>) => void;
  onRename: (name: string) => boolean;
  onDelete: () => void;
}) {
  const { t } = useI18n();
  const [draftName, setDraftName] = useState(name);

  useEffect(() => {
    setDraftName(name);
  }, [name]);

  function commitName() {
    const next = draftName.trim();
    if (next === name) return;
    if (!onRename(next)) setDraftName(name);
  }

  return (
    <div className="rounded-md border border-default bg-[var(--bg-card)]">
      <div className="flex items-center gap-2 px-3 py-2">
        <button
          type="button"
          onClick={onToggle}
          className="flex-1 min-w-0 text-left rounded-md hover:surface-hover transition-colors px-1.5 py-1 flex items-center gap-2"
        >
          <ChevronDown className={`w-3.5 h-3.5 text-tertiary shrink-0 transition-transform ${expanded ? "" : "-rotate-90"}`} />
          <Bot className="w-3.5 h-3.5 text-tertiary shrink-0" />
          <span className="min-w-0">
            <span className="block text-[13px] font-semibold text-primary truncate">{name}</span>
            <span className="block text-[11px] text-tertiary truncate">{agent.command || t("customAgent")}</span>
          </span>
        </button>
        <button
          type="button"
          onClick={onDelete}
          disabled={isBuiltIn && !isOverridden}
          className="icon-touch rounded-md text-tertiary hover:text-primary hover:bg-[var(--bg-hover)] disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent flex items-center justify-center"
          aria-label={isBuiltIn ? t("resetAgentNamed", { name }) : t("removeAgentNamed", { name })}
          title={isBuiltIn ? t("resetAgentNamed", { name }) : t("removeAgentNamed", { name })}
        >
          {isBuiltIn ? <RotateCcw className="w-3.5 h-3.5" /> : <Trash2 className="w-3.5 h-3.5" />}
        </button>
      </div>

      {expanded && (
        <div className="px-3 pb-3 pt-1 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <FieldLabel required>{t("agentName")}</FieldLabel>
              <TextInput
                value={draftName}
                onChange={setDraftName}
                onBlur={commitName}
                disabled={isBuiltIn}
                onKeyDown={(event) => {
                  if (event.key === "Enter") event.currentTarget.blur();
                }}
                invalid={!draftName.trim()}
              />
              {isBuiltIn && <HelpText>{t("builtinAgentNameLocked")}</HelpText>}
            </div>
            <div>
              <FieldLabel required>{t("command")}</FieldLabel>
              <TextInput value={agent.command} onChange={(value) => onPatch({ command: value })} placeholder="codex" />
            </div>
            <div>
              <FieldLabel>{t("resumeMode")}</FieldLabel>
              <SelectInput
                value={agent.resume_mode}
                onChange={(value) => onPatch({ resume_mode: value as GlobalAgentConfig["resume_mode"] })}
                options={[
                  { value: "none", label: t("none") },
                  { value: "flag", label: t("flagMode") },
                  { value: "internal", label: t("internalCommand") },
                ]}
              />
            </div>
            <div>
              <FieldLabel>{t("createMode")}</FieldLabel>
              <SelectInput
                value={agent.create_mode}
                onChange={(value) => onPatch({ create_mode: value as GlobalAgentConfig["create_mode"] })}
                options={[
                  { value: "none", label: t("none") },
                  { value: "generated_uuid", label: t("generatedUuid") },
                ]}
              />
            </div>
          </div>

          <details className="rounded-md border border-default bg-[var(--bg-hover)]/30">
            <summary className="cursor-pointer px-3 py-2 text-[11px] font-semibold uppercase text-tertiary">
              {t("advanced")}
            </summary>
            <div className="px-3 pb-3 pt-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <FieldLabel>{t("resumeTemplate")}</FieldLabel>
                <TextInput value={agent.resume_template} onChange={(value) => onPatch({ resume_template: value })} placeholder="resume {session_id}" />
              </div>
              <div>
                <FieldLabel>{t("createTemplate")}</FieldLabel>
                <TextInput value={agent.create_template} onChange={(value) => onPatch({ create_template: value })} placeholder="tool --session-id {session_id}" />
              </div>
              <div>
                <FieldLabel>{t("labelTemplate")}</FieldLabel>
                <TextInput value={agent.label_template} onChange={(value) => onPatch({ label_template: value })} placeholder="{project}/{tab}/{pane}" />
              </div>
              <div>
                <FieldLabel>{t("labelMode")}</FieldLabel>
                <SelectInput
                  value={agent.label_mode}
                  onChange={(value) => onPatch({ label_mode: value as GlobalAgentConfig["label_mode"] })}
                  options={[
                    { value: "metadata", label: t("metadata") },
                    { value: "internal", label: t("internal") },
                  ]}
                />
              </div>
              <div className="sm:col-span-2">
                <FieldLabel>{t("installHint")}</FieldLabel>
                <TextInput value={agent.install_hint} onChange={(value) => onPatch({ install_hint: value })} placeholder="Install with npm / pip / brew..." />
              </div>
            </div>
          </details>
        </div>
      )}
    </div>
  );
}

export default function GlobalAgentsSettings({ api }: { api: APIClient }) {
  const { t } = useI18n();
  const toast = useToast();
  const [path, setPath] = useState("");
  const [agents, setAgents] = useState<Record<string, GlobalAgentConfig>>({});
  const [builtinAgents, setBuiltinAgents] = useState<Record<string, GlobalAgentConfig>>({});
  const [initialContent, setInitialContent] = useState("");
  const [baseMtime, setBaseMtime] = useState<number | null | undefined>(null);
  const [baseHash, setBaseHash] = useState<string | undefined>(undefined);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const content = useMemo(() => serializeGlobalAgents(agents, builtinAgents), [agents, builtinAgents]);
  const dirty = content !== initialContent;

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    api
      .getGlobalAgents()
      .then((data) => {
        const parsed = agentsFromPayload(data.agents);
        const builtin = agentsFromPayload(data.builtin_agents ?? []);
        setAgents(parsed);
        setBuiltinAgents(builtin);
        setInitialContent(serializeGlobalAgents(parsed, builtin));
        setPath(data.path);
        setBaseMtime(data.mtime);
        setBaseHash(data.content_hash);
        setExpanded(Object.keys(parsed)[0] ?? null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, [api]);

  useEffect(() => {
    load();
  }, [load]);

  function addAgent() {
    const name = nextAgentName(agents);
    setAgents((current) => ({
      ...current,
      [name]: { ...DEFAULT_AGENT, command: name },
    }));
    setExpanded(name);
  }

  function patchAgent(name: string, patch: Partial<GlobalAgentConfig>) {
    setAgents((current) => ({
      ...current,
      [name]: { ...current[name], ...patch },
    }));
  }

  function renameAgent(from: string, toRaw: string): boolean {
    if (builtinAgents[from]) {
      setError(t("builtinAgentNameLocked"));
      return false;
    }
    const to = toRaw.trim();
    if (!to) {
      setError(t("agentNameRequired"));
      return false;
    }
    if (to !== from && agents[to]) {
      setError(t("agentAlreadyExists", { name: to }));
      return false;
    }
    setAgents((current) => {
      const next: Record<string, GlobalAgentConfig> = {};
      for (const [name, agent] of Object.entries(current)) {
        next[name === from ? to : name] = name === from && agent.command === from
          ? { ...agent, command: to }
          : agent;
      }
      return next;
    });
    setExpanded(to);
    setError("");
    return true;
  }

  function deleteAgent(name: string) {
    setAgents((current) => removeOrResetAgent(current, builtinAgents, name));
    if (expanded === name) setExpanded(null);
  }

  async function save() {
    setSaving(true);
    setError("");
    try {
      const result = await api.saveGlobalAgents(content, baseMtime, baseHash);
      const parsed = agentsFromPayload(result.agents);
      const builtin = agentsFromPayload(result.builtin_agents ?? []);
      setAgents(parsed);
      setBuiltinAgents(builtin);
      setInitialContent(serializeGlobalAgents(parsed, builtin));
      setPath(result.path);
      setBaseMtime(result.mtime);
      setBaseHash(result.content_hash);
      toast.success(t("globalAgentsSaved"));
    } catch (err: unknown) {
      const message = err instanceof APIRequestError || err instanceof Error ? err.message : String(err);
      setError(message);
      toast.error(message);
    } finally {
      setSaving(false);
    }
  }

  async function resetToSystemDefaults() {
    setSaving(true);
    setError("");
    try {
      const result = await api.saveGlobalAgents("agents: {}\n", baseMtime, baseHash);
      const parsed = agentsFromPayload(result.agents);
      const builtin = agentsFromPayload(result.builtin_agents ?? []);
      setAgents(parsed);
      setBuiltinAgents(builtin);
      setInitialContent(serializeGlobalAgents(parsed, builtin));
      setPath(result.path);
      setBaseMtime(result.mtime);
      setBaseHash(result.content_hash);
      setExpanded(Object.keys(parsed)[0] ?? null);
      toast.success(t("globalAgentsReset"));
    } catch (err: unknown) {
      const message = err instanceof APIRequestError || err instanceof Error ? err.message : String(err);
      setError(message);
      toast.error(message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section>
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <Bot className="w-3.5 h-3.5 text-tertiary shrink-0" />
          <h4 className="text-[12px] font-semibold text-primary">{t("globalAgents")}</h4>
        </div>
        <button
          type="button"
          onClick={addAgent}
          className="h-8 px-2.5 rounded-md bg-[var(--accent)] text-white text-[12px] font-medium flex items-center gap-1.5 disabled:opacity-50"
          disabled={loading}
        >
          <Plus className="w-3.5 h-3.5" />
          {t("add")}
        </button>
      </div>
      <p className="text-[12px] text-secondary leading-relaxed mb-2">{t("globalAgentsHint")}</p>
      {path && <p className="text-[11px] text-tertiary font-mono truncate mb-2" title={path}>{path}</p>}

      {loading ? (
        <div className="h-28 rounded-md border border-default bg-[var(--bg-page)] flex items-center justify-center text-tertiary">
          <Loader2 className="w-4 h-4 animate-spin" />
        </div>
      ) : (
        <div className="space-y-2 max-h-[45vh] overflow-y-auto pr-1">
          {Object.entries(agents).map(([name, agent]) => (
            <AgentCard
              key={name}
              name={name}
              agent={agent}
              expanded={expanded === name}
              isBuiltIn={Boolean(builtinAgents[name])}
              isOverridden={Boolean(builtinAgents[name] && !agentEquals(agent, builtinAgents[name]))}
              onToggle={() => setExpanded((current) => current === name ? null : name)}
              onPatch={(patch) => patchAgent(name, patch)}
              onRename={(nextName) => renameAgent(name, nextName)}
              onDelete={() => deleteAgent(name)}
            />
          ))}
          {Object.keys(agents).length === 0 && (
            <div className="text-center py-6 border border-dashed border-default rounded-md">
              <Bot className="w-5 h-5 text-tertiary mx-auto mb-1.5" />
              <p className="text-[12px] text-secondary">{t("noAgentsYet")}</p>
              <p className="text-[11px] text-tertiary mt-0.5">{t("globalAgentsEmptyHint")}</p>
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="mt-2 rounded-md border border-[var(--danger)]/20 danger-bg px-2.5 py-2 text-[12px] text-primary flex items-start gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-[var(--danger)] mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex items-center justify-end gap-2 mt-2">
        <button
          type="button"
          onClick={load}
          disabled={!dirty || loading || saving}
          className="h-8 px-3 rounded text-[12px] font-medium text-secondary hover:text-primary surface-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          {t("revert")}
        </button>
        <button
          type="button"
          onClick={resetToSystemDefaults}
          disabled={loading || saving}
          className="h-8 px-3 rounded text-[12px] font-medium text-secondary hover:text-primary surface-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {t("resetToDefaults")}
        </button>
        <button
          type="button"
          onClick={save}
          disabled={!dirty || loading || saving}
          className="h-8 px-3 rounded text-[12px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
        >
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
          {t("save")}
        </button>
      </div>
    </section>
  );
}
