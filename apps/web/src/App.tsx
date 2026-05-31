import { useState, useEffect, useCallback, lazy, Suspense } from "react";
import type { MouseEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  LayoutGrid,
  FileCode2,
  Stethoscope,
  Bot,
  Sun,
  Moon,
  Globe,
  ChevronDown,
  X,
  AlertTriangle,
  RefreshCw,
  ClipboardList,
  ExternalLink,
  FolderPlus,
  CheckCircle2,
  Server,
  TerminalSquare,
  HardDrive,
  ShieldCheck,
} from "lucide-react";
import { I18nProvider, useI18n } from "./i18n";
import { ThemeProvider, useTheme } from "./theme/ThemeProvider";
import { ToastProvider } from "./components/ui/Toast";
import { useApiClient, useConfigOptions, useKeyboardShortcuts } from "./hooks";
import { useDesktopAutoUpdateCheck } from "./hooks/useDesktopAutoUpdateCheck";
import { useProjectStore, getActiveProject } from "./stores/projectStore";
import { useUIStore } from "./stores/uiStore";
import { appTabFromHash, appTabFromUrl, appTabHash, type AppTab } from "./utils/tabRoute";
import { visibleProjectsFromIndex } from "./utils/projects";
import Sidebar from "./components/Sidebar";
const AddProjectModal = lazy(() => import("./components/AddProjectModal"));
const ConfigEditor = lazy(() => import("./components/ConfigEditor"));
const DoctorView = lazy(() => import("./components/DoctorView"));
const SettingsModal = lazy(() => import("./components/SettingsModal"));
import ErrorBoundary from "./components/ErrorBoundary";
import OfflineBanner from "./components/OfflineBanner";
import SkipLink from "./components/SkipLink";
import Dropdown from "./components/ui/Dropdown";
import Tooltip from "./components/ui/Tooltip";
import Dashboard from "./components/Dashboard";
import ConfigSelector from "./components/ConfigSelector";
import type { AddProjectRequest } from "./types";
import type { WorkspaceEditTarget } from "./components/ConfigEditor/types";

type Tab = AppTab;
const GITHUB_RELEASES_URL = "https://github.com/GeminiLight/cc-branch/releases";

const tabs: { id: Tab; labelKey: string; compactLabelKey?: string; icon: typeof LayoutGrid }[] = [
  { id: "dashboard", labelKey: "dashboard", icon: LayoutGrid },
  { id: "workspace", labelKey: "workspaceTab", icon: FileCode2 },
  { id: "project", labelKey: "projectConfigTab", compactLabelKey: "config", icon: Bot },
  { id: "doctor", labelKey: "doctor", icon: Stethoscope },
];

const langItems = [
  { label: "English", value: "en", icon: <Globe className="w-3.5 h-3.5" /> },
  { label: "中文", value: "zh", icon: <Globe className="w-3.5 h-3.5" /> },
];

function initialTab(): Tab {
  if (typeof window === "undefined") return "dashboard";
  return appTabFromUrl(window.location.hash, window.location.search) || "dashboard";
}

function syncTabHash(tab: Tab, replace = false) {
  if (typeof window === "undefined") return;
  const nextHash = appTabHash(tab);
  const url = new URL(window.location.href);
  url.searchParams.delete("tab");
  url.hash = nextHash;
  if (window.location.hash === nextHash && !new URL(window.location.href).searchParams.has("tab")) return;
  window.history[replace ? "replaceState" : "pushState"](null, "", `${url.pathname}${url.search}${url.hash}`);
}

