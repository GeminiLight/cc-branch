import { useCallback, useMemo, useState } from "react";
import { PanelLeftClose, PanelLeftOpen, Plus, Settings, X } from "lucide-react";
import { useQueries } from "@tanstack/react-query";
import type { APIClient } from "../api/client";
import { useProjectStore, type ProjectItem } from "../stores/projectStore";
import { useI18n } from "../i18n";
import logoUrl from "../assets/logo/logo.svg";

interface SidebarProps {
  api: APIClient;
  projects: ProjectItem[];
  activeProjectId: string | null;
  onSelectProject: (id: string) => void;
  onAddProject: () => void;
  onOpenSettings: () => void;
  forceExpanded?: boolean;
}

interface ProjectStatus {
  status: "running" | "stopped" | "external" | "no_config" | "error";
  runningCount: number;
  totalCount: number;
}

function statusLabel(t: (key: string) => string, status: ProjectStatus["status"] | undefined): string {
  if (!status) return "…";
  if (status === "running") return t("running");
  if (status === "external") return t("openOnDemand");
  if (status === "stopped") return t("stopped");
  if (status === "no_config") return t("noConfigShort");
  return t("errorLoading");
}

function statusDotClass(status: ProjectStatus["status"] | undefined): string {
  if (status === "running") return "bg-[var(--success)] animate-pulse";
  if (status === "external") return "bg-[var(--accent)]";
  if (status === "stopped") return "bg-[var(--text-tertiary)]";
  if (status === "no_config") return "bg-[var(--warning)]";
  return "bg-[var(--danger)]";
}

const SIDEBAR_COLLAPSED_KEY = "cc-branch.sidebar.collapsed";

const projectPalettes = [
  "linear-gradient(135deg, #0f766e, #134e4a)",
  "linear-gradient(135deg, #c27803, #8a4b10)",
  "linear-gradient(135deg, #2563eb, #164e63)",
  "linear-gradient(135deg, #be123c, #5b21b6)",
  "linear-gradient(135deg, #1f2937, #475569)",
  "linear-gradient(135deg, #4d7c0f, #166534)",
  "linear-gradient(135deg, #6d28d9, #1d4ed8)",
];

function projectInitials(name: string): string {
  const cleaned = name.trim();
  if (!cleaned) return "P";
  const parts = cleaned
    .split(/[^a-zA-Z0-9]+/)
    .filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return cleaned.slice(0, 2).toUpperCase();
}

function paletteForProject(project: ProjectItem): string {
  const key = `${project.name}:${project.path}`;
  const sum = Array.from(key).reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return projectPalettes[sum % projectPalettes.length];
}

function AppMark({ compact = false }: { compact?: boolean }) {
  return (
    <img
      src={logoUrl}
      alt=""
      className={`shrink-0 rounded-lg shadow-sm ${
        compact ? "w-9 h-9" : "w-10 h-10"
      }`}
      aria-hidden="true"
      draggable={false}
    />
  );
}

