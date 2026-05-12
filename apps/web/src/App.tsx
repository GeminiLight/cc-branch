import { useState, useEffect, useCallback, lazy, Suspense } from "react";
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
} from "lucide-react";
import { I18nProvider, useI18n } from "./i18n";
import { ThemeProvider, useTheme } from "./theme/ThemeProvider";
import { ToastProvider } from "./components/ui/Toast";
import { useApiClient, useConfigOptions, useKeyboardShortcuts } from "./hooks";
import { useProjectStore, getActiveProject } from "./stores/projectStore";
import { useUIStore } from "./stores/uiStore";
import Sidebar from "./components/Sidebar";
const AddProjectModal = lazy(() => import("./components/AddProjectModal"));
import ErrorBoundary from "./components/ErrorBoundary";
import OfflineBanner from "./components/OfflineBanner";
import SkipLink from "./components/SkipLink";
import Dropdown from "./components/ui/Dropdown";
import Tooltip from "./components/ui/Tooltip";
import Dashboard from "./components/Dashboard";
import ConfigEditor from "./components/ConfigEditor";
import DoctorView from "./components/DoctorView";
import SettingsModal from "./components/SettingsModal";
import ConfigSelector from "./components/ConfigSelector";

type Tab = "dashboard" | "workspace" | "project" | "doctor";

const tabs: { id: Tab; labelKey: string; icon: typeof LayoutGrid }[] = [
  { id: "dashboard", labelKey: "dashboard", icon: LayoutGrid },
  { id: "workspace", labelKey: "workspaceTab", icon: FileCode2 },
  { id: "project", labelKey: "projectConfigTab", icon: Bot },
  { id: "doctor", labelKey: "doctor", icon: Stethoscope },
];

const langItems = [
  { label: "English", value: "en", icon: <Globe className="w-3.5 h-3.5" /> },
  { label: "中文", value: "zh", icon: <Globe className="w-3.5 h-3.5" /> },
];

