import { create } from "zustand";

export interface ProjectItem {
  id: string;
  name: string;
  path: string;
  selected_config_path?: string;
}

interface ProjectState {
  projects: ProjectItem[];
  activeProjectId: string | null;

  // Actions
  setSnapshot: (projects: ProjectItem[], activeProjectId: string | null) => void;
  setActiveProjectId: (id: string | null) => void;
}

export const useProjectStore = create<ProjectState>()((set) => ({
  projects: [],
  activeProjectId: null,
  setSnapshot: (projects, activeProjectId) => set({ projects, activeProjectId }),
  setActiveProjectId: (id) => set({ activeProjectId: id }),
}));

// Selector for active project (outside store to avoid serialization issues)
export function getActiveProject(state: ProjectState): ProjectItem | null {
  return state.projects.find((p) => p.id === state.activeProjectId) || state.projects[0] || null;
}
