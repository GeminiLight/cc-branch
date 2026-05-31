import { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { CheckCircle2, ChevronsUpDown, ChevronUp, FolderOpen, FolderSearch, Laptop, Loader2, MapPin, Plus, RefreshCw, Server, X } from "lucide-react";
import type { APIClient } from "../api/client";
import type { AddProjectRequest, RemoteDirectoryListing, SshHostInfo } from "../types";
import { useI18n } from "../i18n";
import { projectDirFromConfigPath } from "../utils/projectPath";
import { useToast } from "./ui/Toast";
import Dropdown from "./ui/Dropdown";

interface AddProjectModalProps {
  api: APIClient;
  isOpen: boolean;
  onClose: () => void;
  onAdd: (request: AddProjectRequest) => Promise<void> | void;
}

type AddMode = "local" | "ssh";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function sshConnectionLabel(host: SshHostInfo): string {
  const endpoint = host.hostname || host.alias;
  const user = host.user ? `${host.user}@` : "";
  const port = host.port ? `:${host.port}` : "";
  return `${user}${endpoint}${port}`;
}

function remoteProjectName(path: string, host: string): string {
  const cleaned = path.trim().replace(/\/+$/, "");
  const last = cleaned.split("/").filter(Boolean).at(-1);
  return last || host || "remote-project";
}

export default function AddProjectModal({ api, isOpen, onClose, onAdd }: AddProjectModalProps) {
  const { t } = useI18n();
  const toast = useToast();
  const [mode, setMode] = useState<AddMode>("local");
  const [path, setPath] = useState("");
  const [sshHosts, setSshHosts] = useState<SshHostInfo[]>([]);
  const [remoteHost, setRemoteHost] = useState("");
  const [remoteUser, setRemoteUser] = useState("");
  const [remotePort, setRemotePort] = useState("");
  const [remotePath, setRemotePath] = useState("");
  const [remoteName, setRemoteName] = useState("");
  const [remoteBrowserOpen, setRemoteBrowserOpen] = useState(false);
  const [remoteListing, setRemoteListing] = useState<RemoteDirectoryListing | null>(null);
  const [remoteBrowseError, setRemoteBrowseError] = useState("");
  const [remoteBrowsing, setRemoteBrowsing] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [picking, setPicking] = useState(false);
  const [adding, setAdding] = useState(false);
  const [currentDir, setCurrentDir] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<{
    path_exists: boolean;
    config_exists: boolean;
    project_name: string;
    slots: number;
    status: string;
  } | null>(null);
  const latestRequest = useRef(0);
  const latestPickRequest = useRef(0);
  const modalRef = useRef<HTMLDivElement>(null);
  const canBrowseSystemDirectory = api.supportsNativeProjectDirectoryPicker();
  const selectedSshAlias = sshHosts.some((host) => host.alias === remoteHost) ? remoteHost : "";
  const selectedSshHost = sshHosts.find((host) => host.alias === selectedSshAlias);
  const inferredRemoteName = remoteName.trim() || remoteProjectName(remotePath, remoteHost);
  const canAddRemote = Boolean(remoteHost.trim() && remotePath.trim() && (remotePort.trim() === "" || Number(remotePort) > 0));
  const canBrowseRemoteDirectory = Boolean(remoteHost.trim() && (remotePort.trim() === "" || Number(remotePort) > 0));

  const handleScan = useCallback(async (value?: string) => {
    const target = (value ?? path).trim();
    if (!target) return;
    const reqId = ++latestRequest.current;
    setScanning(true);
    setScanResult(null);
    try {
      const data = await api.probeProject(target);
      if (reqId !== latestRequest.current) return;
      setScanResult({
        path_exists: data.path_exists,
        config_exists: data.config_exists,
        project_name: data.project_name,
        slots: data.slots,
        status: data.status,
      });
    } catch (e: unknown) {
      if (reqId !== latestRequest.current) return;
      setScanResult({
        path_exists: false,
        config_exists: false,
        project_name: target.split(/[\\/]/).pop() || "",
        slots: 0,
        status: "missing",
      });
      toast.error(errorMessage(e));
    } finally {
      if (reqId === latestRequest.current) {
        setScanning(false);
      }
    }
  }, [path, api, toast]);

  const handlePickDirectory = useCallback(async () => {
    const reqId = ++latestPickRequest.current;
    setPicking(true);
    try {
      const selected = await api.pickProjectDirectory(currentDir || undefined);
      if (reqId !== latestPickRequest.current || !selected) return;
      setPath(selected);
      await handleScan(selected);
    } catch (e: unknown) {
      if (reqId !== latestPickRequest.current) return;
      toast.error(errorMessage(e));
    } finally {
      if (reqId === latestPickRequest.current) {
        setPicking(false);
      }
    }
  }, [api, currentDir, handleScan, toast]);

  const handleAdd = useCallback(async () => {
    if (mode === "local" && (!path.trim() || !scanResult?.path_exists)) return;
    if (mode === "ssh" && !canAddRemote) return;
    setAdding(true);
    try {
      const request: AddProjectRequest = mode === "ssh"
        ? {
            name: inferredRemoteName,
            remote: {
              host: remoteHost.trim(),
              user: remoteUser.trim() || null,
              port: remotePort.trim() ? Number(remotePort) : null,
              cwd: remotePath.trim(),
            },
          }
        : { path: path.trim() };
      await onAdd(request);
      setPath("");
      setRemotePath("");
      setRemoteName("");
      setScanResult(null);
      onClose();
      toast.success(t("projectAdded"));
    } catch (e: unknown) {
      toast.error(errorMessage(e));
    } finally {
      setAdding(false);
    }
  }, [canAddRemote, inferredRemoteName, mode, onAdd, onClose, path, remoteHost, remotePath, remotePort, remoteUser, scanResult, toast, t]);

  function applySshTarget(alias: string) {
    if (!alias) {
      setRemoteHost("");
      setRemoteUser("");
      setRemotePort("");
      setRemoteListing(null);
      setRemoteBrowseError("");
      return;
    }
    const selected = sshHosts.find((host) => host.alias === alias);
    if (!selected) return;
    setRemoteHost(selected.alias);
    setRemoteUser(selected.user || "");
    setRemotePort(selected.port ? String(selected.port) : "");
    setRemoteListing(null);
    setRemoteBrowseError("");
  }

  const browseRemoteDirectory = useCallback(async (nextPath?: string) => {
    if (!canBrowseRemoteDirectory) return;
    const targetPath = (nextPath ?? remotePath).trim() || ".";
    setRemoteBrowserOpen(true);
    setRemoteBrowsing(true);
    setRemoteBrowseError("");
    try {
      const listing = await api.listRemoteDirectories(
        {
          host: remoteHost.trim(),
          user: remoteUser.trim() || null,
          port: remotePort.trim() ? Number(remotePort) : null,
        },
        targetPath,
      );
      setRemoteListing(listing);
      setRemotePath(listing.path);
    } catch (e: unknown) {
      setRemoteBrowseError(errorMessage(e));
    } finally {
      setRemoteBrowsing(false);
    }
  }, [api, canBrowseRemoteDirectory, remoteHost, remotePath, remotePort, remoteUser]);

  const remoteEndpoint = useMemo(() => {
    const user = remoteUser.trim() ? `${remoteUser.trim()}@` : "";
    const port = remotePort.trim() ? `:${remotePort.trim()}` : "";
    return `${user}${remoteHost.trim()}${port}`;
  }, [remoteHost, remotePort, remoteUser]);

  useEffect(() => {
    if (!isOpen) return;
    api.getApiInfo()
      .then((info) => {
        setSshHosts(info.ssh_hosts || []);
        if (info.config_path && api.shouldInjectCurrentProject()) {
          setCurrentDir(projectDirFromConfigPath(info.config_path));
        } else {
          setCurrentDir(null);
        }
      })
      .catch(() => {
        setCurrentDir(null);
        setSshHosts([]);
      });
  }, [isOpen, api]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key !== "Tab" || !modalRef.current) return;
      const focusable = modalRef.current.querySelectorAll<HTMLElement>(
        'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", handleKey);
    const timer = setTimeout(() => {
      const input = modalRef.current?.querySelector<HTMLInputElement>("input");
      input?.focus();
    }, 50);
    return () => {
      document.removeEventListener("keydown", handleKey);
      clearTimeout(timer);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label={t("addProject")}
    >
      <button
        type="button"
        className="absolute inset-0 h-full w-full cursor-default bg-black/20 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
        tabIndex={-1}
      />
      <div ref={modalRef} className="relative z-10 flex max-h-[92dvh] w-full max-w-2xl flex-col overflow-hidden rounded-lg border border-default surface-card animate-modal-in">
        <div className="flex items-center justify-between border-b border-default px-5 py-3.5">
          <div>
            <h3 className="text-sm font-semibold text-primary">{t("addProject")}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-6 w-6 items-center justify-center rounded text-tertiary transition-colors hover:surface-hover hover:text-primary"
            aria-label={t("cancel")}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="min-h-0 overflow-y-auto px-5 py-4 space-y-3.5">
          <div className="grid grid-cols-2 gap-2 rounded-lg border border-default bg-[var(--bg-hover)]/45 p-1">
            {[
              { id: "local" as const, label: t("localProject"), icon: Laptop },
              { id: "ssh" as const, label: t("sshProject"), icon: Server },
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => {
                  setMode(id);
                  setScanResult(null);
                }}
                className={`control-touch rounded-md text-[12px] font-semibold transition-colors inline-flex items-center justify-center gap-1.5 ${
                  mode === id
                    ? "border border-[var(--accent-border)] bg-[var(--accent-bg)] text-primary shadow-sm"
                    : "text-tertiary hover:text-secondary"
                }`}
                aria-pressed={mode === id}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </button>
            ))}
          </div>

          {mode === "local" ? (
            <>
              <div>
                <label htmlFor="project-path-input" className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wide text-tertiary">
                  {t("projectDirectory")}
                </label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <FolderOpen className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-tertiary" />
                    <input
                      id="project-path-input"
                      type="text"
                      value={path}
                      onChange={(e) => {
                        setPath(e.target.value);
                        setScanResult(null);
                      }}
                      placeholder={t("pathExample")}
                      autoComplete="off"
                      className="h-8 w-full rounded border border-default bg-[var(--bg-page)] pl-8 pr-3 text-[13px] text-primary transition-colors placeholder:text-muted focus:border-[var(--accent)] focus:outline-none"
                      onKeyDown={(e) => {
                        if (e.key !== "Enter") return;
                        if (scanResult?.path_exists) void handleAdd();
                        else void handleScan();
                      }}
                    />
                  </div>
                  {canBrowseSystemDirectory && (
                    <button
                      type="button"
                      onClick={() => { void handlePickDirectory(); }}
                      disabled={picking || scanning || adding}
                      className="flex h-8 items-center gap-1.5 rounded border border-default px-2.5 text-[11px] font-medium text-secondary transition-colors surface-hover hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                      aria-label={t("browseDirectory")}
                      title={t("browseDirectory")}
                    >
                      {picking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FolderSearch className="h-3.5 w-3.5" />}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => { void handleScan(); }}
                    disabled={scanning || adding || !path.trim()}
                    className="flex h-8 items-center gap-1.5 rounded bg-[var(--accent)] px-3 text-[11px] font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {scanning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : t("scan")}
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {currentDir && (
                  <button
                    type="button"
                    onClick={() => {
                      setPath(currentDir);
                      void handleScan(currentDir);
                    }}
                    className="flex h-6 items-center gap-1 rounded border border-default px-2 text-[11px] font-medium text-secondary transition-colors surface-hover hover:text-primary"
                  >
                    <MapPin className="h-3 w-3" />
                    {t("useCurrentDir")}
                  </button>
                )}
              </div>

              {scanResult && (
                <div
                  className={`rounded p-2.5 text-[13px] ${
                    scanResult.config_exists
                      ? "success-bg border border-[var(--success)]/10"
                      : !scanResult.path_exists
                        ? "danger-bg border border-[var(--danger)]/10"
                        : "warning-bg border border-[var(--warning)]/10"
                  }`}
                >
                  <p className="font-semibold text-primary">{scanResult.project_name}</p>
                  <p className="mt-px text-[11px] text-secondary">
                    {scanResult.config_exists
                      ? `${scanResult.slots} ${t("slots")}`
                      : !scanResult.path_exists
                        ? t("pathNotFound")
                        : t("canInitializeAfterAdd")}
                  </p>
                </div>
              )}
            </>
          ) : (
            <div className="space-y-3">
              <div className="rounded-lg border border-default bg-[var(--bg-card)] p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("chooseSshTarget")}</p>
                  </div>
                  {selectedSshHost && (
                    <span className="inline-flex items-center gap-1 rounded-md border border-[var(--accent-border)] bg-[var(--accent-bg)] px-2 py-0.5 text-[10px] font-semibold text-[var(--accent)]">
                      <CheckCircle2 className="h-3 w-3" />
                      {t("selectedSshTarget")}
                    </span>
                  )}
                </div>
                {sshHosts.length > 0 ? (
                  <div>
                    <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-tertiary">
                      {t("savedSshTargets")}
                    </p>
                    <Dropdown
                      value={selectedSshAlias}
                      onChange={applySshTarget}
                      align="left"
                      ariaLabel={t("savedSshTargets")}
                      className="w-full"
                      triggerClassName="w-full"
                      items={[
                        { label: t("manualSshTarget"), value: "", description: t("manualSshTargetHelp") },
                        ...sshHosts.map((host) => ({
                          label: host.alias,
                          value: host.alias,
                          description: sshConnectionLabel(host),
                        })),
                      ]}
                      trigger={
                        <span className="flex h-10 w-full min-w-0 items-center justify-between gap-2 rounded-md border border-default bg-[var(--bg-page)] px-2.5 text-left transition-colors hover:border-[var(--accent-border)] hover:bg-[var(--bg-hover)]">
                          <span className="min-w-0">
                            <span className="block truncate text-[13px] font-semibold text-primary">
                              {selectedSshHost ? selectedSshHost.alias : t("manualSshTarget")}
                            </span>
                            <span className="block truncate font-mono text-[10.5px] text-tertiary">
                              {selectedSshHost ? sshConnectionLabel(selectedSshHost) : t("manualSshTargetHelp")}
                            </span>
                          </span>
                          <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-tertiary" />
                        </span>
                      }
                    />
                  </div>
                ) : (
                  <div className="rounded border border-dashed border-default bg-[var(--bg-hover)]/35 px-3 py-2 text-[11px] text-tertiary">
                    {t("noSshTargets")}
                  </div>
                )}
              </div>

              <div className="rounded-lg border border-default bg-[var(--bg-card)] p-3">
                <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("sshConnectionDetails")}</p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-[minmax(0,1fr)_88px]">
                  <div>
                  <label htmlFor="remote-host-input" className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wide text-tertiary">
                    {t("sshHost")}
                  </label>
                  <input
                    id="remote-host-input"
                    type="text"
                    value={remoteHost}
                    onChange={(e) => setRemoteHost(e.target.value)}
                    placeholder="gpu-dev"
                    className="h-8 w-full rounded border border-default bg-[var(--bg-page)] px-3 text-[13px] text-primary transition-colors placeholder:text-muted focus:border-[var(--accent)] focus:outline-none"
                  />
                  </div>
                  <div>
                  <label htmlFor="remote-port-input" className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wide text-tertiary">
                    {t("sshPort")}
                  </label>
                  <input
                    id="remote-port-input"
                    type="number"
                    min={1}
                    max={65535}
                    value={remotePort}
                    onChange={(e) => setRemotePort(e.target.value)}
                    placeholder="22"
                    className="h-8 w-full rounded border border-default bg-[var(--bg-page)] px-3 text-[13px] text-primary transition-colors placeholder:text-muted focus:border-[var(--accent)] focus:outline-none"
                  />
                  </div>
                </div>

                <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <div>
                  <label htmlFor="remote-user-input" className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wide text-tertiary">
                    {t("sshUser")}
                  </label>
                  <input
                    id="remote-user-input"
                    type="text"
                    value={remoteUser}
                    onChange={(e) => setRemoteUser(e.target.value)}
                    placeholder="ubuntu"
                    className="h-8 w-full rounded border border-default bg-[var(--bg-page)] px-3 text-[13px] text-primary transition-colors placeholder:text-muted focus:border-[var(--accent)] focus:outline-none"
                  />
                  </div>
                  <div>
                  <label htmlFor="remote-name-input" className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wide text-tertiary">
                    {t("sshProjectName")}
                  </label>
                  <input
                    id="remote-name-input"
                    type="text"
                    value={remoteName}
                    onChange={(e) => setRemoteName(e.target.value)}
                    placeholder={t("sshProjectNamePlaceholder")}
                    className="h-8 w-full rounded border border-default bg-[var(--bg-page)] px-3 text-[13px] text-primary transition-colors placeholder:text-muted focus:border-[var(--accent)] focus:outline-none"
                  />
                  </div>
                </div>
              </div>

              <div>
                <label htmlFor="remote-path-input" className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wide text-tertiary">
                  {t("sshProjectDirectory")}
                </label>
                <div className="flex gap-2">
                  <input
                    id="remote-path-input"
                    type="text"
                    value={remotePath}
                    onChange={(e) => {
                      setRemotePath(e.target.value);
                      setRemoteListing(null);
                    }}
                    placeholder="/srv/app"
                    className="h-8 min-w-0 flex-1 rounded border border-default bg-[var(--bg-page)] px-3 font-mono text-[13px] text-primary transition-colors placeholder:text-muted focus:border-[var(--accent)] focus:outline-none"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void handleAdd();
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => { void browseRemoteDirectory(); }}
                    disabled={!canBrowseRemoteDirectory || remoteBrowsing}
                    className="flex h-8 items-center gap-1.5 rounded border border-default px-2.5 text-[11px] font-medium text-secondary transition-colors surface-hover hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                    aria-label={t("browseRemoteDirectory")}
                    title={t("browseRemoteDirectory")}
                  >
                    {remoteBrowsing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FolderSearch className="h-3.5 w-3.5" />}
                  </button>
                </div>
                <p className="mt-1 text-[11px] text-tertiary">{t("remoteProjectHelp")}</p>
              </div>

              {remoteBrowserOpen && (
                <div className="rounded-lg border border-default bg-[var(--bg-card)] p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("remoteDirectoryBrowser")}</p>
                      <p className="mt-0.5 truncate font-mono text-[11px] text-secondary">
                        {remoteListing?.path || remotePath || "."}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                      {remoteListing?.parent && (
                        <button
                          type="button"
                          onClick={() => { void browseRemoteDirectory(remoteListing.parent || "."); }}
                          disabled={remoteBrowsing}
                          className="flex h-7 w-7 items-center justify-center rounded border border-default text-tertiary transition-colors hover:text-primary disabled:opacity-50"
                          aria-label={t("parentDirectory")}
                          title={t("parentDirectory")}
                        >
                          <ChevronUp className="h-3.5 w-3.5" />
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => { void browseRemoteDirectory(remoteListing?.path || remotePath || "."); }}
                        disabled={remoteBrowsing}
                        className="flex h-7 w-7 items-center justify-center rounded border border-default text-tertiary transition-colors hover:text-primary disabled:opacity-50"
                        aria-label={t("refresh")}
                        title={t("refresh")}
                      >
                        <RefreshCw className={`h-3.5 w-3.5 ${remoteBrowsing ? "animate-spin" : ""}`} />
                      </button>
                      <button
                        type="button"
                        onClick={() => setRemoteBrowserOpen(false)}
                        className="flex h-7 w-7 items-center justify-center rounded border border-default text-tertiary transition-colors hover:text-primary"
                        aria-label={t("cancel")}
                        title={t("cancel")}
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  {remoteBrowseError && (
                    <p className="mt-2 rounded border border-[var(--danger)]/20 bg-[var(--danger-bg)] px-2 py-1.5 text-[11px] text-[var(--danger)]">
                      {remoteBrowseError}
                    </p>
                  )}
                  <div className="mt-2 max-h-52 overflow-y-auto rounded-md border border-subtle bg-[var(--bg-page)]">
                    {remoteBrowsing && !remoteListing ? (
                      <div className="flex items-center gap-2 px-3 py-3 text-[11px] text-tertiary">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        {t("loading")}
                      </div>
                    ) : remoteListing?.entries.length ? (
                      remoteListing.entries.map((entry) => (
                        <button
                          key={entry.path}
                          type="button"
                          onClick={() => { void browseRemoteDirectory(entry.path); }}
                          className="flex w-full items-center gap-2 border-b border-subtle px-3 py-2 text-left text-[12px] text-secondary transition-colors last:border-b-0 hover:bg-[var(--bg-hover)] hover:text-primary"
                          aria-label={t("openRemoteDirectory", { path: entry.path })}
                        >
                          <FolderOpen className="h-3.5 w-3.5 shrink-0 text-tertiary" />
                          <span className="min-w-0 truncate font-mono">{entry.name}</span>
                        </button>
                      ))
                    ) : (
                      <p className="px-3 py-3 text-[11px] text-tertiary">{t("noRemoteDirectories")}</p>
                    )}
                  </div>
                  {remoteListing?.truncated && (
                    <p className="mt-2 rounded border border-default bg-[var(--bg-elevated)] px-2 py-1.5 text-[11px] text-tertiary">
                      {t("remoteDirectoryTruncated", { count: remoteListing.entries.length })}
                    </p>
                  )}
                  <div className="mt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={() => setRemoteBrowserOpen(false)}
                      className="h-7 rounded bg-[var(--accent)] px-2.5 text-[11px] font-medium text-white transition-opacity hover:opacity-90"
                    >
                      {t("useThisRemoteDirectory")}
                    </button>
                  </div>
                </div>
              )}

              {canAddRemote && (
                <div className="rounded border border-[var(--accent)]/15 bg-[var(--accent-bg)] px-3 py-2">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--accent)]">{t("remoteProjectPreview")}</p>
                  <p className="mt-1 text-[12px] font-semibold text-primary">{inferredRemoteName}</p>
                  <p className="mt-px truncate font-mono text-[11px] text-secondary">
                    {`${remoteEndpoint}:${remotePath.trim()}`}
                  </p>
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="h-8 rounded px-3 text-[13px] font-medium text-secondary transition-colors surface-hover hover:text-primary"
            >
              {t("cancel")}
            </button>
            <button
              type="button"
              onClick={() => { void handleAdd(); }}
              disabled={adding || (mode === "local" ? !scanResult?.path_exists : !canAddRemote)}
              className="flex h-8 items-center gap-1.5 rounded bg-[var(--accent)] px-3 text-[13px] font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {adding ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              {mode === "ssh" ? t("addRemoteProject") : t("addProject")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
