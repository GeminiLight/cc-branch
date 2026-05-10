/**
 * ConfigEditor — Agents management section.
 */

import { useEffect, useState } from "react";
import { Bot, Plus, Trash2, ChevronDown, PencilLine, SlidersHorizontal } from "lucide-react";
import { useI18n } from "../../i18n";
import type { AgentConfig } from "./types";
import {
  CollapsibleSection,
  FieldLabel,
  TextInput,
  SelectInput,
  InlineError,
} from "./FormPrimitives";

function AgentCard({
  name,
  agent,
  onChange,
  onRename,
  onDelete,
  initialExpanded = false,
}: {
  name: string;
  agent: AgentConfig;
  onChange: (patch: Partial<AgentConfig>) => void;
  onRename: (nextName: string) => boolean;
  onDelete: () => void;
  initialExpanded?: boolean;
}) {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(initialExpanded);
  const [draftName, setDraftName] = useState(name);
  const hasDetails =
    agent.resume_mode !== "none" ||
    agent.create_mode !== "none" ||
    agent.label_template ||
    agent.rename_template;
  const summary = agent.command ? t("agentCommandSummary", { command: agent.command }) : t("customAgent");

  useEffect(() => {
    setDraftName(name);
  }, [name]);

  function commitName() {
    const nextName = draftName.trim();
    if (nextName === name) {
      setDraftName(name);
      return;
    }
    if (!onRename(nextName)) {
      setDraftName(name);
    }
  }

  return (
    <div className="rounded-md border border-default bg-[var(--bg-card)] shadow-sm">
      <div className="flex items-center gap-2 px-3 py-2">
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="min-h-10 flex-1 min-w-0 rounded-md px-1.5 text-left hover:surface-hover transition-colors flex items-center gap-2"
          aria-label={expanded ? t("collapseAgent", { name }) : t("expandAgent", { name })}
          title={expanded ? t("collapseAgent", { name }) : t("expandAgent", { name })}
        >
          <ChevronDown
            className={`w-3.5 h-3.5 text-tertiary shrink-0 transition-transform ${expanded ? "" : "-rotate-90"}`}
          />
          <Bot className="w-3.5 h-3.5 text-tertiary shrink-0" />
          <span className="flex-1 min-w-0">
            <span className="block text-[13px] font-semibold text-primary truncate">{name}</span>
            <span className="block text-[10.5px] text-tertiary truncate">{summary}</span>
          </span>
          <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-medium text-secondary">
            <PencilLine className="w-3 h-3" />
            {expanded ? t("editing") : t("edit")}
          </span>
        </button>
        {hasDetails && !expanded && (
          <span className="text-[10px] text-tertiary bg-[var(--accent-bg)] px-1.5 py-0.5 rounded">
            {t("custom")}
          </span>
        )}
        <button
          type="button"
          onClick={onDelete}
          className="icon-touch sm:min-h-8 sm:min-w-8 rounded text-tertiary hover:text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors shrink-0 flex items-center justify-center"
          title={t("removeAgentNamed", { name })}
          aria-label={t("removeAgentNamed", { name })}
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>

      {expanded && (
        <div className="px-3 pb-3 pt-1 space-y-3 animate-stagger">
          <div className="rounded-md border border-default bg-[var(--bg-hover)]/35 p-3 space-y-3">
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-tertiary">
              <Bot className="w-3 h-3" />
              {t("common")}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <FieldLabel required>{t("agentName")}</FieldLabel>
                <TextInput
                  value={draftName}
                  onChange={setDraftName}
                  onBlur={commitName}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.currentTarget.blur();
                    }
                  }}
                  placeholder="codex"
                  invalid={!draftName.trim()}
                />
              </div>
              <div>
                <FieldLabel required>{t("command")}</FieldLabel>
                <TextInput
                  value={agent.command}
                  onChange={(v) => onChange({ command: v })}
                  placeholder="claude"
                />
              </div>
              <div>
                <FieldLabel>{t("resumeMode")}</FieldLabel>
                <SelectInput
                  value={agent.resume_mode}
                  onChange={(v) => onChange({ resume_mode: v as AgentConfig["resume_mode"] })}
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
                  onChange={(v) => onChange({ create_mode: v as AgentConfig["create_mode"] })}
                  options={[
                    { value: "none", label: t("none") },
                    { value: "generated_uuid", label: t("generatedUuid") },
                  ]}
                />
              </div>
            </div>
          </div>

          <details className="rounded-md border border-default bg-[var(--bg-card)]">
            <summary className="flex items-center gap-2 px-3 py-2 cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-tertiary hover:text-secondary">
              <SlidersHorizontal className="w-3 h-3" />
              {t("advanced")}
            </summary>
            <div className="px-3 pb-3 pt-1 space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {agent.resume_mode !== "none" && (
                  <div>
                    <FieldLabel>{t("resumeTemplate")}</FieldLabel>
                    <TextInput
                      value={agent.resume_template}
                      onChange={(v) => onChange({ resume_template: v })}
                      placeholder="-r {session_id}"
                    />
                  </div>
                )}
                {agent.create_mode !== "none" && (
                  <div>
                    <FieldLabel>{t("createTemplate")}</FieldLabel>
                    <TextInput
                      value={agent.create_template}
                      onChange={(v) => onChange({ create_template: v })}
                      placeholder="claude --session-id {session_id}"
                    />
                  </div>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <FieldLabel>{t("labelTemplate")}</FieldLabel>
                  <TextInput
                    value={agent.label_template}
                    onChange={(v) => onChange({ label_template: v })}
                    placeholder="{project}/{slot}/{window}"
                  />
                </div>
                <div>
                  <FieldLabel>{t("labelMode")}</FieldLabel>
                  <SelectInput
                    value={agent.label_mode}
                    onChange={(v) => onChange({ label_mode: v as AgentConfig["label_mode"] })}
                    options={[
                      { value: "metadata", label: t("metadata") },
                      { value: "internal", label: t("internal") },
                    ]}
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <FieldLabel>{t("renameTemplate")}</FieldLabel>
                  <TextInput
                    value={agent.rename_template}
                    onChange={(v) => onChange({ rename_template: v })}
                    placeholder="tmux rename-window {label}"
                  />
                </div>
              </div>
            </div>
          </details>
        </div>
      )}
    </div>
  );
}

