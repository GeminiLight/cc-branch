import { Laptop, Server, Undo2 } from "lucide-react";
import { useMemo } from "react";
import { useI18n } from "../../i18n";
import type { SshHostInfo } from "../../types";
import type { RemoteConfig, RemoteSetting } from "./types";
import {
  FieldLabel,
  HelpText,
  KeyValueList,
  SelectInput,
  TextInput,
} from "./FormPrimitives";

type RemoteMode = "inherit" | "local" | "ssh";

function isRemoteConfig(remote: RemoteSetting | undefined): remote is RemoteConfig {
  return typeof remote === "object" && remote !== null;
}

function compactRemote(remote: RemoteConfig): RemoteConfig | null {
  const next: RemoteConfig = {};
  if (remote.host?.trim()) next.host = remote.host.trim();
  if (remote.user?.trim()) next.user = remote.user.trim();
  if (remote.port != null && Number.isFinite(remote.port)) next.port = remote.port;
  if (remote.cwd?.trim()) next.cwd = remote.cwd.trim();
  if (remote.args && remote.args.length > 0) next.args = remote.args.filter((arg) => arg.trim());
  if (remote.options && Object.keys(remote.options).length > 0) next.options = remote.options;
  return Object.keys(next).length > 0 ? next : null;
}

function remoteSummary(remote: RemoteSetting | undefined): string {
  if (!isRemoteConfig(remote)) return "";
  const host = remote.host?.trim();
  if (!host) return "";
  return `${remote.user?.trim() ? `${remote.user.trim()}@` : ""}${host}${remote.port ? `:${remote.port}` : ""}`;
}

function argsText(remote: RemoteConfig): string {
  return (remote.args ?? []).join(" ");
}

function optionsToStrings(options: Record<string, unknown> | undefined): Record<string, string> {
  return Object.fromEntries(
    Object.entries(options ?? {}).map(([key, value]) => [key, value == null ? "" : String(value)])
  );
}

function sshTargetLabel(host: SshHostInfo): string {
  const target = host.hostname && host.hostname !== host.alias ? host.hostname : "";
  const user = host.user ? `${host.user}@` : "";
  const port = host.port ? `:${host.port}` : "";
  return target ? `${host.alias} (${user}${target}${port})` : `${host.alias}${host.user || host.port ? ` (${user}${host.alias}${port})` : ""}`;
}

