import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { APIClient } from "../api/client";
import { I18nProvider } from "../i18n";
import Sidebar from "./Sidebar";
import type { ProjectItem } from "../stores/projectStore";
import type { WorkspaceStatus } from "../types";

function renderSidebar({
  onOpenSettings,
  projects = [],
  activeProjectId = null,
  seedWorkspaceStatus = false,
  workspaceStatus,
  onSetProjectPinned,
  onReorderProject,
}: {
  onOpenSettings?: () => void;
  projects?: ProjectItem[];
  activeProjectId?: string | null;
  seedWorkspaceStatus?: boolean;
  workspaceStatus?: WorkspaceStatus;
  onSetProjectPinned?: (id: string, pinned: boolean) => void;
  onReorderProject?: (id: string, beforeId: string | null, pinned?: boolean) => void;
} = {}) {
  const resolvedOnOpenSettings = onOpenSettings ?? vi.fn(() => undefined);
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  const api = {
    getStatus: vi.fn().mockResolvedValue({
      status: "ready",
      config_path: "",
      state_path: "",
      slots: [{ name: "dev", runtime: "tmux", status: "running", session_name: "demo-dev", windows: [] }],
    }),
  } as unknown as APIClient;

  if (seedWorkspaceStatus) {
    client.setQueryData(["workspace", "status", "/tmp/active", undefined], workspaceStatus ?? {
      status: "ready",
      config_path: "",
      state_path: "",
      slots: [
        { name: "dev", runtime: "tmux", status: "running", session_name: "demo-dev", windows: [] },
        { name: "review", runtime: "terminal", status: "external", session_name: "demo-review", windows: [] },
      ],
    });
  }

  render(
    <QueryClientProvider client={client}>
      <I18nProvider>
        <Sidebar
          api={api}
          projects={projects}
          activeProjectId={activeProjectId}
          onSelectProject={() => {}}
          onRemoveProject={() => {}}
          onSetProjectPinned={onSetProjectPinned ?? (() => {})}
          onReorderProject={onReorderProject ?? (() => {})}
          onAddProject={() => {}}
          onOpenSettings={resolvedOnOpenSettings}
        />
      </I18nProvider>
    </QueryClientProvider>
  );

  return { api, onOpenSettings: resolvedOnOpenSettings };
}

describe("Sidebar", () => {
  it("opens settings from the footer button", () => {
    window.localStorage.clear();
    const { onOpenSettings } = renderSidebar();

    fireEvent.click(screen.getByRole("button", { name: "Settings" }));

    expect(onOpenSettings).toHaveBeenCalledTimes(1);
  });

  it("polls status only for the active project", async () => {
    const { api } = renderSidebar({
      activeProjectId: "active",
      projects: [
        { id: "active", name: "Active", path: "/tmp/active" },
        { id: "idle", name: "Idle", path: "/tmp/idle" },
      ],
    });

    await waitFor(() => {
      expect(api.getStatus).toHaveBeenCalledTimes(1);
    });
    expect(api.getStatus).toHaveBeenCalledWith(
      { projectPath: "/tmp/active", configPath: undefined },
      expect.any(AbortSignal),
    );
  });

  it("derives sidebar status from the shared workspace status cache", async () => {
    renderSidebar({
      activeProjectId: "active",
      seedWorkspaceStatus: true,
      projects: [
        { id: "active", name: "Active", path: "/tmp/active" },
      ],
    });

    expect(await screen.findByText("1/2 · running")).toBeInTheDocument();
    expect(screen.queryByText(/undefined\/undefined/)).not.toBeInTheDocument();
  });

  it("counts split slot groups as one user-visible sidebar tab", async () => {
    renderSidebar({
      activeProjectId: "active",
      seedWorkspaceStatus: true,
      workspaceStatus: {
        status: "ready",
        config_path: "",
        state_path: "",
        slots: [
          { name: "dev", split_group: "dev", runtime: "terminal", status: "running", session_name: "demo-dev", windows: [] },
          { name: "dev-agents", split_group: "dev", runtime: "tmux", status: "running", session_name: "demo-dev-agents", windows: [] },
        ],
      },
      projects: [
        { id: "active", name: "Active", path: "/tmp/active" },
      ],
    });

    expect(await screen.findByText("1/1 · running")).toBeInTheDocument();
  });

  it("shows a stable path subtitle for inactive projects instead of placeholder dots", () => {
    renderSidebar({
      activeProjectId: "active",
      projects: [
        { id: "active", name: "Active", path: "/Users/demo/code/active" },
        { id: "idle", name: "Idle", path: "/Users/demo/code/research-projects" },
      ],
    });

    expect(screen.getByText("~/code/research-projects")).toBeInTheDocument();
    expect(screen.queryByText("...")).not.toBeInTheDocument();
  });

  it("keeps pinned projects in a dedicated section and toggles pin state", () => {
    const onSetProjectPinned = vi.fn();
    renderSidebar({
      activeProjectId: "active",
      onSetProjectPinned,
      projects: [
        { id: "active", name: "Active", path: "/tmp/active" },
        { id: "pinned", name: "Pinned Project", path: "/tmp/pinned", pinned: true },
      ],
    });

    expect(screen.getByText("Pinned")).toBeInTheDocument();
    expect(screen.getByText("Projects")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Unpin Pinned Project" }));
    fireEvent.click(screen.getByRole("button", { name: "Pin Active" }));

    expect(onSetProjectPinned).toHaveBeenCalledWith("pinned", false);
    expect(onSetProjectPinned).toHaveBeenCalledWith("active", true);
  });

  it("reorders projects by dropping one project before another", () => {
    const onReorderProject = vi.fn();
    renderSidebar({
      activeProjectId: "alpha",
      onReorderProject,
      projects: [
        { id: "alpha", name: "Alpha", path: "/tmp/alpha" },
        { id: "beta", name: "Beta", path: "/tmp/beta" },
      ],
    });

    fireEvent.dragStart(screen.getByRole("button", { name: "Move Alpha" }));
    fireEvent.drop(screen.getByRole("button", { name: "Move Beta" }));

    expect(onReorderProject).toHaveBeenCalledWith("alpha", "beta");
  });
});