export default function AgentsSection({
  agents,
  onChange,
  expanded,
  onToggle,
}: {
  agents: Record<string, AgentConfig>;
  onChange: (agents: Record<string, AgentConfig>, rename?: { from: string; to: string }) => void;
  expanded: boolean;
  onToggle: () => void;
}) {
  const { t } = useI18n();
  const [newlyAddedName, setNewlyAddedName] = useState<string | null>(null);
  const [error, setError] = useState("");

  const entries = Object.entries(agents);

  function nextAgentName() {
    const names = new Set(Object.keys(agents));
    let i = entries.length + 1;
    let name = `agent-${i}`;
    while (names.has(name)) {
      i += 1;
      name = `agent-${i}`;
    }
    return name;
  }

  function addAgent() {
    const name = nextAgentName();
    setError("");
    setNewlyAddedName(name);
    onChange({
      ...agents,
      [name]: {
        command: name,
        resume_mode: "none",
        resume_template: "",
        create_mode: "generated_uuid",
        create_template: `${name} --session-id {{session_id}}`,
        label_template: "{project}/{slot}/{window}",
        label_mode: "metadata",
        rename_template: "",
      },
    });
  }

  function renameAgent(currentName: string, nextNameRaw: string): boolean {
    const nextName = nextNameRaw.trim();
    if (!nextName) {
      setError(t("agentNameRequired"));
      return false;
    }
    if (nextName !== currentName && agents[nextName]) {
      setError(t("agentAlreadyExists", { name: nextName }));
      return false;
    }
    if (nextName === currentName) {
      setError("");
      return true;
    }

    const nextAgents: Record<string, AgentConfig> = {};
    for (const [name, agent] of entries) {
      if (name === currentName) {
        nextAgents[nextName] = {
          ...agent,
          command: agent.command === currentName ? nextName : agent.command,
        };
      } else {
        nextAgents[name] = agent;
      }
    }
    setError("");
    setNewlyAddedName(nextName);
    onChange(nextAgents, { from: currentName, to: nextName });
    return true;
  }

  function updateAgent(name: string, patch: Partial<AgentConfig>) {
    onChange({
      ...agents,
      [name]: { ...agents[name], ...patch },
    });
  }

  function deleteAgent(name: string) {
    const next = { ...agents };
    delete next[name];
    onChange(next);
  }

  return (
    <section className="rounded-md transition-colors">
      <div className={`px-4 py-3 flex items-center justify-between rounded-md transition-colors ${
        expanded ? "bg-[var(--bg-hover)]/45" : "hover:surface-hover"
      }`}>
        <button
          type="button"
          onClick={onToggle}
          className="flex items-center gap-2 text-left group flex-1 min-w-0 control-touch"
          aria-label={expanded ? t("collapseAgentsSection") : t("expandAgentsSection")}
        >
          <ChevronDown
            className={`w-3.5 h-3.5 text-tertiary shrink-0 transition-transform ${
              expanded ? "" : "-rotate-90"
            }`}
          />
          <Bot className="w-3.5 h-3.5 text-tertiary shrink-0" />
          <div className="min-w-0">
            <span className="text-[13px] font-semibold text-primary">{t("agentOverrides")}</span>
            <span className="text-[11px] text-tertiary ml-2">
              {t("agentOverridesDefined", { count: entries.length })}
            </span>
          </div>
        </button>
        <button
          type="button"
          onClick={() => {
            addAgent();
            if (!expanded) onToggle();
          }}
          className="control-touch px-3 rounded-md text-[12px] font-medium bg-[var(--accent)] text-[var(--text-on-accent)] hover:bg-[var(--accent-light)] transition-colors flex items-center gap-1.5 shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          {t("add")}
        </button>
      </div>

      <CollapsibleSection expanded={expanded}>
        <div className="space-y-2">
          <p className="text-[11px] text-tertiary leading-relaxed px-1">
            {t("agentOverridesHint")}
          </p>
          {entries.map(([name, agent]) => (
            <AgentCard
              key={name}
              name={name}
              agent={agent}
              onChange={(p) => updateAgent(name, p)}
              onRename={(nextName) => renameAgent(name, nextName)}
              onDelete={() => deleteAgent(name)}
              initialExpanded={newlyAddedName === name}
            />
          ))}

          {entries.length === 0 && (
            <div className="text-center py-6 border border-dashed border-default rounded-md">
              <Bot className="w-5 h-5 text-tertiary mx-auto mb-1.5" />
              <p className="text-[12px] text-secondary">{t("noAgentsYet")}</p>
              <p className="text-[11px] text-tertiary mt-0.5">
                {t("addAgentHint")}
              </p>
            </div>
          )}
          {error && <InlineError message={error} />}
        </div>
      </CollapsibleSection>
    </section>
  );
}
