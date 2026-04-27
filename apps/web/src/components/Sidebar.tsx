import { useMemo } from "react";
import { FolderGit2, Plus, LayoutGrid, X } from "lucide-react";
import { useQueries } from "@tanstack/react-query";
import type { APIClient } from "../api/client";
import { useProjectStore, type ProjectItem } from "../stores/projectStore";
import { useI18n } from "../i18n";

interface SidebarProps {
  api: APIClient;
  projects: ProjectItem[];
  activeProjectId: string | null;
  onSelectProject: (id: string) => void;
  onAddProject: () => void;
}

interface ProjectStatus {
  status: "running" | "stopped" | "no_config" | "error";
  runningCount: number;
  totalCount: number;
}

export default function Sidebar({
  api,
  projects,
  activeProjectId,
  onSelectProject,
  onAddProject,
}: SidebarProps) {
  const { t } = useI18n();
  const removeProject = useProjectStore((s) => s.removeProject);

  // Use TanStack Query to poll all project statuses
  const statusQueries = useQueries({
    queries: projects.map((p) => ({
      queryKey: ["sidebar", "status", p.id, p.path],
      queryFn: async ({ signal }: { signal: AbortSignal }) => {
        try {
          const data = await api.getStatus(p.path, signal);
          const running = data.slots.filter((s) => s.status === "running").length;
          return {
            status: running > 0 ? ("running" as const) : ("stopped" as const),
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
    <aside className="w-56 min-w-56 surface-card border-r border-default flex flex-col h-[100dvh]">
      {/* Brand */}
      <div className="h-12 px-3 flex items-center gap-2.5 border-b border-default shrink-0">
        <div className="w-7 h-7 rounded-md bg-[var(--accent-bg)] border border-[var(--accent-border)] flex items-center justify-center">
          <LayoutGrid className="w-3.5 h-3.5 text-[var(--accent)]" />
        </div>
        <div className="min-w-0">
          <span className="block text-[13px] font-semibold tracking-tight text-primary leading-tight">
            cc-branch
          </span>
          <span className="block text-[10px] text-tertiary leading-tight">
            {t("workspaceControl")}
          </span>
        </div>
      </div>

      {/* Projects */}
      <nav
        className="flex-1 overflow-y-auto py-1.5 px-1.5 space-y-0.5"
        aria-label={t("project")}
      >
        {projects.length === 0 && (
          <div className="px-3 py-8 text-center">
            <p className="text-[12px] text-tertiary">{t("noProjects")}</p>
            <p className="text-[11px] text-muted mt-1">{t("addProjectHint")}</p>
          </div>
        )}
        {projects.map((p) => {
          const active = activeProjectId === p.id;
          const st = statuses[p.id];

          return (
            <div
              key={p.id}
              className={`group w-full rounded-md text-[13px] transition-all flex items-center gap-1 relative ${
                active
                  ? "bg-[var(--accent-bg)] text-primary shadow-sm"
                  : "text-secondary hover:text-primary hover:surface-hover"
              }`}
            >
              {/* Active indicator — left border */}
              {active && (
                <span className="absolute left-0 top-1.5 bottom-1.5 w-[2.5px] rounded-r-full bg-[var(--accent)]" />
              )}

              <button
                type="button"
                onClick={() => onSelectProject(p.id)}
                className="flex-1 min-w-0 text-left px-2.5 py-2.5 pl-2.5 flex items-center gap-2 rounded-md"
                aria-current={active ? "page" : undefined}
              >
                <div
                  className={`w-6 h-6 rounded-md border flex items-center justify-center shrink-0 ${
                    active
                      ? "bg-[var(--bg-card)] border-[var(--accent-border)]"
                      : "bg-[var(--border-subtle)] border-transparent"
                  }`}
                >
                  <FolderGit2
                    className={`w-3.5 h-3.5 shrink-0 ${
                      active ? "text-[var(--accent)]" : "text-tertiary"
                    }`}
                  />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <p className="font-medium truncate leading-tight">{p.name}</p>
                    {p.id === "current" && (
                      <span className="text-[9px] px-1 py-px rounded bg-[var(--accent-bg)] text-[var(--accent)] font-semibold shrink-0">
                        {t("current")}
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-tertiary truncate font-mono mt-0.5 leading-tight">
                    {st
                      ? `${st.runningCount}/${st.totalCount} ${t("slots")}`
                      : "…"}
                  </p>
                </div>

                <span
                  className={`w-[5px] h-[5px] rounded-full shrink-0 ${
                    st?.status === "running"
                      ? "bg-[var(--success)]"
                      : st?.status === "stopped"
                      ? "bg-tertiary"
                      : st?.status === "no_config"
                      ? "bg-[var(--warning)]"
                      : "bg-[var(--danger)]"
                  } ${st?.status === "running" ? "animate-pulse" : ""}`}
                />
              </button>

              {/* Delete button on hover */}
              {p.id !== "current" && (
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
                  className="mr-1 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto focus:opacity-100 focus:pointer-events-auto w-5 h-5 rounded flex items-center justify-center text-tertiary hover:text-danger hover:danger-bg transition-all"
                  aria-label={`${t("remove")} ${p.name}`}
                  tabIndex={0}
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          );
        })}
      </nav>

      {/* Add */}
      <div className="p-2 border-t border-default shrink-0">
        <button
          type="button"
          onClick={onAddProject}
          className="w-full h-8 rounded-md flex items-center justify-center gap-1.5 text-[11px] font-semibold text-secondary hover:text-primary hover:bg-[var(--accent-bg)] hover:border-[var(--accent-border)] transition-colors border border-dashed border-default"
        >
          <Plus className="w-3.5 h-3.5" />
          {t("addProject")}
        </button>
      </div>
    </aside>
  );
}
