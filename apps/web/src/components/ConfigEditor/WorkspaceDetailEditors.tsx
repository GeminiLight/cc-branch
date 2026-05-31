import { Bot, ChevronDown, Laptop, Power, Server, Terminal } from "lucide-react";
import { useI18n } from "../../i18n";
import type { SshHostInfo, WorkspaceScope } from "../../types";
import type { RemoteSetting, SlotConfig, WindowConfig } from "./types";
import {
  FieldLabel,
  KeyValueList,
  SelectInput,
  TextInput,
} from "./FormPrimitives";
import LayoutPicker from "./LayoutPicker";
import RemoteRunEditor from "./RemoteRunEditor";
import SessionInput from "./SessionInput";
import type { TabLayout } from "./workspace-model";

type SelectOption = { value: string; label: string };

function isRemoteConfig(remote: RemoteSetting | undefined): remote is Exclude<RemoteSetting, false | null | undefined> {
  return typeof remote === "object" && remote !== null;
}

function remoteLabel(remote: RemoteSetting | undefined, inheritedRemote?: RemoteSetting): string | null {
  const target = isRemoteConfig(remote) ? remote : isRemoteConfig(inheritedRemote) && remote !== false ? inheritedRemote : null;
  if (!target?.host?.trim()) return null;
  const user = target.user?.trim() ? `${target.user.trim()}@` : "";
  const port = target.port ? `:${target.port}` : "";
  return `${user}${target.host.trim()}${port}`;
}

function sessionLabel(t: (key: string, values?: Record<string, string | number>) => string, value: string | null | undefined): string {
  if (!value || value === "auto") return t("sessionAutoSummary");
  if (value === "fresh") return t("sessionFreshSummary");
  return t("sessionResumeSummary", { id: value.length > 14 ? `${value.slice(0, 8)}...` : value });
}

