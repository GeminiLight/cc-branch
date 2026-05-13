import { ArrowDown, ArrowUp, ChevronDown, Plus, Trash2 } from "lucide-react";
import { useI18n } from "../../i18n";
import type { WorkspaceScope } from "../../types";
import AgentMark, { displayAgentName } from "../ui/AgentMark";
import type { WindowConfig } from "./types";
import {
  FieldLabel,
  KeyValueList,
  SelectInput,
  TextInput,
} from "./FormPrimitives";
import SessionInput from "./SessionInput";
import { countText } from "./workspace-display";

type AgentOption = { value: string; label: string };

export default function TmuxGroupEditor({
  groupName,
  windows,
  agentOptions,
  scope,
  onGroupNameChange,
  onAddWindow,
  onMoveWindow,
  onDeleteWindow,
  onUpdateWindow,
}: {
  groupName: string;
  windows: WindowConfig[];
  agentOptions: AgentOption[];
  scope?: WorkspaceScope;
  onGroupNameChange: (value: string) => void;
  onAddWindow: () => void;
  onMoveWindow: (windowIndex: number, dir: number) => void;
  onDeleteWindow: (windowIndex: number) => void;
  onUpdateWindow: (windowIndex: number, patch: Partial<WindowConfig>) => void;
}) {
  const { t } = useI18n();

  return (
    <div className="space-y-3">
      <div>
        <FieldLabel required>{t("paneName")}</FieldLabel>
        <TextInput
          value={groupName}
          onChange={onGroupNameChange}
          placeholder="tmux"
          invalid={!groupName.trim()}
        />
      </div>
      <div className="rounded-md border border-default bg-[var(--bg-hover)]/30 p-2.5">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("tmuxWindows")}</p>
            <p className="mt-0.5 text-[11px] text-tertiary">
              {countText(t, "tmuxWindowGroupSummary_one", "tmuxWindowGroupSummary", windows.length)}
            </p>
          </div>
          <button
            type="button"
            onClick={onAddWindow}
            className="control-touch rounded-md border border-default bg-[var(--bg-card)] px-2.5 text-[11px] font-semibold text-secondary hover:border-[var(--border-strong)] hover:text-primary transition-colors inline-flex items-center gap-1.5"
          >
            <Plus className="h-3.5 w-3.5 text-tertiary" />
            {t("addTmuxWindow")}
          </button>
        </div>
        <div className="mt-2 space-y-2">
          {windows.map((window, windowIndex) => (
            <div
              key={`${window.name}-${windowIndex}-detail`}
              className="rounded-md border border-default bg-[var(--bg-card)] p-2 shadow-sm"
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  <AgentMark agent={window.agent} compact />
                  <div className="min-w-0">
                    <p className="truncate text-[12px] font-semibold text-primary">{window.name || t("unnamed")}</p>
                    <p className="truncate text-[10px] text-tertiary">
                      {window.agent ? displayAgentName(window.agent) : window.command || "$SHELL"}
                    </p>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <button
                    type="button"
                    onClick={() => onMoveWindow(windowIndex, -1)}
                    disabled={windowIndex === 0}
                    className="icon-touch sm:min-h-7 sm:min-w-7 rounded-md text-tertiary hover:bg-[var(--bg-hover)] hover:text-primary disabled:opacity-30"
                    aria-label={t("moveUp")}
                    title={t("moveUp")}
                  >
                    <ArrowUp className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onMoveWindow(windowIndex, 1)}
                    disabled={windowIndex >= windows.length - 1}
                    className="icon-touch sm:min-h-7 sm:min-w-7 rounded-md text-tertiary hover:bg-[var(--bg-hover)] hover:text-primary disabled:opacity-30"
                    aria-label={t("moveDown")}
                    title={t("moveDown")}
                  >
                    <ArrowDown className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onDeleteWindow(windowIndex)}
                    disabled={windows.length <= 1}
                    className="icon-touch sm:min-h-7 sm:min-w-7 rounded-md text-tertiary hover:bg-[var(--danger-bg)] hover:text-[var(--danger)] disabled:opacity-30"
                    aria-label={t("removeTmuxWindow")}
                    title={t("removeTmuxWindow")}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-1 gap-2">
                <div>
                  <FieldLabel required>{t("tmuxWindow")}</FieldLabel>
                  <TextInput
                    value={window.name}
                    onChange={(value) => onUpdateWindow(windowIndex, { name: value })}
                    placeholder="main"
                    invalid={!window.name.trim()}
                  />
                </div>
                <div>
                  <FieldLabel>{t("agent")}</FieldLabel>
                  <SelectInput
                    value={window.agent ?? ""}
                    onChange={(value) => onUpdateWindow(windowIndex, {
                      agent: value || null,
                      command: value ? null : window.command,
                      session: value ? window.session ?? "auto" : null,
                    })}
                    options={agentOptions}
                  />
                </div>
                {window.agent ? (
                  <div>
                    <FieldLabel>{t("agentSession")}</FieldLabel>
                    <SessionInput
                      value={window.session ?? window.session_id ?? "auto"}
                      onChange={(value) => onUpdateWindow(windowIndex, { session: value || null, session_id: null })}
                      agent={window.agent}
                      scope={scope}
                    />
                  </div>
                ) : (
                  <div>
                    <FieldLabel>{t("shellCommand")}</FieldLabel>
                    <TextInput
                      value={window.command ?? ""}
                      onChange={(value) => onUpdateWindow(windowIndex, { command: value || null })}
                      placeholder="$SHELL"
                    />
                  </div>
                )}
              </div>
              <details className="group mt-2 rounded-md border border-subtle bg-[var(--bg-hover)]/25">
                <summary className="flex items-center gap-2 px-2.5 py-2 cursor-pointer text-[10px] font-semibold uppercase tracking-wide text-tertiary hover:text-secondary">
                  <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" />
                  {t("advanced")}
                </summary>
                <div className="px-2.5 pb-2.5 pt-0 space-y-2.5">
                  <div>
                    <FieldLabel>{t("workingDirectory")}</FieldLabel>
                    <TextInput
                      value={window.cwd ?? ""}
                      onChange={(value) => onUpdateWindow(windowIndex, { cwd: value || null })}
                      placeholder={t("relativeToSlotCwd")}
                    />
                  </div>
                  <div>
                    <FieldLabel>{t("label")}</FieldLabel>
                    <TextInput
                      value={window.label ?? ""}
                      onChange={(value) => onUpdateWindow(windowIndex, { label: value || null })}
                      placeholder={t("overrideLabel")}
                    />
                  </div>
                  <div>
                    <FieldLabel>{t("environmentVariables")}</FieldLabel>
                    <KeyValueList
                      items={window.env}
                      onChange={(env) => onUpdateWindow(windowIndex, { env })}
                    />
                  </div>
                </div>
              </details>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
