import { useCallback, useMemo, useState, type CSSProperties } from "react";
import { ChevronLeft, ChevronRight, GripVertical, Pin, PinOff, Plus, Settings, X } from "lucide-react";
import { useQueries } from "@tanstack/react-query";
import type { APIClient } from "../api/client";
import type { WorkspaceStatus } from "../types";
import type { ProjectItem } from "../stores/projectStore";
import { useI18n } from "../i18n";
import { getLocalStorageItem, setLocalStorageItem } from "../utils/browserStorage";
import logoUrl from "../assets/logo/logo.svg";
import { runningWorkspaceTabCount, workspaceTabCount } from "./workspace-status-view-model";

interface SidebarProps {
  api: APIClient;
  projects: ProjectItem[];
  activeProjectId: string | null;
  onSelectProject: (id: string) => void;
  onRemoveProject: (id: string) => void;
  onSetProjectPinned: (id: string, pinned: boolean) => void;
  onReorderProject: (id: string, beforeId: string | null, pinned?: boolean) => void;
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
  if (!status) return t("notChecked");
  if (status === "running") return t("running");
  if (status === "external") return t("openOnDemand");
  if (status === "stopped") return t("stopped");
  if (status === "no_config") return t("noConfigShort");
  return t("errorLoading");
}

function compactProjectPath(path: string): string {
  const normalized = path.trim().replace(/\\/g, "/");
  if (!normalized) return "";
  const homePath = normalized.match(/^\/Users\/[^/]+(\/.*)?$/);
  if (homePath) return `~${homePath[1] || ""}`;
  if (normalized.length <= 34) return normalized;
  const parts = normalized.split("/").filter(Boolean);
  if (parts.length >= 2) return `…/${parts.slice(-2).join("/")}`;
  return normalized;
}

function projectSubtitle(t: (key: string) => string, project: ProjectItem, status: ProjectStatus | undefined): string {
  if (status) {
    return `${status.runningCount}/${status.totalCount} · ${statusLabel(t, status.status)}`;
  }
  return compactProjectPath(project.path) || t("notChecked");
}

function statusDotClass(status: ProjectStatus["status"] | undefined): string {
  if (!status) return "bg-[var(--text-tertiary)] opacity-50";
  if (status === "running") return "bg-[var(--success)] animate-pulse";
  if (status === "external") return "bg-[var(--accent)]";
  if (status === "stopped") return "bg-[var(--text-tertiary)]";
  if (status === "no_config") return "bg-[var(--warning)]";
  return "bg-[var(--danger)]";
}

function statusFromWorkspace(data: WorkspaceStatus | undefined): ProjectStatus | undefined {
  if (!data) return undefined;
  if (data.status === "needs_init" || data.status === "missing") {
    return { status: "no_config", runningCount: 0, totalCount: 0 };
  }
  if (data.status === "invalid_config") {
    return { status: "error", runningCount: 0, totalCount: 0 };
  }

  const slots = Array.isArray(data.slots) ? data.slots : [];
  const running = runningWorkspaceTabCount(slots);
  const external = slots.some((s) => s.status === "external");
  return {
    status: running > 0 ? "running" : external ? "external" : "stopped",
    runningCount: running,
    totalCount: workspaceTabCount(slots),
  };
}

const SIDEBAR_COLLAPSED_KEY = "cc-branch.sidebar.collapsed";

function projectMonogram(name: string): string {
  const cleaned = name.trim();
  if (!cleaned) return "P";
  return cleaned[0].toUpperCase();
}

function projectHue(project: ProjectItem): number {
  const key = `${project.name}:${project.path}`;
  return Array.from(key).reduce((acc, char) => acc + char.charCodeAt(0), 0) % 360;
}

function projectIconStyle(project: ProjectItem, active: boolean): CSSProperties {
  const hue = projectHue(project);
  return {
    background: `linear-gradient(145deg, hsl(${hue} 85% 97%), hsl(${hue} 82% 90%))`,
    borderColor: `hsl(${hue} 72% 72% / ${active ? "0.55" : "0.32"})`,
    color: `hsl(${hue} 54% 31%)`,
    boxShadow: active
      ? `0 10px 22px hsl(${hue} 70% 45% / 0.18), inset 0 1px 0 rgb(255 255 255 / 0.85)`
      : "inset 0 1px 0 rgb(255 255 255 / 0.72)",
  };
}