function PaneRunSummary({
  launchEnabled,
  agent,
  command,
  session,
  remote,
  inheritedRemote,
}: {
  launchEnabled: boolean;
  agent?: string | null;
  command?: string | null;
  session?: string | null;
  remote?: RemoteSetting;
  inheritedRemote?: RemoteSetting;
}) {
  const { t } = useI18n();
  const sshTarget = remoteLabel(remote, inheritedRemote);
  const runLocal = !sshTarget || remote === false;
  const rows = [
    {
      icon: Power,
      label: t("launchPlan"),
      value: launchEnabled ? t("launchEnabledSummary") : t("launchDisabledSummary"),
    },
    {
      icon: agent ? Bot : Terminal,
      label: agent ? t("agent") : t("launchCommand"),
      value: agent || command || "$SHELL",
    },
    {
      icon: Bot,
      label: t("sessionBehavior"),
      value: agent ? sessionLabel(t, session) : t("notUsed"),
      muted: !agent,
    },
    {
      icon: runLocal ? Laptop : Server,
      label: t("runLocation"),
      value: runLocal ? t("localMachine") : t("remoteRunsOn", { target: sshTarget || "" }),
    },
  ];

  return (
    <section className="rounded-md border border-subtle bg-[var(--bg-hover)]/25 px-3 py-2.5">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-1">
        {rows.map(({ icon: Icon, label, value, muted }) => (
          <div key={label} className="flex min-w-0 items-start gap-2">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border border-default bg-[var(--bg-card)] text-tertiary">
              <Icon className="h-3 w-3" aria-hidden="true" />
            </span>
            <span className="min-w-0">
              <span className="block text-[9px] font-semibold uppercase tracking-wide text-tertiary">{label}</span>
              <span className={`mt-0.5 block truncate text-[11.5px] font-medium ${muted ? "text-tertiary" : "text-primary"}`}>
                {value}
              </span>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

export function LaunchToggle({
  enabled,
  onChange,
}: {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-default bg-[var(--bg-card)] px-3 py-2">
      <div className="min-w-0">
        <p className="text-[12px] font-semibold text-primary">{t("openOnLaunch")}</p>
        <p className="mt-0.5 text-[10.5px] text-tertiary">{t("openOnLaunchHint")}</p>
      </div>
      <button
        type="button"
        onClick={() => onChange(!enabled)}
        className={`relative h-6 w-10 shrink-0 rounded-full border transition-colors ${
          enabled ? "border-[var(--accent)] bg-[var(--accent)]" : "border-default bg-[var(--bg-page)]"
        }`}
        aria-pressed={enabled}
        aria-label={enabled ? t("disableLaunch") : t("enableLaunch")}
        title={enabled ? t("disableLaunch") : t("enableLaunch")}
      >
        <span
          className={`absolute top-0.5 h-[18px] w-[18px] rounded-full bg-white shadow-sm transition-transform ${
            enabled ? "translate-x-[18px]" : "translate-x-0.5"
          }`}
        />
      </button>
    </div>
  );
}

export function DefaultShellCommandHint({
  defaultShellName,
  value,
  onUseDefaultShell,
}: {
  defaultShellName?: string | null;
  value: string;
  onUseDefaultShell: () => void;
}) {
  const { t } = useI18n();
  const isUsingDefault = value.trim() === "$SHELL";

  return (
    <div className="mt-1.5 flex items-center justify-between gap-2">
      <p className="min-w-0 truncate text-[10.5px] text-tertiary">
        {defaultShellName
          ? t("defaultShellResolved", { shell: defaultShellName })
          : t("defaultShellFallbackHint")}
      </p>
      <button
        type="button"
        onClick={onUseDefaultShell}
        disabled={isUsingDefault}
        className="shrink-0 rounded-md border border-default bg-[var(--bg-card)] px-2 py-1 text-[10.5px] font-semibold text-secondary transition-colors hover:border-[var(--border-strong)] hover:text-primary disabled:cursor-default disabled:opacity-45"
      >
        {isUsingDefault ? t("usingDefaultShell") : t("useDefaultShell")}
      </button>
    </div>
  );
}

export function TabEditor({
  slot,
  layoutOptions,
  sshHosts,
  onChange,
}: {
  slot: SlotConfig;
  layoutOptions: SelectOption[];
  sshHosts?: SshHostInfo[];
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
      <RemoteRunEditor
        value={slot.remote}
        sshHosts={sshHosts}
        onChange={(remote) => onChange({ remote })}
      />
    </section>
  );
}

export function TerminalPaneEditor({
  slot,
  window,
  agentOptions,
  scope,
  defaultShellName,
  sshHosts,
  onSlotChange,
  onWindowChange,
  launchEnabled = true,
  onLaunchEnabledChange,
}: {
  slot: SlotConfig;
  window: WindowConfig | null;
  agentOptions: SelectOption[];
  scope?: WorkspaceScope;
  defaultShellName?: string | null;
  sshHosts?: SshHostInfo[];
  onSlotChange: (patch: Partial<SlotConfig>) => void;
  onWindowChange: (patch: Partial<WindowConfig>) => void;
  launchEnabled?: boolean;
  onLaunchEnabledChange?: (enabled: boolean) => void;
}) {
  const { t } = useI18n();
  const agent = window?.agent ?? slot.agent;
  const titleValue = window?.name ?? slot.title ?? slot.name ?? "";
  const commandValue = window?.command ?? slot.command ?? "";
  const remoteValue: RemoteSetting | undefined = window ? window.remote : slot.remote;

  return (
    <div className="space-y-2.5">
      <PaneRunSummary
        launchEnabled={launchEnabled}
        agent={agent}
        command={commandValue}
        session={window?.session ?? slot.session ?? "auto"}
        remote={remoteValue}
        inheritedRemote={window ? slot.remote : undefined}
      />
      <LaunchToggle
        enabled={launchEnabled}
        onChange={(enabled) => {
          if (onLaunchEnabledChange) onLaunchEnabledChange(enabled);
          else if (window) onWindowChange({ enabled });
        }}
      />
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
            value={window?.session ?? slot.session ?? "auto"}
            onChange={(value) => {
              if (window) onWindowChange({ session: value || null });
              else onSlotChange({ session: value || undefined });
            }}
            agent={agent}
            scope={scope}
          />
        </div>
      ) : (
        <div>
          <FieldLabel>{t("shellCommand")}</FieldLabel>
          <TextInput
            value={commandValue}
            onChange={(value) => {
              if (window) onWindowChange({ command: value || null });
              else onSlotChange({ command: value || undefined });
            }}
            placeholder="$SHELL"
          />
          <DefaultShellCommandHint
            defaultShellName={defaultShellName}
            value={commandValue}
            onUseDefaultShell={() => {
              if (window) onWindowChange({ command: "$SHELL" });
              else onSlotChange({ command: "$SHELL" });
            }}
          />
        </div>
      )}
      <RemoteRunEditor
        value={remoteValue}
        inheritedRemote={window ? slot.remote : undefined}
        sshHosts={sshHosts}
        onChange={(remote) => {
          if (window) onWindowChange({ remote });
          else onSlotChange({ remote });
        }}
      />
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
  inheritedRemote,
  sshHosts,
  onChange,
}: {
  window: WindowConfig;
  agentOptions: SelectOption[];
  scope?: WorkspaceScope;
  inheritedRemote?: RemoteSetting;
  sshHosts?: SshHostInfo[];
  onChange: (patch: Partial<WindowConfig>) => void;
}) {
  const { t } = useI18n();

  return (
    <div className="space-y-2.5">
      <PaneRunSummary
        launchEnabled={window.enabled !== false}
        agent={window.agent}
        command={window.command}
        session={window.session ?? "auto"}
        remote={window.remote}
        inheritedRemote={inheritedRemote}
      />
      <LaunchToggle enabled={window.enabled !== false} onChange={(enabled) => onChange({ enabled })} />
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
          value={window.session ?? "auto"}
          onChange={(value) => onChange({ session: value || null })}
          agent={window.agent}
          scope={scope}
        />
      </div>
      <RemoteRunEditor
        value={window.remote}
        inheritedRemote={inheritedRemote}
        sshHosts={sshHosts}
        onChange={(remote) => onChange({ remote })}
      />
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
