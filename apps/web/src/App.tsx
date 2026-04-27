import { useState, useEffect, useCallback, lazy, Suspense } from "react";
import {
  LayoutGrid,
  FileCode2,
  Stethoscope,
  Sun,
  Moon,
  Globe,
  ChevronDown,
  X,
} from "lucide-react";
import { I18nProvider, useI18n } from "./i18n";
import { ThemeProvider, useTheme } from "./theme/ThemeProvider";
import { ToastProvider } from "./components/ui/Toast";
import { useApiClient, useKeyboardShortcuts } from "./hooks";
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

type Tab = "dashboard" | "config" | "doctor";

const tabs: { id: Tab; labelKey: string; icon: typeof LayoutGrid }[] = [
  { id: "dashboard", labelKey: "dashboard", icon: LayoutGrid },
  { id: "config", labelKey: "config", icon: FileCode2 },
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

  const projects = useProjectStore((s) => s.projects);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const activeProject = useProjectStore(getActiveProject);
  const setActiveProjectId = useProjectStore((s) => s.setActiveProjectId);
  const injectCurrentProject = useProjectStore((s) => s.injectCurrentProject);
  const addProject = useProjectStore((s) => s.addProject);

  const setMobileSidebarOpen = useUIStore((s) => s.setMobileSidebarOpen);
  const [addModalOpen, setAddModalOpen] = useState(false);

  // Auto-inject current project on mount
  useEffect(() => {
    client
      .getApiInfo()
      .then((info) => {
        const dir = info.config_path
          ? info.config_path.replace(/[\\/]\.cc-branch\.yaml$/, "")
          : "";
        if (dir) injectCurrentProject(dir);
      })
      .catch(() => {
        // Silently fail; user can still manually add projects
      });
  }, [client, injectCurrentProject]);

  const handleAddProject = useCallback(
    (path: string) => {
      const id = `proj_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 5)}`;
      const name = path.split(/[\\/]/).pop() || "project";
      addProject({ id, name, path });
    },
    [addProject]
  );

  const handleSelectProject = useCallback(
    (id: string) => {
      setActiveProjectId(id);
      setTab("dashboard");
      setMobileSidebarOpen(false);
    },
    [setActiveProjectId, setMobileSidebarOpen]
  );

  const handleSetTab = useCallback((id: Tab) => setTab(id), []);

  // Global keyboard shortcuts
  useKeyboardShortcuts({
    onTab1: () => setTab("dashboard"),
    onTab2: () => setTab("config"),
    onTab3: () => setTab("doctor"),
    onEscape: () => {
      setMobileSidebarOpen(false);
      setAddModalOpen(false);
    },
  });

  return (
    <div className="min-h-[100dvh] surface-page flex text-[13px] leading-relaxed">
      {/* Desktop sidebar */}
      <div className="hidden md:block">
        <Sidebar
          api={client}
          projects={projects}
          activeProjectId={activeProjectId}
          onSelectProject={handleSelectProject}
          onAddProject={() => setAddModalOpen(true)}
        />
      </div>

      {/* Mobile sidebar overlay */}
      <MobileSidebarOverlay
        client={client}
        projects={projects}
        activeProjectId={activeProjectId}
        onSelectProject={handleSelectProject}
        onAddProject={() => setAddModalOpen(true)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-12 border-b border-default surface-card flex items-center justify-between px-5 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            {/* Mobile hamburger */}
            <button
              type="button"
              onClick={() => setMobileSidebarOpen(true)}
              className="md:hidden h-7 w-7 rounded-md flex items-center justify-center text-secondary hover:text-primary hover:surface-hover transition-colors"
              aria-label={t("openSidebar")}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>

            <span className="text-sm font-semibold text-primary tracking-tight">
              {activeProject?.name || t("appTitle")}
            </span>
            {activeProject?.path && (
              <Tooltip content={activeProject.path} side="bottom">
                <span className="text-[11px] text-tertiary font-mono truncate max-w-[280px]">
                  {activeProject.path}
                </span>
              </Tooltip>
            )}
          </div>

          <div className="flex items-center gap-0.5 shrink-0">
            <Dropdown
              align="right"
              value={lang}
              onChange={(v) => setLang(v as "en" | "zh")}
              items={langItems}
              trigger={
                <div className="h-7 px-2 rounded-md flex items-center gap-1.5 text-[11px] font-medium text-secondary hover:text-primary hover:surface-hover transition-colors cursor-pointer">
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
                className="h-7 w-7 rounded-md flex items-center justify-center text-secondary hover:text-primary hover:surface-hover transition-colors"
                aria-label={theme === "light" ? t("dark") : t("light")}
                aria-pressed={theme === "dark"}
              >
                {theme === "light" ? (
                  <Moon className="w-3.5 h-3.5" />
                ) : (
                  <Sun className="w-3.5 h-3.5" />
                )}
              </button>
            </Tooltip>
          </div>
        </header>

        {/* Tabs */}
        <div className="px-5 pt-4">
          <div
            className="inline-flex items-center gap-1 rounded-lg border border-default surface-card p-1 shadow-sm"
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
                  className={`relative h-8 rounded-md flex items-center gap-1.5 px-3 text-[13px] font-medium transition-colors ${
                    active
                      ? "bg-[var(--accent-bg)] text-primary shadow-sm"
                      : "text-tertiary hover:text-secondary hover:surface-hover"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {t(labelKey)}
                  {active && <span className="absolute left-1.5 top-2 bottom-2 w-[2px] rounded-full bg-[var(--accent)]" />}
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <main id="main-content" className="flex-1 px-5 py-4 min-w-0 overflow-y-auto" tabIndex={-1}>
          {activeProject ? (
            <>
              <div role="tabpanel" id="panel-dashboard" aria-labelledby="tab-dashboard" hidden={tab !== "dashboard"}>
                <Dashboard key={`dash-${activeProject.id}`} projectPath={activeProject.path} isActive={tab === "dashboard"} />
              </div>
              <div role="tabpanel" id="panel-config" aria-labelledby="tab-config" hidden={tab !== "config"}>
                <ConfigEditor key={`cfg-${activeProject.id}`} projectPath={activeProject.path} />
              </div>
              <div role="tabpanel" id="panel-doctor" aria-labelledby="tab-doctor" hidden={tab !== "doctor"}>
                <DoctorView key={`doc-${activeProject.id}`} projectPath={activeProject.path} />
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
    </div>
  );
}

function MobileSidebarOverlay({
  client,
  projects,
  activeProjectId,
  onSelectProject,
  onAddProject,
}: {
  client: ReturnType<typeof useApiClient>;
  projects: ReturnType<typeof useProjectStore.getState>["projects"];
  activeProjectId: string | null;
  onSelectProject: (id: string) => void;
  onAddProject: () => void;
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
          onAddProject={onAddProject}
        />
        <button
          type="button"
          onClick={() => setMobileSidebarOpen(false)}
          className="absolute -right-10 top-3 w-8 h-8 rounded-full bg-[var(--bg-card)]/90 backdrop-blur flex items-center justify-center text-primary shadow-md border border-default"
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