export default function Sidebar({
  api,
  projects,
  activeProjectId,
  onSelectProject,
  onAddProject,
  onOpenSettings,
  forceExpanded = false,
}: SidebarProps) {
  const { t } = useI18n();
  const removeProject = useProjectStore((s) => s.removeProject);
  const [storedCollapsed, setStoredCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "true";
  });
  const collapsed = forceExpanded ? false : storedCollapsed;

  const toggleCollapsed = useCallback(() => {
    setStoredCollapsed((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(next));
      }
      return next;
    });
  }, []);

  // Use TanStack Query to poll all project statuses
  const statusQueries = useQueries({
    queries: projects.map((p) => ({
      queryKey: ["sidebar", "status", p.id, p.path],
      queryFn: async ({ signal }: { signal: AbortSignal }) => {
        try {
          const data = await api.getStatus(p.path, signal);
          const running = data.slots.filter((s) => s.status === "running").length;
          const external = data.slots.filter((s) => s.status === "external").length;
          return {
            status: running > 0 ? ("running" as const) : external > 0 ? ("external" as const) : ("stopped" as const),
            runningCount: running,
            totalCount: data.slots.length,
          };
        } catch {
          return { status: "no_config" as const, runningCount: 0, totalCount: 0 };
        }
      },
      refetchInterval: 5000,
      refetchIntervalInBackground: false,
      staleTime: 3000,
    })),
  });

  const statuses = useMemo(() => {
    const map: Record<string, ProjectStatus> = {};
    projects.forEach((p, i) => {
      const q = statusQueries[i];
      if (q.data) {
        map[p.id] = q.data;
      }
    });
    return map;
  }, [projects, statusQueries]);

  return (
    <aside
      className={`relative z-30 bg-[var(--sidebar-bg)] border-r border-default flex flex-col h-[100dvh] transition-[width,min-width] duration-200 ease-out ${
        collapsed ? "w-[68px] min-w-[68px]" : "w-[264px] min-w-[264px]"
      }`}
    >
      {/* Brand */}
      <div
        className={`h-[var(--chrome-height)] min-h-[var(--chrome-height)] px-3 flex items-center border-b border-default chrome-surface shrink-0 ${
          collapsed ? "justify-center" : "gap-2.5"
        }`}
      >
        <AppMark compact={collapsed} />
        {!collapsed && (
          <div className="min-w-0">
            <span className="block text-[14px] font-semibold tracking-tight text-primary leading-tight">
              cc-branch
            </span>
            <span className="block text-[11px] text-tertiary leading-tight">
              {t("workspaceControl")}
            </span>
          </div>
        )}
        {!forceExpanded && (
          <button
            type="button"
            onClick={toggleCollapsed}
            className="absolute -right-3 top-[calc((var(--chrome-height)-28px)/2)] z-50 w-6 h-7 rounded-md bg-[var(--bg-card)] border border-default shadow-sm flex items-center justify-center text-tertiary hover:text-primary hover:border-[var(--border-strong)] transition-colors"
            aria-label={collapsed ? t("expand") : t("collapse")}
            title={collapsed ? t("expand") : t("collapse")}
          >
            {collapsed ? (
              <PanelLeftOpen className="w-3.5 h-3.5" />
            ) : (
              <PanelLeftClose className="w-3.5 h-3.5" />
            )}
          </button>
        )}
      </div>

      {/* Projects */}
      <nav
        className={`flex-1 overflow-y-auto py-2 space-y-1 ${
          collapsed ? "px-2" : "px-2.5"
        }`}
        aria-label={t("project")}
      >
        {projects.length === 0 && (
          <div className={`py-8 text-center ${collapsed ? "px-0" : "px-3"}`}>
            <p className="text-[12px] text-tertiary">{collapsed ? "..." : t("noProjects")}</p>
            {!collapsed && <p className="text-[11px] text-muted mt-1">{t("addProjectHint")}</p>}
          </div>
        )}
        {projects.map((p) => {
          const active = activeProjectId === p.id;
          const st = statuses[p.id];
          const initials = projectInitials(p.name);

          return (
            <div
              key={p.id}
              className={`group w-full rounded-md text-[13px] transition-all flex items-center gap-1 relative ${
                active
                  ? "bg-[var(--accent-bg)] text-primary border border-[var(--accent-border)]"
                  : "text-secondary hover:text-primary hover:bg-[var(--bg-hover)] border border-transparent"
              }`}
              title={collapsed ? p.name : undefined}
            >
              {/* Active indicator — left border */}
              {active && !collapsed && (
                <span className="absolute left-0 top-1.5 bottom-1.5 w-[2.5px] rounded-r-full bg-[var(--accent)]" />
              )}

              <button
                type="button"
                onClick={() => onSelectProject(p.id)}
                className={`flex-1 min-w-0 text-left rounded-md flex items-center ${
                  collapsed ? "justify-center px-1 py-1.5" : "gap-2.5 px-2.5 py-2.5"
                }`}
                aria-current={active ? "page" : undefined}
                aria-label={collapsed ? p.name : undefined}
              >
                <div
                  className={`rounded-md border border-white/25 flex items-center justify-center shrink-0 text-white font-black tracking-tight shadow-sm ${
                    collapsed ? "w-10 h-10 text-[12px]" : "w-8 h-8 text-[11px]"
                  }`}
                  style={{ background: paletteForProject(p) }}
                >
                  {initials}
                </div>

                {!collapsed && (
                  <>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <p className="font-semibold truncate leading-tight">{p.name}</p>
                        {p.id === "current" && (
                          <span className="text-[9px] px-1 py-px rounded bg-[var(--accent-bg)] text-[var(--accent)] font-semibold shrink-0">
                            {t("current")}
                          </span>
                        )}
                      </div>
                      <p className="text-[10px] text-tertiary truncate font-mono mt-0.5 leading-tight">
                        {st
                          ? `${st.runningCount}/${st.totalCount} ${t("slots")} / ${statusLabel(t, st.status)}`
                          : "..."}
                      </p>
                    </div>

                    <span
                      className={`w-2 h-2 rounded-full shrink-0 ${statusDotClass(st?.status)}`}
                      title={statusLabel(t, st?.status)}
                      aria-label={statusLabel(t, st?.status)}
                    />
                  </>
                )}
              </button>

              {/* Delete button */}
              {!collapsed && p.id !== "current" && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeProject(p.id);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.stopPropagation();
                      e.preventDefault();
                      removeProject(p.id);
                    }
                  }}
                  className="mr-1 icon-touch sm:min-h-8 sm:min-w-8 rounded-md flex items-center justify-center text-muted opacity-0 group-hover:opacity-100 focus-visible:opacity-100 hover:text-danger hover:danger-bg transition-colors"
                  aria-label={`${t("remove")} ${p.name}`}
                  tabIndex={0}
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          );
        })}
      </nav>

      {/* Add / Settings */}
      <div className={`border-t border-default shrink-0 grid gap-2 ${collapsed ? "p-2" : "p-2.5"}`}>
        <button
          type="button"
          onClick={onAddProject}
          className={`control-touch rounded-lg flex items-center justify-center gap-1.5 text-[12px] font-semibold text-secondary hover:text-primary hover:bg-[var(--accent-bg)] hover:border-[var(--accent-border)] transition-colors border border-dashed border-default ${
            collapsed ? "w-full px-0" : "w-full px-3"
          }`}
          aria-label={t("addProject")}
          title={collapsed ? t("addProject") : undefined}
        >
          <Plus className="w-3.5 h-3.5" />
          {!collapsed && t("addProject")}
        </button>
        <button
          type="button"
          onClick={onOpenSettings}
          className={`control-touch rounded-lg flex items-center justify-center gap-1.5 text-[12px] font-semibold text-secondary hover:text-primary hover:bg-[var(--bg-hover)] transition-colors border border-default ${
            collapsed ? "w-full px-0" : "w-full px-3"
          }`}
          aria-label={t("settings")}
          title={collapsed ? t("settings") : undefined}
        >
          <Settings className="w-3.5 h-3.5" />
          {!collapsed && t("settings")}
        </button>
      </div>
    </aside>
  );
}
