import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent } from "react";
import { ChevronLeft, ChevronRight, GripVertical, Pin, PinOff, Plus, Server, Settings, X } from "lucide-react";
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
  resizable?: boolean;
  desktopDragRegion?: boolean;
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
  return compactProjectPath(project.display_path || project.path) || t("notChecked");
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
const SIDEBAR_WIDTH_KEY = "cc-branch.sidebar.width";
const SIDEBAR_COLLAPSED_WIDTH = 68;
const SIDEBAR_DEFAULT_WIDTH = 264;
const SIDEBAR_MIN_WIDTH = 220;
const SIDEBAR_MAX_WIDTH = 420;

function clampSidebarWidth(width: number): number {
  return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, Math.round(width)));
}

function projectMonogram(name: string): string {
  const cleaned = name.trim();
  if (!cleaned) return "P";
  return cleaned[0].toUpperCase();
}

function projectHue(project: ProjectItem): number {
  const key = `${project.name}:${project.display_path || project.path}`;
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
  resizable = false,
  desktopDragRegion = false,
}: SidebarProps) {
  const { t } = useI18n();
  const [storedCollapsed, setStoredCollapsed] = useState(() => {
    return getLocalStorageItem(SIDEBAR_COLLAPSED_KEY) === "true";
  });
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const storedValue = getLocalStorageItem(SIDEBAR_WIDTH_KEY);
    if (storedValue === null) return SIDEBAR_DEFAULT_WIDTH;
    const stored = Number(storedValue);
    return Number.isFinite(stored) ? clampSidebarWidth(stored) : SIDEBAR_DEFAULT_WIDTH;
  });
  const [isResizingSidebar, setIsResizingSidebar] = useState(false);
  const [draggingProjectId, setDraggingProjectId] = useState<string | null>(null);
  const [dragOverProjectId, setDragOverProjectId] = useState<string | null>(null);
  const [dragOverPlacement, setDragOverPlacement] = useState<"before" | "after">("before");
  const pointerDragRef = useRef<{ projectId: string; startX: number; startY: number; active: boolean } | null>(null);
  const sidebarResizeRef = useRef<{ startX: number; startWidth: number; currentWidth: number } | null>(null);
  const collapsed = forceExpanded ? false : storedCollapsed;
  const renderedSidebarWidth = collapsed ? SIDEBAR_COLLAPSED_WIDTH : forceExpanded ? SIDEBAR_DEFAULT_WIDTH : sidebarWidth;
  const canResizeSidebar = resizable && !collapsed && !forceExpanded;
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

  const endProjectDrag = useCallback(() => {
    setDraggingProjectId(null);
    setDragOverProjectId(null);
    setDragOverPlacement("before");
    pointerDragRef.current = null;
  }, []);

  const reorderProjectAt = useCallback((projectId: string, targetId: string, placement: "before" | "after") => {
    if (!projectId || projectId === targetId) return;
    const source = projects.find((project) => project.id === projectId);
    const targetIndex = projects.findIndex((project) => project.id === targetId);
    const target = targetIndex >= 0 ? projects[targetIndex] : undefined;
    if (!source || !target) return;
    const nextPinned = Boolean(source.pinned) !== Boolean(target.pinned) ? Boolean(target.pinned) : undefined;
    if (placement === "after") {
      const next = projects.slice(targetIndex + 1).find((project) => Boolean(project.pinned) === Boolean(target.pinned));
      onReorderProject(projectId, next?.id ?? null, nextPinned);
      return;
    }
    if (typeof nextPinned === "boolean") {
      onReorderProject(projectId, targetId, nextPinned);
    } else {
      onReorderProject(projectId, targetId);
    }
  }, [onReorderProject, projects]);

  const beginPointerProjectDrag = useCallback((projectId: string, event: ReactPointerEvent<HTMLElement>) => {
    if (collapsed || event.button !== 0) return;
    const target = event.target as HTMLElement | null;
    if (target?.closest("[data-project-action='true']")) return;
    pointerDragRef.current = {
      projectId,
      startX: event.clientX,
      startY: event.clientY,
      active: false,
    };
  }, [collapsed]);

  const resizeSidebarBy = useCallback((delta: number) => {
    setSidebarWidth((prev) => {
      const next = clampSidebarWidth(prev + delta);
      setLocalStorageItem(SIDEBAR_WIDTH_KEY, String(next));
      return next;
    });
  }, []);

  const resetSidebarWidth = useCallback(() => {
    setSidebarWidth(SIDEBAR_DEFAULT_WIDTH);
    setLocalStorageItem(SIDEBAR_WIDTH_KEY, String(SIDEBAR_DEFAULT_WIDTH));
  }, []);

  const beginSidebarResize = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (!canResizeSidebar || event.button !== 0) return;
    event.preventDefault();
    sidebarResizeRef.current = { startX: event.clientX, startWidth: sidebarWidth, currentWidth: sidebarWidth };
    setIsResizingSidebar(true);
  }, [canResizeSidebar, sidebarWidth]);

  useEffect(() => {
    if (!isResizingSidebar) return;
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    function handlePointerMove(event: globalThis.PointerEvent) {
      const resize = sidebarResizeRef.current;
      if (!resize) return;
      event.preventDefault();
      const next = clampSidebarWidth(resize.startWidth + event.clientX - resize.startX);
      resize.currentWidth = next;
      setSidebarWidth(next);
    }

    function handlePointerUp() {
      const width = sidebarResizeRef.current?.currentWidth ?? sidebarWidth;
      setLocalStorageItem(SIDEBAR_WIDTH_KEY, String(clampSidebarWidth(width)));
      sidebarResizeRef.current = null;
      setIsResizingSidebar(false);
    }

    window.addEventListener("pointermove", handlePointerMove, { passive: false });
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);
    return () => {
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
    };
  }, [isResizingSidebar, sidebarWidth]);

  useEffect(() => {
    function targetFromPoint(clientX: number, clientY: number): { projectId: string; placement: "before" | "after" } | null {
      const element = document.elementFromPoint(clientX, clientY) as HTMLElement | null;
      const row = element?.closest<HTMLElement>("[data-project-id]");
      const projectId = row?.dataset.projectId;
      if (!row || !projectId) return null;
      const rect = row.getBoundingClientRect();
      return {
        projectId,
        placement: clientY > rect.top + rect.height / 2 ? "after" : "before",
      };
    }

    function handlePointerMove(event: globalThis.PointerEvent) {
      const drag = pointerDragRef.current;
      if (!drag) return;
      const moved = Math.abs(event.clientX - drag.startX) + Math.abs(event.clientY - drag.startY);
      if (!drag.active && moved < 6) return;
      if (!drag.active) {
        drag.active = true;
        setDraggingProjectId(drag.projectId);
      }
      event.preventDefault();
      const target = targetFromPoint(event.clientX, event.clientY);
      setDragOverProjectId(target?.projectId && target.projectId !== drag.projectId ? target.projectId : null);
      if (target?.projectId && target.projectId !== drag.projectId) setDragOverPlacement(target.placement);
    }

    function handlePointerUp(event: globalThis.PointerEvent) {
      const drag = pointerDragRef.current;
      if (!drag) return;
      const wasActive = drag.active;
      const sourceId = drag.projectId;
      const target = targetFromPoint(event.clientX, event.clientY);
      endProjectDrag();
      if (wasActive && target?.projectId && target.projectId !== sourceId) {
        reorderProjectAt(sourceId, target.projectId, target.placement);
      }
    }

    window.addEventListener("pointermove", handlePointerMove, { passive: false });
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", endProjectDrag);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", endProjectDrag);
    };
  }, [endProjectDrag, reorderProjectAt]);

  return (
    <aside
      className={`relative z-30 bg-[var(--sidebar-bg)] border-r border-default flex h-full flex-col ${
        isResizingSidebar ? "" : "transition-[width,min-width] duration-200 ease-out"
      }`}
      style={{ width: renderedSidebarWidth, minWidth: renderedSidebarWidth }}
    >
      {canResizeSidebar && (
        <div
          className={`group absolute -right-1.5 top-0 bottom-0 z-40 w-3 cursor-col-resize outline-none ${
            isResizingSidebar ? "bg-[var(--accent-bg)]/45" : ""
          }`}
          aria-label={t("resizeSidebar")}
          title={t("resizeSidebar")}
          role="separator"
          tabIndex={0}
          aria-orientation="vertical"
          aria-valuemin={SIDEBAR_MIN_WIDTH}
          aria-valuemax={SIDEBAR_MAX_WIDTH}
          aria-valuenow={sidebarWidth}
          onPointerDown={beginSidebarResize}
          onDoubleClick={resetSidebarWidth}
          onKeyDown={(event) => {
            if (event.key === "ArrowLeft") {
              event.preventDefault();
              resizeSidebarBy(event.shiftKey ? -40 : -16);
            } else if (event.key === "ArrowRight") {
              event.preventDefault();
              resizeSidebarBy(event.shiftKey ? 40 : 16);
            } else if (event.key === "Home") {
              event.preventDefault();
              setSidebarWidth(SIDEBAR_MIN_WIDTH);
              setLocalStorageItem(SIDEBAR_WIDTH_KEY, String(SIDEBAR_MIN_WIDTH));
            } else if (event.key === "End") {
              event.preventDefault();
              setSidebarWidth(SIDEBAR_MAX_WIDTH);
              setLocalStorageItem(SIDEBAR_WIDTH_KEY, String(SIDEBAR_MAX_WIDTH));
            } else if (event.key === "Enter") {
              event.preventDefault();
              resetSidebarWidth();
            }
          }}
        >
          <span
            className={`absolute left-1/2 top-2 bottom-2 w-px -translate-x-1/2 rounded-full transition-colors ${
              isResizingSidebar
                ? "bg-[var(--accent)]"
                : "bg-transparent group-hover:bg-[var(--accent)]/70 group-focus-visible:bg-[var(--accent)]/80"
            }`}
            aria-hidden="true"
          />
        </div>
      )}

      {/* Brand */}
      <div
        className={`h-[var(--chrome-height)] min-h-[var(--chrome-height)] px-3 flex items-center border-b border-default chrome-surface shrink-0 ${
          collapsed ? "justify-center" : "gap-2.5"
        }`}
        data-testid={desktopDragRegion ? "desktop-sidebar-drag-region" : undefined}
        data-tauri-drag-region={desktopDragRegion ? true : undefined}
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
            data-tauri-drag-region={desktopDragRegion ? "false" : undefined}
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
              endProjectDrag();
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
              const isDropTarget = Boolean(draggingProjectId && draggingProjectId !== p.id && dragOverProjectId === p.id);

              const dropBeforeProject = () => {
                if (!draggingProjectId || draggingProjectId === p.id) return;
                reorderProjectAt(draggingProjectId, p.id, dragOverPlacement);
                endProjectDrag();
              };

              return (
                <div key={p.id} className="relative">
                  {!collapsed && isDropTarget && (
                    <span
                      className={`absolute left-2 right-2 z-10 h-0.5 rounded-full bg-[var(--accent)] shadow-[0_0_0_3px_var(--accent-bg)] ${
                        dragOverPlacement === "after" ? "-bottom-1" : "-top-1"
                      }`}
                    />
                  )}
                  <div
                    data-project-id={p.id}
                    draggable={false}
                    onPointerDown={(event) => beginPointerProjectDrag(p.id, event)}
                    className={`group w-full rounded-md text-[13px] transition-all relative ${
                      active
                        ? "bg-[var(--bg-card)] text-primary shadow-sm"
                        : "text-secondary hover:text-primary hover:bg-[var(--bg-hover)]"
                    } ${isDragging ? "opacity-55 ring-1 ring-[var(--accent)]/35" : ""} ${
                      !collapsed ? "cursor-grab active:cursor-grabbing" : ""
                    }`}
                    title={collapsed ? p.name : undefined}
                    onDragOver={(event) => {
                      if (!draggingProjectId || draggingProjectId === p.id) return;
                      event.preventDefault();
                      event.stopPropagation();
                      event.dataTransfer.dropEffect = "move";
                      setDragOverProjectId(p.id);
                    }}
                    onDragLeave={(event) => {
                      const nextTarget = event.relatedTarget as Node | null;
                      if (nextTarget && event.currentTarget.contains(nextTarget)) return;
                      if (dragOverProjectId === p.id) setDragOverProjectId(null);
                    }}
                    onDrop={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      dropBeforeProject();
                    }}
                  >
                    {active && !collapsed && (
                      <span className="absolute left-0 top-2 bottom-2 w-[2px] rounded-r-full bg-[var(--accent)]" />
                    )}

                    <div
                      className={
                        collapsed
                          ? "flex items-center justify-center px-1 py-1.5"
                          : "grid min-w-0 grid-cols-[18px_minmax(0,1fr)_12px] items-center gap-1 px-2 py-1.5"
                      }
                    >
                      {!collapsed && (
                        <button
                          type="button"
                          draggable={false}
                          onPointerDown={(event) => beginPointerProjectDrag(p.id, event)}
                          className="flex h-8 w-[18px] items-center justify-center rounded-md text-muted/55 transition-colors hover:surface-hover hover:text-primary group-hover:text-tertiary focus-visible:text-primary cursor-grab active:cursor-grabbing"
                          aria-label={t("moveProject", { name: p.name })}
                          title={t("moveProject", { name: p.name })}
                        >
                          <GripVertical className="w-3.5 h-3.5" />
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => onSelectProject(p.id)}
                        className={`min-w-0 text-left rounded-md ${
                          collapsed ? "flex justify-center px-0 py-0" : "grid grid-cols-[34px_minmax(0,1fr)] items-center gap-1"
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
                          <div className="min-w-0 pr-1 transition-[padding] group-hover:pr-14 group-focus-within:pr-14">
                            <p className="flex min-w-0 items-center gap-1.5 text-[13px] font-semibold leading-tight">
                              {p.remote && <Server className="h-3 w-3 shrink-0 text-[var(--accent)]" aria-hidden="true" />}
                              <span className="truncate">{p.name}</span>
                            </p>
                            <p className="mt-0.5 flex min-w-0 items-center gap-1.5 text-[10px] text-tertiary leading-tight">
                              {p.id === "current" && (
                                <span className="rounded bg-[var(--accent-bg)] px-1 py-px text-[9px] font-semibold leading-none text-[var(--accent)]">
                                  {t("current")}
                                </span>
                              )}
                              <span className="min-w-0 truncate">{projectSubtitle(t, p, st)}</span>
                            </p>
                          </div>
                        )}
                      </button>

                      <span
                        className={`rounded-full border border-[var(--sidebar-bg)] shadow-[0_0_0_1px_rgb(255_255_255_/_0.18)] ${
                          collapsed ? "absolute right-2 top-2.5 w-2.5 h-2.5" : "w-2 h-2 shrink-0"
                        } ${statusDotClass(st?.status)}`}
                        title={statusLabel(t, st?.status)}
                        aria-label={statusLabel(t, st?.status)}
                      />

                      {!collapsed && (
                        <div className="absolute right-1.5 top-1/2 flex -translate-y-1/2 items-center gap-0.5 rounded-md bg-[var(--bg-card)]/95 px-0.5 py-0.5 opacity-0 shadow-sm ring-1 ring-[var(--border-subtle)] transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                          <button
                            type="button"
                            draggable={false}
                            data-project-action="true"
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
                              draggable={false}
                              data-project-action="true"
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
                  </div>
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
