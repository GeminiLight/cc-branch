/**
 * ConfigEditor — Agents management section.
 */

import { useState } from "react";
import { Bot, Plus, Trash2, ChevronDown } from "lucide-react";
import type { AgentConfig } from "./types";
import {
  SectionHeader,
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
  onDelete,
}: {
  name: string;
  agent: AgentConfig;
  onChange: (patch: Partial<AgentConfig>) => void;
  onDelete: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails =
    agent.resume_mode !== "none" ||
    agent.create_mode !== "none" ||
    agent.label_template ||
    agent.rename_template;

  return (
    <div className="border border-default rounded-md">
      <div className="flex items-center gap-2 px-2.5 py-2">
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="p-0.5 rounded text-tertiary hover:text-primary transition-colors shrink-0"
        >
          <ChevronDown
            className={`w-3.5 h-3.5 transition-transform ${expanded ? "" : "-rotate-90"}`}
          />
        </button>
        <div className="flex-1 min-w-0">
          <span className="text-[13px] font-medium text-primary">{name}</span>
          {agent.command && (
            <code className="ml-2 text-[11px] text-tertiary font-mono">{agent.command}</code>
          )}
        </div>
        {hasDetails && !expanded && (
          <span className="text-[10px] text-tertiary bg-[var(--accent-bg)] px-1.5 py-0.5 rounded">
            custom
          </span>
        )}
        <button
          type="button"
          onClick={onDelete}
          className="p-1 rounded text-tertiary hover:text-[var(--danger)] hover:bg-[var(--danger-bg)] transition-colors shrink-0"
          title="Remove agent"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>

      {expanded && (
        <div className="px-3 pb-3 pt-1 space-y-3 border-t border-default animate-stagger">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <FieldLabel required>Command</FieldLabel>
              <TextInput
                value={agent.command}
                onChange={(v) => onChange({ command: v })}
                placeholder="claude"
              />
            </div>
            <div>
              <FieldLabel>Label template</FieldLabel>
              <TextInput
                value={agent.label_template}
                onChange={(v) => onChange({ label_template: v })}
                placeholder="{project}/{slot}/{window}"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <FieldLabel>Resume mode</FieldLabel>
              <SelectInput
                value={agent.resume_mode}
                onChange={(v) => onChange({ resume_mode: v as AgentConfig["resume_mode"] })}
                options={[
                  { value: "none", label: "None" },
                  { value: "flag", label: "Flag (-r)" },
                  { value: "internal", label: "Internal command" },
                ]}
              />
            </div>
            {agent.resume_mode !== "none" && (
              <div>
                <FieldLabel>Resume template</FieldLabel>
                <TextInput
                  value={agent.resume_template}
                  onChange={(v) => onChange({ resume_template: v })}
                  placeholder="-r {session_id}"
                />
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <FieldLabel>Create mode</FieldLabel>
              <SelectInput
                value={agent.create_mode}
                onChange={(v) => onChange({ create_mode: v as AgentConfig["create_mode"] })}
                options={[
                  { value: "none", label: "None" },
                  { value: "generated_uuid", label: "Generated UUID" },
                ]}
              />
            </div>
            {agent.create_mode !== "none" && (
              <div>
                <FieldLabel>Create template</FieldLabel>
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
              <FieldLabel>Label mode</FieldLabel>
              <SelectInput
                value={agent.label_mode}
                onChange={(v) => onChange({ label_mode: v as AgentConfig["label_mode"] })}
                options={[
                  { value: "metadata", label: "Metadata" },
                  { value: "internal", label: "Internal" },
                ]}
              />
            </div>
            <div>
              <FieldLabel>Rename template</FieldLabel>
              <TextInput
                value={agent.rename_template}
                onChange={(v) => onChange({ rename_template: v })}
                placeholder="tmux rename-window {label}"
              />
            </div>
          </div>
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
  onChange: (agents: Record<string, AgentConfig>) => void;
  expanded: boolean;
  onToggle: () => void;
}) {
  const [newName, setNewName] = useState("");
  const [error, setError] = useState("");

  const entries = Object.entries(agents);

  function addAgent() {
    const name = newName.trim();
    if (!name) {
      setError("Agent name is required");
      return;
    }
    if (agents[name]) {
      setError(`Agent "${name}" already exists`);
      return;
    }
    setError("");
    setNewName("");
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
    <div className="border border-default rounded-lg surface-card">
      <SectionHeader
        title="Agents"
        subtitle={`${entries.length} defined`}
        icon={<Bot className="w-3.5 h-3.5" />}
        expanded={expanded}
        onToggle={onToggle}
      />
      <CollapsibleSection expanded={expanded}>
        <div className="space-y-2">
          {entries.map(([name, agent]) => (
            <AgentCard
              key={name}
              name={name}
              agent={agent}
              onChange={(p) => updateAgent(name, p)}
              onDelete={() => deleteAgent(name)}
            />
          ))}

          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newName}
              onChange={(e) => {
                setNewName(e.target.value);
                setError("");
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") addAgent();
              }}
              placeholder="New agent name…"
              className="flex-1 h-8 px-2.5 rounded-md border border-default text-[13px] bg-[var(--bg-card)] transition-colors focus:outline-none focus:border-[var(--accent)]"
            />
            <button
              type="button"
              onClick={addAgent}
              disabled={!newName.trim()}
              className="h-8 px-3 rounded-md text-[12px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" />
              Add
            </button>
          </div>
          {error && <InlineError message={error} />}
        </div>
      </CollapsibleSection>
    </div>
  );
}