export default function RemoteRunEditor({
  value,
  inheritedRemote,
  sshHosts = [],
  onChange,
  compact = false,
}: {
  value?: RemoteSetting;
  inheritedRemote?: RemoteSetting;
  sshHosts?: SshHostInfo[];
  onChange: (remote: RemoteSetting) => void;
  compact?: boolean;
}) {
  const { t } = useI18n();
  const inheritedSummary = remoteSummary(inheritedRemote);
  const hasInheritedRemote = Boolean(inheritedSummary);
  const mode: RemoteMode = value === false
    ? "local"
    : isRemoteConfig(value)
      ? "ssh"
      : hasInheritedRemote
        ? "inherit"
        : "local";

  const remote = useMemo<RemoteConfig>(() => {
    if (isRemoteConfig(value)) return value;
    if (isRemoteConfig(inheritedRemote)) {
      return {
        host: inheritedRemote.host ?? "",
        user: inheritedRemote.user ?? null,
        port: inheritedRemote.port ?? null,
        cwd: inheritedRemote.cwd ?? null,
        args: inheritedRemote.args ?? [],
        options: inheritedRemote.options ?? {},
      };
    }
    return { host: "", args: [], options: {} };
  }, [inheritedRemote, value]);
  const effectiveSummary = mode === "inherit" ? inheritedSummary : remoteSummary(remote);
  const hostRequired = mode === "ssh" && !hasInheritedRemote && !remote.host?.trim();
  const portInvalid = mode === "ssh" && remote.port != null && (remote.port < 1 || remote.port > 65535);

  function setMode(nextMode: RemoteMode) {
    if (nextMode === "inherit") {
      onChange(null);
      return;
    }
    if (nextMode === "local") {
      onChange(hasInheritedRemote ? false : null);
      return;
    }
    onChange(compactRemote(remote) ?? { host: "" });
  }

  function updateRemote(patch: Partial<RemoteConfig>) {
    onChange(compactRemote({ ...remote, ...patch }) ?? { host: "" });
  }

  function applySshTarget(alias: string) {
    if (!alias) {
      updateRemote({ host: "", user: null, port: null });
      return;
    }
    const selected = sshHosts.find((host) => host.alias === alias);
    if (!selected) return;
    updateRemote({
      host: selected.alias,
      user: selected.user ?? null,
      port: selected.port ?? null,
    });
  }

  const locationOptions = [
    ...(hasInheritedRemote ? [{ id: "inherit" as const, label: t("runInherit"), icon: Undo2 }] : []),
    { id: "local" as const, label: t("runLocal"), icon: Laptop },
    { id: "ssh" as const, label: t("runSsh"), icon: Server },
  ];

  return (
    <section className={`rounded-md border border-default bg-[var(--bg-card)] ${compact ? "p-2.5" : "p-3"} space-y-2.5`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{t("runLocation")}</p>
          <p className="mt-0.5 truncate text-[11px] text-tertiary">
            {mode === "ssh"
              ? t("remoteRunsOn", { target: effectiveSummary || t("sshHost") })
              : mode === "inherit"
                ? t("inheritedRemoteSummary", { target: inheritedSummary })
                : t("localMachine")}
          </p>
        </div>
      </div>

      <div className={`grid gap-1.5 ${hasInheritedRemote ? "grid-cols-3" : "grid-cols-2"}`}>
        {locationOptions.map(({ id, label, icon: Icon }) => {
          const active = mode === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => setMode(id)}
              className={`control-touch rounded-md border px-2 text-[11px] font-semibold transition-colors inline-flex items-center justify-center gap-1.5 min-w-0 ${
                active
                  ? "border-[var(--accent)] bg-[var(--accent-bg)] text-[var(--accent-strong)]"
                  : "border-default bg-[var(--bg-card)] text-secondary hover:border-[var(--border-strong)] hover:text-primary"
              }`}
              aria-pressed={active}
            >
              <Icon className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{label}</span>
            </button>
          );
        })}
      </div>

      {mode === "ssh" && (
        <div className="space-y-2.5">
          {sshHosts.length > 0 && (
            <div>
              <FieldLabel>{t("sshTarget")}</FieldLabel>
              <SelectInput
                value={sshHosts.some((host) => host.alias === remote.host) ? remote.host ?? "" : ""}
                onChange={applySshTarget}
                ariaLabel={t("sshTarget")}
                options={[
                  { value: "", label: t("manualSshTarget") },
                  ...sshHosts.map((host) => ({ value: host.alias, label: sshTargetLabel(host) })),
                ]}
              />
              <HelpText>{t("sshTargetHint")}</HelpText>
            </div>
          )}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-[minmax(0,1fr)_96px] xl:grid-cols-1">
            <div>
              <FieldLabel required={!hasInheritedRemote}>{t("sshHost")}</FieldLabel>
              <TextInput
                value={remote.host ?? ""}
                onChange={(host) => updateRemote({ host: host || null })}
                placeholder={hasInheritedRemote ? inheritedSummary : "devbox"}
                invalid={hostRequired}
              />
              {hostRequired && <HelpText>{t("remoteHostRequiredInline")}</HelpText>}
            </div>
            <div>
              <FieldLabel>{t("sshPort")}</FieldLabel>
              <TextInput
                value={remote.port == null ? "" : String(remote.port)}
                onChange={(port) => updateRemote({ port: port.trim() ? Number(port) : null })}
                placeholder="22"
                invalid={portInvalid}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-1">
            <div>
              <FieldLabel>{t("sshUser")}</FieldLabel>
              <TextInput
                value={remote.user ?? ""}
                onChange={(user) => updateRemote({ user: user || null })}
                placeholder="ubuntu"
              />
            </div>
            <div>
              <FieldLabel>{t("remoteDirectory")}</FieldLabel>
              <TextInput
                value={remote.cwd ?? ""}
                onChange={(cwd) => updateRemote({ cwd: cwd || null })}
                placeholder="/srv/app"
              />
            </div>
          </div>

          <details className="group rounded-md border border-subtle bg-[var(--bg-hover)]/25">
            <summary className="flex cursor-pointer items-center gap-2 px-2.5 py-2 text-[10px] font-semibold uppercase tracking-wide text-tertiary hover:text-secondary">
              {t("sshAdvanced")}
            </summary>
            <div className="space-y-2.5 px-2.5 pb-2.5">
              <div>
                <FieldLabel>{t("sshArgs")}</FieldLabel>
                <TextInput
                  value={argsText(remote)}
                  onChange={(args) => updateRemote({ args: args.trim() ? args.trim().split(/\s+/) : [] })}
                  placeholder="-A -J bastion"
                />
                <HelpText>{t("sshArgsHint")}</HelpText>
              </div>
              <div>
                <FieldLabel>{t("sshOptions")}</FieldLabel>
                <KeyValueList
                  items={optionsToStrings(remote.options)}
                  keyLabel="ServerAliveInterval"
                  valueLabel="30"
                  onChange={(options) => updateRemote({ options })}
                />
              </div>
            </div>
          </details>
        </div>
      )}
    </section>
  );
}
