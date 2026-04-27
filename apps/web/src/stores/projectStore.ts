import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface ProjectItem {
  id: string;
  name: string;
  path: string;
}

interface ProjectState {
  projects: ProjectItem[];
  activeProjectId: string | null;

  // Actions
  setProjects: (projects: ProjectItem[]) => void;
  addProject: (project: ProjectItem) => void;
  removeProject: (id: string) => void;
  reorderProjects: (projects: ProjectItem[]) => void;
  setActiveProjectId: (id: string | null) => void;
  injectCurrentProject: (dir: string) => void;
}

const STORAGE_KEY = "cc-branch-projects";

export const useProjectStore = create<ProjectState>()(
  persist(
    (set) => ({
      projects: [],
      activeProjectId: null,

      setProjects: (projects) => set({ projects }),

      addProject: (project) =>
        set((state) => {
          const exists = state.projects.some((p) => p.path === project.path);
          if (exists) return state;
          const next = [...state.projects, project];
          return { projects: next, activeProjectId: project.id };
        }),

      removeProject: (id) =>
        set((state) => {
          const idx = state.projects.findIndex((p) => p.id === id);
          if (idx < 0) return state;
          const next = state.projects.filter((p) => p.id !== id);
          let nextActive = state.activeProjectId;
          if (nextActive === id) {
            nextActive = next[idx]?.id ?? next[next.length - 1]?.id ?? null;
          }
          return { projects: next, activeProjectId: nextActive };
        }),

      reorderProjects: (projects) => set({ projects }),

      setActiveProjectId: (id) => set({ activeProjectId: id }),

      injectCurrentProject: (dir) =>
        set((state) => {
          const name = dir.split(/[\\/]/).pop() || "current";
          const proj: ProjectItem = { id: "current", name, path: dir };
          // Check if a project with the same path already exists
          const samePathIdx = state.projects.findIndex((p) => p.path === dir);
          if (samePathIdx >= 0) {
            const next = [...state.projects];
            next[samePathIdx] = { ...next[samePathIdx], id: "current" };
            return { projects: next, activeProjectId: "current" };
          }
          const existingCurrent = state.projects.findIndex((p) => p.id === "current");
          if (existingCurrent >= 0) {
            const next = [...state.projects];
            next[existingCurrent] = proj;
            return { projects: next, activeProjectId: "current" };
          }
          return { projects: [proj, ...state.projects], activeProjectId: "current" };
        }),
    }),
    {
      name: STORAGE_KEY,
      partialize: (state) => ({ projects: state.projects, activeProjectId: state.activeProjectId }),
    }
  )
);

// Selector for active project (outside store to avoid serialization issues)
export function getActiveProject(state: ProjectState): ProjectItem | null {
  return state.projects.find((p) => p.id === state.activeProjectId) || state.projects[0] || null;
}