function projectSections(projects: ProjectItem[]): Array<{ key: "pinned" | "projects"; titleKey: string; projects: ProjectItem[] }> {
  const pinned = projects.filter((project) => project.pinned);
  const normal = projects.filter((project) => !project.pinned);
  const sections: Array<{ key: "pinned" | "projects"; titleKey: string; projects: ProjectItem[] }> = [];
  if (pinned.length > 0) sections.push({ key: "pinned", titleKey: "pinnedProjects", projects: pinned });
  if (normal.length > 0) sections.push({ key: "projects", titleKey: "projects", projects: normal });
  return sections;
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
  onRemoveProject,
  onSetProjectPinned,
  onReorderProject,
  onAddProject,
  onOpenSettings,
  forceExpanded = false,
}: SidebarProps) {
  const { t } = useI18n();
  const [storedCollapsed, setStoredCollapsed] = useState(() => {
    return getLocalStorageItem(SIDEBAR_COLLAPSED_KEY) === "true";
  });
  const [draggingProjectId, setDraggingProjectId] = useState<string | null>(null);
  const collapsed = forceExpanded ? false : storedCollapsed;
  const sections = useMemo(() => projectSections(projects), [projects]);

  const toggleCollapsed = useCallback(() => {
    setStoredCollapsed((prev) => {
      const next = !prev;
      setLocalStorageItem(SIDEBAR_COLLAPSED_KEY, String(next));
      return next;
    });
  }, []);

  // Reuse the workspace status cache and only poll the active project. Polling every
  // project multiplies config parsing and tmux inspection cost as the sidebar grows.
  const statusQueries = useQueries({
    queries: projects.map((p) => {
      const active = p.id === activeProjectId;
      return {
        queryKey: ["workspace", "status", p.path, p.selected_config_path],
        queryFn: ({ signal }: { signal: AbortSignal }) =>
          api.getStatus({ projectPath: p.path, configPath: p.selected_config_path }, signal),
        enabled: active,
        refetchInterval: active ? 5000 : false,
        refetchIntervalInBackground: false,
        staleTime: 3000,
      };
    }),
  });

  const statuses = useMemo(() => {
    const map: Record<string, ProjectStatus> = {};
    projects.forEach((p, i) => {
      const q = statusQueries[i];
      if (q.isError) {
        map[p.id] = { status: "error", runningCount: 0, totalCount: 0 };
        return;
      }
      const status = statusFromWorkspace(q.data as WorkspaceStatus | undefined);
      if (status) map[p.id] = status;
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
            className="absolute -right-2.5 top-[calc((var(--chrome-height)-24px)/2)] z-50 w-5 h-6 rounded-full bg-[var(--bg-card)] border border-default shadow-sm flex items-center justify-center text-tertiary hover:text-primary hover:border-[var(--border-strong)] transition-colors"
            aria-label={collapsed ? t("expand") : t("collapse")}
            title={collapsed ? t("expand") : t("collapse")}
          >
            {collapsed ? (
              <ChevronRight className="w-3.5 h-3.5" strokeWidth={2} />
            ) : (
              <ChevronLeft className="w-3.5 h-3.5" strokeWidth={2} />
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
            <p className="text-[12px] text-tertiary">{collapsed ? "…" : t("noProjects")}</p>
            {!collapsed && <p className="text-[11px] text-muted mt-1">{t("addProjectHint")}</p>}
          </div>
        )}
        {sections.map((section) => (
          <div
            key={section.key}
            className={collapsed ? "space-y-1" : "space-y-1.5"}
            onDragOver={(event) => {
              if (!draggingProjectId) return;
              event.preventDefault();
            }}
            onDrop={(event) => {
              event.preventDefault();
              if (!draggingProjectId) return;
              const source = projects.find((project) => project.id === draggingProjectId);
              const targetPinned = section.key === "pinned";
              const nextPinned = source && Boolean(source.pinned) !== targetPinned ? targetPinned : undefined;
              if (typeof nextPinned === "boolean") {
                onReorderProject(draggingProjectId, null, nextPinned);
              } else {
                onReorderProject(draggingProjectId, null);
              }
              setDraggingProjectId(null);
            }}
          >
            {!collapsed && sections.length > 1 && (
              <div className="flex items-center justify-between px-2 pt-1 pb-0.5">
                <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-tertiary">
                  {t(section.titleKey)}
                </span>
                <span className="text-[10px] font-mono text-muted">{section.projects.length}</span>
              </div>
            )}
            {section.projects.map((p) => {
          const active = activeProjectId === p.id;
          const st = statuses[p.id];
          const monogram = projectMonogram(p.name);
          const canRemove = p.id !== "current";
          const isDragging = draggingProjectId === p.id;

          return (
            <div
              key={p.id}
              className={`group w-full rounded-md text-[13px] transition-all relative ${
                active
                  ? "bg-[var(--bg-card)] text-primary"
                  : "text-secondary hover:text-primary hover:bg-[var(--bg-hover)]"
              } ${isDragging ? "opacity-55 ring-1 ring-[var(--accent)]/35" : ""}`}
              title={collapsed ? p.name : undefined}
              onDragOver={(event) => {
                if (!draggingProjectId || draggingProjectId === p.id) return;
                event.preventDefault();
                event.stopPropagation();
              }}
              onDrop={(event) => {
                event.preventDefault();
                event.stopPropagation();
                if (!draggingProjectId || draggingProjectId === p.id) return;
                const source = projects.find((project) => project.id === draggingProjectId);
                const nextPinned = source && Boolean(source.pinned) !== Boolean(p.pinned) ? Boolean(p.pinned) : undefined;
                if (typeof nextPinned === "boolean") {
                  onReorderProject(draggingProjectId, p.id, nextPinned);
                } else {
                  onReorderProject(draggingProjectId, p.id);
                }
                setDraggingProjectId(null);
              }}
            >
              {/* Active indicator — left border */}
              {active && !collapsed && (
                <span className="absolute left-0 top-2 bottom-2 w-[2px] rounded-r-full bg-[var(--accent)]" />
              )}

              <button
                type="button"
                onClick={() => onSelectProject(p.id)}
                className={`w-full min-w-0 text-left rounded-md flex items-center ${
                  collapsed ? "justify-center px-1 py-1.5" : `gap-2.5 py-2.5 pl-2.5 ${canRemove ? "pr-[5.75rem]" : "pr-16"}`
                }`}
                aria-current={active ? "page" : undefined}
                aria-label={collapsed ? p.name : undefined}
              >
                <div
                  className={`relative overflow-hidden rounded-lg border flex items-center justify-center shrink-0 font-bold tracking-tight transition-transform group-hover:scale-[1.03] ${
                    collapsed ? "w-10 h-10 text-[16px]" : "w-8 h-8 text-[13px]"
                  }`}
                  style={projectIconStyle(p, active)}
                >
                  <span className="absolute inset-x-1 top-1 h-px bg-white/80" aria-hidden="true" />
                  <span className="relative">{monogram}</span>
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
                      <p className="text-[10px] text-tertiary truncate mt-0.5 leading-tight">
                        {projectSubtitle(t, p, st)}
                      </p>
                    </div>
                  </>
                )}
              </button>

              <span
                className={`absolute rounded-full border border-[var(--sidebar-bg)] shadow-[0_0_0_1px_rgb(255_255_255_/_0.18)] ${
                  collapsed ? "right-2 top-2.5 w-2.5 h-2.5" : "right-3 top-2.5 w-2 h-2"
                } ${statusDotClass(st?.status)}`}
                title={statusLabel(t, st?.status)}
                aria-label={statusLabel(t, st?.status)}
              />

              {!collapsed && (
                <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                  <button
                    type="button"
                    draggable
                    onDragStart={(event) => {
                      setDraggingProjectId(p.id);
                      if (event.dataTransfer) {
                        event.dataTransfer.effectAllowed = "move";
                        event.dataTransfer.setData("text/plain", p.id);
                      }
                    }}
                    onDragEnd={() => setDraggingProjectId(null)}
                    className="icon-touch sm:min-h-7 sm:min-w-7 rounded-md flex items-center justify-center text-muted hover:text-primary hover:surface-hover transition-colors cursor-grab active:cursor-grabbing"
                    aria-label={t("moveProject", { name: p.name })}
                    title={t("moveProject", { name: p.name })}
                  >
                    <GripVertical className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSetProjectPinned(p.id, !p.pinned);
                    }}
                    className={`icon-touch sm:min-h-7 sm:min-w-7 rounded-md flex items-center justify-center transition-colors ${
                      p.pinned
                        ? "text-[var(--accent)] bg-[var(--accent-bg)]"
                        : "text-muted hover:text-primary hover:surface-hover"
                    }`}
                    aria-label={t(p.pinned ? "unpinProject" : "pinProject", { name: p.name })}
                    title={t(p.pinned ? "unpinProject" : "pinProject", { name: p.name })}
                  >
                    {p.pinned ? <PinOff className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}
                  </button>
                  {canRemove && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemoveProject(p.id);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.stopPropagation();
                          e.preventDefault();
                          onRemoveProject(p.id);
                        }
                      }}
                      className="icon-touch sm:min-h-7 sm:min-w-7 rounded-md flex items-center justify-center text-muted hover:text-danger hover:danger-bg transition-colors"
                      aria-label={`${t("remove")} ${p.name}`}
                      tabIndex={0}
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              )}
            </div>
          );
            })}
            {!collapsed && draggingProjectId && (
              <div className="mx-1 h-2 rounded-full border border-dashed border-[var(--accent-border)] bg-[var(--accent-bg)]/40" />
            )}
          </div>
        ))}
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