function AppInner() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const { t, lang, setLang } = useI18n();
  const { theme, toggle } = useTheme();
  const client = useApiClient();
  const queryClient = useQueryClient();

  const projects = useProjectStore((s) => s.projects);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const activeProject = useProjectStore(getActiveProject);
  const setSnapshot = useProjectStore((s) => s.setSnapshot);

  const setMobileSidebarOpen = useUIStore((s) => s.setMobileSidebarOpen);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const activeConfigPath = activeProject?.selected_config_path;
  const activeScope = activeProject ? { projectPath: activeProject.path, configPath: activeConfigPath } : undefined;
  const { data: configOptionsData } = useConfigOptions(activeScope);
  const selectedConfigPath = configOptionsData?.selected_config_path || activeConfigPath;

  // Hydrate global projects index and inject current workspace on mount.
  useEffect(() => {
    let cancelled = false;
    client
      .injectCurrentProject()
      .then((data) => {
        if (cancelled) return;
        setSnapshot(data.projects, data.active_project_id);
      })
      .catch(() => {
        // Silently fail; user can still manually add projects.
      });
    return () => {
      cancelled = true;
    };
  }, [client, setSnapshot]);

  const handleAddProject = useCallback(
    async (path: string) => {
      const name = path.split(/[\\/]/).pop() || "project";
      const data = await client.addProject(path, name);
      setSnapshot(data.projects, data.active_project_id);
    },
    [client, setSnapshot]
  );

  const handleSelectProject = useCallback(
    (id: string) => {
      client
        .activateProject(id)
        .then((data) => setSnapshot(data.projects, data.active_project_id))
        .catch(() => {
          // keep current UI selection if activation fails.
        });
      setTab("dashboard");
      setMobileSidebarOpen(false);
    },
    [client, setMobileSidebarOpen, setSnapshot]
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

  const handleSetTab = useCallback((id: Tab) => setTab(id), []);
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

  const handleEditWorkspaceTarget = useCallback(() => {
    setTab("workspace");
  }, []);

  const handleOpenSettings = useCallback(() => {
    setMobileSidebarOpen(false);
    setSettingsOpen(true);
  }, [setMobileSidebarOpen]);

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
    <div className="h-[100dvh] surface-page flex overflow-hidden text-[14px] leading-relaxed">
      {/* Desktop sidebar */}
      <div className="hidden md:block relative z-30">
        <Sidebar
          api={client}
          projects={projects}
          activeProjectId={activeProjectId}
          onSelectProject={handleSelectProject}
          onRemoveProject={handleRemoveProject}
          onAddProject={() => setAddModalOpen(true)}
          onOpenSettings={handleOpenSettings}
        />
      </div>

      {/* Mobile sidebar overlay */}
      <MobileSidebarOverlay
        client={client}
        projects={projects}
        activeProjectId={activeProjectId}
        onSelectProject={handleSelectProject}
        onRemoveProject={handleRemoveProject}
        onAddProject={() => setAddModalOpen(true)}
        onOpenSettings={handleOpenSettings}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-[var(--chrome-height)] min-h-[var(--chrome-height)] border-b border-default chrome-surface flex items-center justify-between px-5 shrink-0 z-10">
          <div className="flex items-center gap-3 min-w-0">
            {/* Mobile hamburger */}
            <button
              type="button"
              onClick={() => setMobileSidebarOpen(true)}
              className="md:hidden icon-touch rounded-md flex items-center justify-center text-secondary hover:text-primary hover:surface-hover transition-colors"
              aria-label={t("openSidebar")}
            >
              <LayoutGrid className="w-4 h-4" />
            </button>

            <div className="min-w-0 flex flex-col justify-center">
              <span className="text-sm font-semibold text-primary tracking-tight leading-tight">
                {activeProject?.name || t("appTitle")}
              </span>
              {activeProject?.path && (
                <Tooltip content={activeProject.path} side="bottom">
                  <span className="block text-[11px] text-tertiary font-mono truncate max-w-[min(52vw,520px)] leading-tight mt-0.5">
                    {activeProject.path}
                  </span>
                </Tooltip>
              )}
            </div>
          </div>

          <div className="flex items-center gap-0.5 shrink-0">
            {configOptionsData?.configs && activeProject && (
              <ConfigSelector
                projectPath={activeProject.path}
                configs={configOptionsData.configs}
                selectedPath={selectedConfigPath}
                onSelect={handleSelectConfig}
                onCreate={handleCreateConfig}
                onRename={handleRenameConfig}
                onDelete={handleDeleteConfig}
              />
            )}
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

        {/* Tabs */}
        <div className="px-4 sm:px-5 pt-3">
          <div className="page-shell border-b border-subtle">
          <div
            className="inline-flex items-center gap-5 min-h-10"
            role="tablist"
            onKeyDown={(e) => {
              const idx = tabs.findIndex((t) => t.id === tab);
              if (e.key === "ArrowRight") {
                e.preventDefault();
                const next = tabs[(idx + 1) % tabs.length];
                setTab(next.id);
                document.getElementById(`tab-${next.id}`)?.focus();
              } else if (e.key === "ArrowLeft") {
                e.preventDefault();
                const prev = tabs[(idx - 1 + tabs.length) % tabs.length];
                setTab(prev.id);
                document.getElementById(`tab-${prev.id}`)?.focus();
              } else if (e.key === "Home") {
                e.preventDefault();
                setTab(tabs[0].id);
                document.getElementById(`tab-${tabs[0].id}`)?.focus();
              } else if (e.key === "End") {
                e.preventDefault();
                setTab(tabs[tabs.length - 1].id);
                document.getElementById(`tab-${tabs[tabs.length - 1].id}`)?.focus();
              }
            }}
          >
            {tabs.map(({ id, labelKey, icon: Icon }) => {
              const active = tab === id;
              return (
                <button
                  type="button"
                  key={id}
                  role="tab"
                  aria-selected={active}
                  aria-controls={`panel-${id}`}
                  id={`tab-${id}`}
                  onClick={() => handleSetTab(id)}
                  className={`relative control-touch flex items-center gap-1.5 border-b-2 px-0 text-[13px] font-medium transition-colors ${
                    active
                      ? "border-[var(--accent)] text-primary"
                      : "border-transparent text-tertiary hover:text-secondary"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {t(labelKey)}
                </button>
              );
            })}
          </div>
          </div>
        </div>

        {/* Content */}
        <main id="main-content" className="flex-1 px-4 sm:px-5 py-5 min-w-0 overflow-y-auto" tabIndex={-1}>
          {activeProject ? (
            <>
              <div role="tabpanel" id="panel-dashboard" aria-labelledby="tab-dashboard" hidden={tab !== "dashboard"} className={`transition-opacity duration-200 ${tab === "dashboard" ? "opacity-100" : "opacity-0 hidden"}`}>
                <Dashboard
                  key={`dash-${activeProject.id}-${selectedConfigPath || "default"}`}
                  projectPath={activeProject.path}
                  configPath={selectedConfigPath}
                  isActive={tab === "dashboard"}
                  onEditTarget={handleEditWorkspaceTarget}
                />
              </div>
              <div role="tabpanel" id="panel-workspace" aria-labelledby="tab-workspace" hidden={tab !== "workspace"} className={`transition-opacity duration-200 ${tab === "workspace" ? "opacity-100" : "opacity-0 hidden"}`}>
                <ConfigEditor key={`workspace-${activeProject.id}-${selectedConfigPath || "default"}`} projectPath={activeProject.path} configPath={selectedConfigPath} view="workspace" />
              </div>
              <div role="tabpanel" id="panel-project" aria-labelledby="tab-project" hidden={tab !== "project"} className={`transition-opacity duration-200 ${tab === "project" ? "opacity-100" : "opacity-0 hidden"}`}>
                <ConfigEditor
                  key={`project-config-${activeProject.id}-${selectedConfigPath || "default"}`}
                  projectPath={activeProject.path}
                  configPath={selectedConfigPath}
                  view="project"
                />
              </div>
              <div role="tabpanel" id="panel-doctor" aria-labelledby="tab-doctor" hidden={tab !== "doctor"} className={`transition-opacity duration-200 ${tab === "doctor" ? "opacity-100" : "opacity-0 hidden"}`}>
                <DoctorView key={`doc-${activeProject.id}-${selectedConfigPath || "default"}`} projectPath={activeProject.path} configPath={selectedConfigPath} />
              </div>
            </>
          ) : (
            <div className="text-center py-20">
              <p className="text-sm text-secondary">{t("selectProject")}</p>
            </div>
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
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
    </div>
  );
}

function MobileSidebarOverlay({
  client,
  projects,
  activeProjectId,
  onSelectProject,
  onRemoveProject,
  onAddProject,
  onOpenSettings,
}: {
  client: ReturnType<typeof useApiClient>;
  projects: ReturnType<typeof useProjectStore.getState>["projects"];
  activeProjectId: string | null;
  onSelectProject: (id: string) => void;
  onRemoveProject: (id: string) => void;
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