export function PanelLoading() {
  const { t } = useI18n();

  return (
    <div
      className="mx-auto flex min-h-[calc(100dvh-var(--chrome-height)-3rem)] max-w-2xl flex-col justify-center py-8"
      aria-label={t("startupAria")}
    >
      <div className="rounded-lg border border-default bg-[var(--bg-card)] px-5 py-5 shadow-sm">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-[var(--accent)]/20 bg-[var(--accent-bg)] text-[var(--accent)]">
            <Server className="h-5 w-5 animate-pulse" />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-base font-semibold leading-tight text-primary">{t("startupTitle")}</h2>
            <p className="mt-2 text-[13px] leading-5 text-secondary">{t("startupDesc")}</p>
          </div>
        </div>

        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          <div className="rounded-md border border-default bg-[var(--bg-elevated)] px-3 py-3">
            <div className="flex items-center gap-2 text-[12px] font-semibold text-primary">
              <ShieldCheck className="h-4 w-4 text-[var(--accent)]" />
              {t("startupLocalhostTitle")}
            </div>
            <p className="mt-1 text-[11px] leading-4 text-tertiary">{t("startupLocalhostDesc")}</p>
          </div>
          <div className="rounded-md border border-default bg-[var(--bg-elevated)] px-3 py-3">
            <div className="flex items-center gap-2 text-[12px] font-semibold text-primary">
              <HardDrive className="h-4 w-4 text-[var(--accent)]" />
              {t("startupPrivacyTitle")}
            </div>
            <p className="mt-1 text-[11px] leading-4 text-tertiary">{t("startupPrivacyDesc")}</p>
          </div>
        </div>

        <p className="mt-4 rounded-md border border-default bg-[var(--bg-elevated)] px-3 py-2 text-[11px] leading-4 text-tertiary">
          {t("startupNetworkPrompt")}
        </p>
      </div>
    </div>
  );
}

function releaseUrlForBackendFailure(message: string): string {
  const version = message.match(/^Desktop version:\s*(v?[0-9]+\.[0-9]+\.[0-9]+[^\s]*)/m)?.[1];
  if (!version) return GITHUB_RELEASES_URL;
  const tag = version.startsWith("v") ? version : `v${version}`;
  if (!/^v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$/.test(tag)) {
    return GITHUB_RELEASES_URL;
  }
  return `${GITHUB_RELEASES_URL}/tag/${encodeURIComponent(tag)}`;
}

function buildBackendDiagnosticsReport(message: string): string {
  const lines = [
    "CC Branch backend startup report",
    `Time: ${new Date().toISOString()}`,
    `Error: ${message}`,
  ];

  if (typeof window !== "undefined") {
    const desktopGlobals = window as Window & { __TAURI__?: unknown; __TAURI_INTERNALS__?: unknown };
    const mode = desktopGlobals.__TAURI__ || desktopGlobals.__TAURI_INTERNALS__ ? "tauri" : window.location.protocol.replace(":", "") || "unknown";
    lines.push(`Mode: ${mode}`);
    lines.push(`URL: ${window.location.href}`);
  }

  if (typeof navigator !== "undefined") {
    lines.push(`Platform: ${navigator.platform || "unknown"}`);
    lines.push(`User agent: ${navigator.userAgent || "unknown"}`);
  }

  lines.push("");
  lines.push("Suggested checks:");
  lines.push("1. Click Retry to restart the bundled backend.");
  lines.push(`2. Open ${releaseUrlForBackendFailure(message)} and reinstall the desktop installer for this platform.`);
  lines.push("3. Paste this report into the GitHub issue if the problem continues.");

  return lines.join("\n");
}

