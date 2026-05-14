import { ChevronDown } from "lucide-react";
import { useI18n } from "../../i18n";
import type { WorkspaceScope } from "../../types";
import type { SlotConfig, WindowConfig } from "./types";
import {
  FieldLabel,
  KeyValueList,
  SelectInput,
  TextInput,
} from "./FormPrimitives";
import LayoutPicker from "./LayoutPicker";
import SessionInput from "./SessionInput";
import type { TabLayout } from "./workspace-model";

type SelectOption = { value: string; label: string };

export function TabEditor({
  slot,
  layoutOptions,
  onChange,
}: {
  slot: SlotConfig;
  layoutOptions: SelectOption[];
  onChange: (patch: Partial<SlotConfig>) => void;
}) {
  const { t } = useI18n();

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("tab")}</p>
        <span className="text-[10px] text-tertiary">{t("tabGroup")}</span>
      </div>
      <div>
        <FieldLabel required>{t("tabName")}</FieldLabel>
        <TextInput
          value={slot.name}
          onChange={(value) => onChange({ name: value })}
          placeholder="coding"
          invalid={!slot.name.trim()}
        />
      </div>
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 xl:grid-cols-1">
        <div>
          <FieldLabel>{t("tabLayout")}</FieldLabel>
          <LayoutPicker
            value={slot.layout || "auto"}
            options={layoutOptions}
            onChange={(value) => onChange({ layout: value as TabLayout })}
          />
        </div>
      </div>
    </section>
  );
}

export function TerminalPaneEditor({
  slot,
  window,
  agentOptions,
  scope,
  onSlotChange,
  onWindowChange,
}: {
  slot: SlotConfig;
  window: WindowConfig | null;
  agentOptions: SelectOption[];
  scope?: WorkspaceScope;
  onSlotChange: (patch: Partial<SlotConfig>) => void;
  onWindowChange: (patch: Partial<WindowConfig>) => void;
}) {
  const { t } = useI18n();
  const agent = window?.agent ?? slot.agent;
  const titleValue = window?.name ?? slot.title ?? slot.name ?? "";

  return (
    <div className="space-y-2.5">
      <div>
        <FieldLabel>{t("title")}</FieldLabel>
        <TextInput
          value={titleValue}
          onChange={(value) => {
            if (window) onWindowChange({ name: value });
            else onSlotChange({ title: value || undefined });
          }}
          placeholder="main"
        />
      </div>
      <div>
        <FieldLabel>{t("agent")}</FieldLabel>
        <SelectInput
          value={agent ?? ""}
          onChange={(value) => {
            if (window) {
              onWindowChange({
                agent: value || null,
                command: value ? null : window.command,
                session: value ? window.session ?? "auto" : null,
              });
            } else {
              onSlotChange({
                agent: value || undefined,
                command: value ? undefined : slot.command,
                session: value ? slot.session ?? "auto" : undefined,
              });
            }
          }}
          options={agentOptions}
        />
      </div>
      {agent ? (
        <div>
          <FieldLabel>{t("agentSession")}</FieldLabel>
          <SessionInput
            value={window?.session ?? window?.session_id ?? slot.session ?? slot.session_id ?? "auto"}
            onChange={(value) => {
              if (window) onWindowChange({ session: value || null, session_id: null });
              else onSlotChange({ session: value || undefined, session_id: undefined });
            }}
            agent={agent}
            scope={scope}
          />
        </div>
      ) : (
        <div>
          <FieldLabel>{t("shellCommand")}</FieldLabel>
          <TextInput
            value={window?.command ?? slot.command ?? ""}
            onChange={(value) => {
              if (window) onWindowChange({ command: value || null });
              else onSlotChange({ command: value || undefined });
            }}
            placeholder="$SHELL"
          />
        </div>
      )}
      <details className="group rounded-md border border-default bg-[var(--bg-card)]">
        <summary className="flex cursor-pointer items-center gap-2 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-tertiary hover:text-secondary">
          <ChevronDown className="h-3 w-3 transition-transform group-open:rotate-180" />
          {t("advanced")}
        </summary>
        <div className="space-y-2.5 px-3 pb-3 pt-1">
          <div>
            <FieldLabel>{t("workingDirectory")}</FieldLabel>
            <TextInput
              value={window?.cwd ?? slot.cwd ?? ""}
              onChange={(value) => {
                if (window) onWindowChange({ cwd: value || null });
                else onSlotChange({ cwd: value || "." });
              }}
              placeholder="."
            />
          </div>
          <div>
            <FieldLabel>{t("environmentVariables")}</FieldLabel>
            <KeyValueList
              items={window?.env ?? slot.env}
              onChange={(env) => {
                if (window) onWindowChange({ env });
                else onSlotChange({ env });
              }}
            />
          </div>
        </div>
      </details>
    </div>
  );
}

export function AgentPaneEditor({
  window,
  agentOptions,
  scope,
  onChange,
}: {
  window: WindowConfig;
  agentOptions: SelectOption[];
  scope?: WorkspaceScope;
  onChange: (patch: Partial<WindowConfig>) => void;
}) {
  const { t } = useI18n();

  return (
    <div className="space-y-2.5">
      <div>
        <FieldLabel required>{t("paneName")}</FieldLabel>
        <TextInput
          value={window.name}
          onChange={(value) => onChange({ name: value })}
          placeholder="builder"
          invalid={!window.name.trim()}
        />
      </div>
      <div>
        <FieldLabel>{t("agent")}</FieldLabel>
        <SelectInput
          value={window.agent ?? ""}
          onChange={(value) => onChange({
            agent: value || null,
            session: value ? window.session ?? "auto" : null,
          })}
          options={agentOptions}
        />
      </div>
      <div>
        <FieldLabel>{t("agentSession")}</FieldLabel>
        <SessionInput
          value={window.session ?? window.session_id ?? "auto"}
          onChange={(value) => onChange({ session: value || null, session_id: null })}
          agent={window.agent}
          scope={scope}
        />
      </div>
      <details className="group rounded-md border border-default bg-[var(--bg-card)]">
        <summary className="flex cursor-pointer items-center gap-2 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-tertiary hover:text-secondary">
          <ChevronDown className="h-3 w-3 transition-transform group-open:rotate-180" />
          {t("advanced")}
        </summary>
        <div className="space-y-2.5 px-3 pb-3 pt-1">
          <div>
            <FieldLabel>{t("commandOverride")}</FieldLabel>
            <TextInput
              value={window.command ?? ""}
              onChange={(value) => onChange({ command: value || null })}
              placeholder="npm run dev"
            />
          </div>
          <div>
            <FieldLabel>{t("workingDirectory")}</FieldLabel>
            <TextInput
              value={window.cwd ?? ""}
              onChange={(value) => onChange({ cwd: value || null })}
              placeholder={t("relativeToSlotCwd")}
            />
          </div>
          <div>
            <FieldLabel>{t("label")}</FieldLabel>
            <TextInput
              value={window.label ?? ""}
              onChange={(value) => onChange({ label: value || null })}
              placeholder={t("overrideLabel")}
            />
          </div>
          <div>
            <FieldLabel>{t("environmentVariables")}</FieldLabel>
            <KeyValueList
              items={window.env}
              onChange={(env) => onChange({ env })}
            />
          </div>
        </div>
      </details>
    </div>
  );
}