async function copyTextToClipboard(text: string): Promise<void> {
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  if (typeof document === "undefined") {
    throw new Error("Clipboard is not available in this environment.");
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  document.body.removeChild(textarea);
  if (!copied) throw new Error("Clipboard copy failed.");
}

async function openExternalUrlFallback(url: string): Promise<void> {
  if (typeof window !== "undefined" && typeof window.open === "function") {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

export function PageSwitcher({ tab, onSelect }: { tab: Tab; onSelect: (id: Tab) => void }) {
  const { t } = useI18n();

  return (
    <nav
      className="w-full min-w-0 shrink flex justify-center sm:w-auto"
      aria-label={t("primaryNavigation")}
    >
      <div
        className="grid h-10 w-full min-w-0 grid-cols-4 items-center gap-1 rounded-lg border border-default bg-[var(--bg-elevated)] p-1 sm:inline-flex sm:w-auto sm:max-w-[min(52vw,620px)] sm:shrink sm:overflow-x-auto"
        role="tablist"
        aria-label={t("workspaceControl")}
        onKeyDown={(e) => {
          const idx = tabs.findIndex((item) => item.id === tab);
          if (e.key === "ArrowRight") {
            e.preventDefault();
            const next = tabs[(idx + 1) % tabs.length];
            onSelect(next.id);
            document.getElementById(`tab-${next.id}`)?.focus();
          } else if (e.key === "ArrowLeft") {
            e.preventDefault();
            const prev = tabs[(idx - 1 + tabs.length) % tabs.length];
            onSelect(prev.id);
            document.getElementById(`tab-${prev.id}`)?.focus();
          } else if (e.key === "Home") {
            e.preventDefault();
            onSelect(tabs[0].id);
            document.getElementById(`tab-${tabs[0].id}`)?.focus();
          } else if (e.key === "End") {
            e.preventDefault();
            onSelect(tabs[tabs.length - 1].id);
            document.getElementById(`tab-${tabs[tabs.length - 1].id}`)?.focus();
          }
        }}
      >
        {tabs.map(({ id, labelKey, compactLabelKey, icon: Icon }) => {
          const active = tab === id;
          const label = t(labelKey);
          const compactLabel = t(compactLabelKey || labelKey);
          return (
            <Tooltip key={id} content={label} side="bottom">
              <button
                type="button"
                role="tab"
                aria-selected={active}
                aria-controls={`panel-${id}`}
                id={`tab-${id}`}
                onClick={() => onSelect(id)}
                className={`relative flex h-8 min-w-0 shrink-0 items-center justify-center gap-1 rounded-md px-1.5 text-[11px] font-semibold transition-colors sm:gap-1.5 sm:px-2.5 sm:text-[12px] ${
                  active
                    ? "bg-[var(--bg-card)] text-primary shadow-sm ring-1 ring-[var(--border-subtle)]"
                    : "text-tertiary hover:bg-[var(--bg-hover)] hover:text-secondary"
                }`}
                aria-label={label}
                title={label}
              >
                <Icon className={`h-3.5 w-3.5 shrink-0 ${active ? "text-[var(--accent)]" : ""}`} />
                <span className="min-w-0 truncate sm:hidden">{compactLabel}</span>
                <span className="hidden whitespace-nowrap sm:inline">{label}</span>
              </button>
            </Tooltip>
          );
        })}
      </div>
    </nav>
  );
}

export function BackendFailurePanel({
  message,
  onRetry,
  onOpenRelease = openExternalUrlFallback,
}: {
  message: string;
  onRetry: () => void | Promise<void>;
  onOpenRelease?: (url: string) => void | Promise<void>;
}) {
  const { t } = useI18n();
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const [retrying, setRetrying] = useState(false);
  const releaseUrl = releaseUrlForBackendFailure(message);

  const handleCopyDiagnostics = useCallback(async () => {
    try {
      await copyTextToClipboard(buildBackendDiagnosticsReport(message));
      setCopyState("copied");
    } catch {
      setCopyState("error");
    }
  }, [message]);

  const handleRetry = useCallback(async () => {
    if (retrying) return;
    setRetrying(true);
    try {
      await onRetry();
    } finally {
      setRetrying(false);
    }
  }, [onRetry, retrying]);

  const handleOpenRelease = useCallback(
    async (event: MouseEvent<HTMLAnchorElement>) => {
      event.preventDefault();
      await onOpenRelease(releaseUrl);
    },
    [onOpenRelease, releaseUrl],
  );

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-var(--chrome-height)-3rem)] max-w-2xl flex-col justify-center py-8">
      <div className="flex items-start gap-3 rounded-lg border border-[var(--danger)]/30 bg-[var(--bg-card)] px-4 py-4 shadow-sm">
        <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md danger-bg">
          <AlertTriangle className="h-4 w-4 danger" />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold text-primary">{t("backendStartupTitle")}</h2>
          <p className="mt-1 text-[13px] leading-5 text-secondary">{t("backendStartupDesc")}</p>
          <pre className="mt-3 max-h-40 overflow-auto rounded-md border border-default bg-[var(--bg-elevated)] px-3 py-2 text-left text-[11px] leading-4 text-secondary whitespace-pre-wrap break-words">
            {message}
          </pre>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleRetry}
              disabled={retrying}
              className="inline-flex h-9 items-center gap-2 rounded-md bg-[var(--accent)] px-3 text-[12px] font-semibold text-[var(--text-on-accent)] hover:bg-[var(--accent-light)] disabled:cursor-not-allowed disabled:opacity-70"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${retrying ? "animate-spin" : ""}`} />
              {retrying ? t("retrying") : t("retry")}
            </button>
            <button
              type="button"
              onClick={handleCopyDiagnostics}
              className="inline-flex h-9 items-center gap-2 rounded-md border border-default bg-[var(--bg-elevated)] px-3 text-[12px] font-semibold text-secondary hover:bg-[var(--bg-hover)] hover:text-primary"
            >
              <ClipboardList className="h-3.5 w-3.5" />
              {t("copyReport")}
            </button>
            <a
              href={releaseUrl}
              target="_blank"
              rel="noreferrer"
              onClick={handleOpenRelease}
              className="inline-flex h-9 items-center gap-2 rounded-md border border-default bg-[var(--bg-elevated)] px-3 text-[12px] font-semibold text-secondary hover:bg-[var(--bg-hover)] hover:text-primary"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              {t("downloadLatestInstaller")}
            </a>
            <span className="text-[11px] leading-4 text-tertiary">{t("backendStartupHint")}</span>
          </div>
          {copyState !== "idle" && (
            <p
              className={`mt-2 text-[11px] leading-4 ${copyState === "copied" ? "text-[var(--success)]" : "danger"}`}
              role="status"
            >
              {copyState === "copied" ? t("backendDiagnosticsCopied") : t("backendDiagnosticsCopyFailed")}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export function FirstRunEmptyState({ onAddProject }: { onAddProject: () => void }) {
  const { t } = useI18n();

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-var(--chrome-height)-3rem)] max-w-4xl flex-col justify-center py-8">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-stretch">
        <div className="rounded-lg border border-default bg-[var(--bg-card)] px-5 py-5 shadow-sm">
          <div className="inline-flex items-center gap-1.5 rounded-md border border-[var(--success)]/20 bg-[var(--success-bg)] px-2 py-1 text-[11px] font-semibold text-[var(--success)]">
            <CheckCircle2 className="h-3.5 w-3.5" />
            {t("firstRunBackendReady")}
          </div>
          <h2 className="mt-4 max-w-2xl text-[22px] font-semibold leading-tight text-primary sm:text-[26px]">
            {t("firstRunTitle")}
          </h2>
          <p className="mt-2 max-w-2xl text-[13px] leading-5 text-secondary">
            {t("firstRunDesc")}
          </p>
          <div className="mt-3 flex max-w-2xl items-start gap-2 rounded-md border border-default bg-[var(--bg-elevated)] px-3 py-2 text-[11px] leading-4 text-tertiary">
            <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--accent)]" />
            <span>
              <strong className="font-semibold text-secondary">{t("firstRunLocalOnly")}</strong>
              {" "}
              {t("firstRunPrivacy")}
            </span>
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={onAddProject}
              className="inline-flex h-10 items-center gap-2 rounded-md bg-[var(--accent)] px-3.5 text-[13px] font-semibold text-[var(--text-on-accent)] hover:bg-[var(--accent-light)]"
            >
              <FolderPlus className="h-4 w-4" />
              {t("firstRunAddProject")}
            </button>
            <span className="text-[11px] leading-4 text-tertiary">{t("firstRunAddProjectHint")}</span>
          </div>
        </div>

        <div className="grid gap-2 rounded-lg border border-default bg-[var(--bg-elevated)] p-3">
          <div className="rounded-md border border-default bg-[var(--bg-card)] px-3 py-3">
            <div className="flex items-center gap-2 text-[12px] font-semibold text-primary">
              <TerminalSquare className="h-4 w-4 text-[var(--accent)]" />
              {t("firstRunLocalTitle")}
            </div>
            <p className="mt-1 text-[11px] leading-4 text-tertiary">{t("firstRunLocalDesc")}</p>
          </div>
          <div className="rounded-md border border-default bg-[var(--bg-card)] px-3 py-3">
            <div className="flex items-center gap-2 text-[12px] font-semibold text-primary">
              <Server className="h-4 w-4 text-[var(--accent)]" />
              {t("firstRunSshTitle")}
            </div>
            <p className="mt-1 text-[11px] leading-4 text-tertiary">{t("firstRunSshDesc")}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function AppInner() {
  const [tab, setTabState] = useState<Tab>(initialTab);
  const { t, lang, setLang } = useI18n();
  const { theme, toggle } = useTheme();
  const client = useApiClient();
  const queryClient = useQueryClient();
  const desktopGlobals =
    typeof window !== "undefined"
      ? (window as Window & { __TAURI__?: unknown; __TAURI_INTERNALS__?: unknown })
      : null;
  const isMacDesktopShell =
    typeof window !== "undefined" &&
    typeof navigator !== "undefined" &&
    /Mac/.test(navigator.platform) &&
    Boolean(
      window.location.protocol !== "http:" ||
      desktopGlobals?.__TAURI__ ||
      desktopGlobals?.__TAURI_INTERNALS__
    );

  const projects = useProjectStore((s) => s.projects);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const activeProject = useProjectStore(getActiveProject);
  const setSnapshot = useProjectStore((s) => s.setSnapshot);

  const setMobileSidebarOpen = useUIStore((s) => s.setMobileSidebarOpen);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [projectsHydrated, setProjectsHydrated] = useState(false);
  const [projectsLoadError, setProjectsLoadError] = useState<string | null>(null);
  const [projectsReloadNonce, setProjectsReloadNonce] = useState(0);
  const [workspaceFocusTarget, setWorkspaceFocusTarget] = useState<WorkspaceEditTarget | null>(null);
  useDesktopAutoUpdateCheck(projectsHydrated);
  const activeConfigPath = activeProject?.selected_config_path;
  const activeScope = activeProject ? { projectPath: activeProject.path, configPath: activeConfigPath } : undefined;
  const { data: configOptionsData } = useConfigOptions(activeScope);
  const selectedConfigPath = configOptionsData?.selected_config_path || activeConfigPath;
  const activeProjectDisplayPath = activeProject?.display_path || activeProject?.path;

  const setTab = useCallback((next: Tab, replace = false) => {
    setTabState(next);
    syncTabHash(next, replace);
  }, []);

  useEffect(() => {
    const handleHashChange = () => {
      setTabState(appTabFromHash(window.location.hash) || "dashboard");
    };
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  // Web server mode represents one launched directory, so it should surface that
  // directory as "current". Desktop mode is app-wide and must not infer a
  // project from the packaged app's process cwd, but it should still show a
  // persisted "current" project when the backend already knows the real project.
  useEffect(() => {
    let cancelled = false;
    const injectCurrentProject = client.shouldInjectCurrentProject();
    const loadProjects = injectCurrentProject
      ? client.injectCurrentProject()
      : client.getProjectsIndex();
    loadProjects
      .then((data) => {
        if (cancelled) return;
        setProjectsLoadError(null);
        const visibleProjects = visibleProjectsFromIndex(data.projects);
        const activeId = visibleProjects.some((project) => project.id === data.active_project_id)
          ? data.active_project_id
          : visibleProjects[0]?.id ?? null;
        setSnapshot(visibleProjects, activeId);
      })
      .catch((error) => {
        if (cancelled) return;
        setProjectsLoadError(error instanceof Error ? error.message : t("backendUnreachable"));
      })
      .finally(() => {
        if (!cancelled) setProjectsHydrated(true);
      });
    return () => {
      cancelled = true;
    };
  }, [client, projectsReloadNonce, setSnapshot, t]);

  const handleAddProject = useCallback(
    async (request: AddProjectRequest) => {
      const data = await client.addProject(request);
      setSnapshot(data.projects, data.active_project_id);
      setTab("dashboard", true);
      setMobileSidebarOpen(false);
    },
    [client, setMobileSidebarOpen, setSnapshot, setTab]
  );

  const handleBackendRetry = useCallback(async () => {
    setProjectsHydrated(false);
    setProjectsLoadError(null);
    try {
      await client.restartBackend();
      setProjectsReloadNonce((value) => value + 1);
    } catch (error) {
      setProjectsLoadError(error instanceof Error ? error.message : t("backendUnreachable"));
      setProjectsHydrated(true);
    }
  }, [client, t]);

  const handleSelectProject = useCallback(
    (id: string) => {
      client
        .activateProject(id)
        .then((data) => setSnapshot(data.projects, data.active_project_id))
        .catch(() => {
          // keep current UI selection if activation fails.
        });
      setTab("dashboard", true);
      setMobileSidebarOpen(false);
    },
    [client, setMobileSidebarOpen, setSnapshot, setTab]
  );

  const handleRemoveProject = useCallback(
    (id: string) => {
      client
        .removeProject(id)
        .then((data) => setSnapshot(data.projects, data.active_project_id))
        .catch(() => {
          // keep current state if backend remove fails.
        });
    },
    [client, setSnapshot]
  );

  const handleSetProjectPinned = useCallback(
    (id: string, pinned: boolean) => {
      client
        .setProjectPinned(id, pinned)
        .then((data) => setSnapshot(data.projects, data.active_project_id))
        .catch(() => {
          // keep current order if backend update fails.
        });
    },
    [client, setSnapshot]
  );

  const handleReorderProject = useCallback(
    async (id: string, beforeId: string | null, pinned?: boolean) => {
      if (!id || id === beforeId) return;
      try {
        if (typeof pinned === "boolean") {
          await client.setProjectPinned(id, pinned);
        }
        const data = await client.reorderProject(id, beforeId);
        setSnapshot(data.projects, data.active_project_id);
      } catch {
        // keep current order if backend update fails.
      }
    },
    [client, setSnapshot]
  );

  const handleSetTab = useCallback((id: Tab) => setTab(id), [setTab]);
  const handleSelectConfig = useCallback(
    (path: string) => {
      if (!activeProject?.path) return;
      client
        .setProjectConfig(activeProject.path, path)
        .then((data) => setSnapshot(data.projects, data.active_project_id))
        .catch(() => {
          // keep current config selection if update fails.
        });
    },
    [activeProject?.path, client, setSnapshot]
  );

  const refreshConfigData = useCallback(
    (projectPath: string, configPath?: string) => {
      queryClient.invalidateQueries({ queryKey: ["workspace", "configs", projectPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "config", projectPath, configPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "status", projectPath, configPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "agents", projectPath, configPath] });
    },
    [queryClient]
  );

  const handleCreateConfig = useCallback(
    async (name: string, sourceConfigPath?: string) => {
      if (!activeProject?.path) return;
      const options = await client.createWorkspaceConfig(activeProject.path, name, sourceConfigPath || selectedConfigPath);
      const data = await client.setProjectConfig(activeProject.path, options.selected_config_path);
      setSnapshot(data.projects, data.active_project_id);
      refreshConfigData(activeProject.path, options.selected_config_path);
    },
    [activeProject?.path, client, refreshConfigData, selectedConfigPath, setSnapshot]
  );

  const handleRenameConfig = useCallback(
    async (configPath: string, name: string) => {
      if (!activeProject?.path) return;
      const options = await client.renameWorkspaceConfig(activeProject.path, configPath, name);
      const data = await client.setProjectConfig(activeProject.path, options.selected_config_path);
      setSnapshot(data.projects, data.active_project_id);
      refreshConfigData(activeProject.path, options.selected_config_path);
    },
    [activeProject?.path, client, refreshConfigData, setSnapshot]
  );

  const handleDeleteConfig = useCallback(
    async (configPath: string) => {
      if (!activeProject?.path) return;
      const options = await client.deleteWorkspaceConfig(activeProject.path, configPath);
      const data = await client.setProjectConfig(activeProject.path, options.selected_config_path);
      setSnapshot(data.projects, data.active_project_id);
      refreshConfigData(activeProject.path, options.selected_config_path);
    },
    [activeProject?.path, client, refreshConfigData, setSnapshot]
  );

  const handleEditWorkspaceTarget = useCallback((target: WorkspaceEditTarget) => {
    setWorkspaceFocusTarget({ ...target });
    setTab("workspace");
  }, [setTab]);

  const handleOpenSettings = useCallback(() => {
    setMobileSidebarOpen(false);
    setSettingsOpen(true);
  }, [setMobileSidebarOpen]);

  const activePanel = activeProject ? (
    <Suspense fallback={<PanelLoading />}>
      <div
        role="tabpanel"
        id={`panel-${tab}`}
        aria-labelledby={`tab-${tab}`}
        className="transition-opacity duration-200 opacity-100"
      >
        {tab === "dashboard" ? (
          <Dashboard
            key={`dash-${activeProject.id}-${selectedConfigPath || "default"}`}
            projectPath={activeProject.path}
            configPath={selectedConfigPath}
            isActive
            onEditTarget={handleEditWorkspaceTarget}
          />
        ) : tab === "workspace" ? (
          <ConfigEditor
            key={`workspace-${activeProject.id}-${selectedConfigPath || "default"}`}
            projectPath={activeProject.path}
            configPath={selectedConfigPath}
            view="workspace"
            focusTarget={workspaceFocusTarget}
          />
        ) : tab === "project" ? (
          <ConfigEditor
            key={`project-config-${activeProject.id}-${selectedConfigPath || "default"}`}
            projectPath={activeProject.path}
            configPath={selectedConfigPath}
            view="project"
          />
        ) : (
          <DoctorView
            key={`doc-${activeProject.id}-${selectedConfigPath || "default"}`}
            projectPath={activeProject.path}
            configPath={selectedConfigPath}
          />
        )}
      </div>
    </Suspense>
  ) : null;

  // Global keyboard shortcuts
  useKeyboardShortcuts({
    onTab1: () => setTab("dashboard"),
    onTab2: () => setTab("workspace"),
    onTab3: () => setTab("project"),
    onTab4: () => setTab("doctor"),
    onEscape: () => {
      setMobileSidebarOpen(false);
      setAddModalOpen(false);
    },
  });

  return (
    <div className={`h-[100dvh] surface-page flex overflow-hidden text-[14px] leading-relaxed ${isMacDesktopShell ? "mac-desktop-shell" : ""}`}>
      {isMacDesktopShell && (
        <div
          data-tauri-drag-region
          className="fixed left-0 right-0 top-0 z-40 h-[var(--desktop-titlebar-height)] surface-page"
          aria-hidden="true"
        />
      )}
      {/* Desktop sidebar */}
      <div className="hidden md:block relative z-30">
        <Sidebar
          api={client}
          projects={projects}
          activeProjectId={activeProjectId}
          onSelectProject={handleSelectProject}
          onRemoveProject={handleRemoveProject}
          onSetProjectPinned={handleSetProjectPinned}
          onReorderProject={handleReorderProject}
          onAddProject={() => setAddModalOpen(true)}
          onOpenSettings={handleOpenSettings}
          resizable
        />
      </div>

      {/* Mobile sidebar overlay */}
      <MobileSidebarOverlay
        client={client}
        projects={projects}
        activeProjectId={activeProjectId}
        onSelectProject={handleSelectProject}
        onRemoveProject={handleRemoveProject}
        onSetProjectPinned={handleSetProjectPinned}
        onReorderProject={handleReorderProject}
        onAddProject={() => setAddModalOpen(true)}
        onOpenSettings={handleOpenSettings}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="min-h-[var(--chrome-height)] border-b border-default chrome-surface flex flex-wrap items-center justify-between gap-2 px-3 py-2 sm:h-[var(--chrome-height)] sm:flex-nowrap sm:gap-3 sm:px-5 sm:py-0 shrink-0 z-10">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            {/* Mobile hamburger */}
            <button
              type="button"
              onClick={() => setMobileSidebarOpen(true)}
              className="md:hidden icon-touch rounded-md flex items-center justify-center text-secondary hover:text-primary hover:surface-hover transition-colors"
              aria-label={t("openSidebar")}
            >
              <LayoutGrid className="w-4 h-4" />
            </button>

            <div className="hidden sm:flex min-w-0 flex-col justify-center">
              {!projectsHydrated ? (
                <>
                  <span className="block h-[16px] w-[168px] rounded bg-[var(--bg-hover)]/70" aria-hidden="true" />
                  <span className="mt-1 block h-[11px] w-[240px] max-w-[min(32vw,240px)] rounded bg-[var(--bg-hover)]/45" aria-hidden="true" />
                </>
              ) : (
                <span className="text-sm font-semibold text-primary tracking-tight leading-tight">
                  {activeProject?.name || t("appTitle")}
                </span>
              )}
              {projectsHydrated && activeProjectDisplayPath && (
                <Tooltip content={activeProjectDisplayPath} side="bottom">
                  <span className="block text-[11px] text-tertiary font-mono truncate max-w-[min(32vw,320px)] leading-tight mt-0.5">
                    {activeProjectDisplayPath}
                  </span>
                </Tooltip>
              )}
            </div>
          </div>

          {activeProject && projectsHydrated && (
            <div className="order-3 w-full sm:order-none sm:w-auto">
              <PageSwitcher tab={tab} onSelect={handleSetTab} />
            </div>
          )}

          <div className="flex items-center justify-end gap-0.5 min-w-0 shrink-0">
            {activeProject && configOptionsData?.configs ? (
              <ConfigSelector
                projectPath={activeProject.path}
                configs={configOptionsData.configs}
                selectedPath={selectedConfigPath}
                onSelect={handleSelectConfig}
                onCreate={handleCreateConfig}
                onRename={handleRenameConfig}
                onDelete={handleDeleteConfig}
              />
            ) : activeProject ? (
              <div
                className="control-touch w-[152px] sm:min-w-[176px] max-w-[260px] rounded-lg border border-default bg-[var(--bg-hover)]/45"
                aria-hidden="true"
              />
            ) : null}
            <Dropdown
              align="right"
              value={lang}
              onChange={(v) => setLang(v as "en" | "zh")}
              items={langItems}
              trigger={
                <div className="control-touch px-2.5 rounded-md flex items-center gap-1.5 text-[12px] font-medium text-secondary hover:text-primary hover:surface-hover transition-colors cursor-pointer">
                  <Globe className="w-3 h-3" />
                  <span className="uppercase">{lang}</span>
                  <ChevronDown className="w-3 h-3 text-tertiary" />
                </div>
              }
            />
            <Tooltip
              content={theme === "light" ? t("dark") : t("light")}
              side="bottom"
            >
              <button
                type="button"
                onClick={toggle}
                className="icon-touch rounded-md flex items-center justify-center text-secondary hover:text-primary hover:surface-hover transition-colors"
                aria-label={theme === "light" ? t("dark") : t("light")}
                aria-pressed={theme === "dark"}
              >
                {theme === "light" ? (
                  <Moon className="w-4 h-4" />
                ) : (
                  <Sun className="w-4 h-4" />
                )}
              </button>
            </Tooltip>
          </div>
        </header>

        {/* Content */}
        <main id="main-content" className="flex-1 px-4 sm:px-5 py-4 min-w-0 overflow-y-auto" tabIndex={-1}>
          {!projectsHydrated ? (
            <PanelLoading />
          ) : projectsLoadError ? (
            <BackendFailurePanel
              message={projectsLoadError}
              onRetry={handleBackendRetry}
              onOpenRelease={(url) => client.openExternalUrl(url)}
            />
          ) : activeProject ? (
            activePanel
          ) : (
            <FirstRunEmptyState onAddProject={() => setAddModalOpen(true)} />
          )}
        </main>
      </div>

      <Suspense fallback={null}>
        <AddProjectModal
          api={client}
          isOpen={addModalOpen}
          onClose={() => setAddModalOpen(false)}
          onAdd={handleAddProject}
        />
      </Suspense>
      {settingsOpen && (
        <Suspense fallback={null}>
          <SettingsModal
            isOpen={settingsOpen}
            onClose={() => setSettingsOpen(false)}
          />
        </Suspense>
      )}
    </div>
  );
}

function MobileSidebarOverlay({
  client,
  projects,
  activeProjectId,
  onSelectProject,
  onRemoveProject,
  onSetProjectPinned,
  onReorderProject,
  onAddProject,
  onOpenSettings,
}: {
  client: ReturnType<typeof useApiClient>;
  projects: ReturnType<typeof useProjectStore.getState>["projects"];
  activeProjectId: string | null;
  onSelectProject: (id: string) => void;
  onRemoveProject: (id: string) => void;
  onSetProjectPinned: (id: string, pinned: boolean) => void;
  onReorderProject: (id: string, beforeId: string | null, pinned?: boolean) => void;
  onAddProject: () => void;
  onOpenSettings: () => void;
}) {
  const { t } = useI18n();
  const mobileSidebarOpen = useUIStore((s) => s.mobileSidebarOpen);
  const setMobileSidebarOpen = useUIStore((s) => s.setMobileSidebarOpen);

  if (!mobileSidebarOpen) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/20 z-[90] md:hidden animate-fade-in"
        onClick={() => setMobileSidebarOpen(false)}
      />
      <div className="fixed left-0 top-0 h-[100dvh] z-[100] md:hidden animate-slide-in-left flex">
        <Sidebar
          api={client}
          projects={projects}
          activeProjectId={activeProjectId}
          onSelectProject={onSelectProject}
          onRemoveProject={onRemoveProject}
          onSetProjectPinned={onSetProjectPinned}
          onReorderProject={onReorderProject}
          onAddProject={onAddProject}
          onOpenSettings={onOpenSettings}
          forceExpanded
        />
        <button
          type="button"
          onClick={() => setMobileSidebarOpen(false)}
          className="absolute -right-10 top-3 w-10 h-10 rounded-full bg-[var(--bg-card)]/90 backdrop-blur flex items-center justify-center text-primary shadow-md border border-default"
          aria-label={t("cancel")}
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </>
  );
}

function App() {
  return (
    <I18nProvider>
      <ThemeProvider>
        <ToastProvider>
          <ErrorBoundary>
            <SkipLink />
            <OfflineBanner />
            <AppInner />
          </ErrorBoundary>
        </ToastProvider>
      </ThemeProvider>
    </I18nProvider>
  );
}

export default App;
