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
  resizable = false,
  desktopDragRegion = false,
}: {
  onOpenSettings?: () => void;
  projects?: ProjectItem[];
  activeProjectId?: string | null;
  seedWorkspaceStatus?: boolean;
  workspaceStatus?: WorkspaceStatus;
  onSetProjectPinned?: (id: string, pinned: boolean) => void;
  onReorderProject?: (id: string, beforeId: string | null, pinned?: boolean) => void;
  resizable?: boolean;
  desktopDragRegion?: boolean;
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
          resizable={resizable}
          desktopDragRegion={desktopDragRegion}
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

    const betaButton = screen.getByText("Beta").closest("button") as HTMLElement;
    const betaRow = betaButton.closest("[data-project-id]") as HTMLElement;
    const elementFromPoint = vi.fn(() => betaButton);
    Object.defineProperty(document, "elementFromPoint", {
      configurable: true,
      value: elementFromPoint,
    });
    vi.spyOn(betaRow, "getBoundingClientRect").mockReturnValue({
      x: 0,
      y: 100,
      top: 100,
      right: 240,
      bottom: 140,
      left: 0,
      width: 240,
      height: 40,
      toJSON: () => ({}),
    });

    fireEvent.pointerDown(screen.getByRole("button", { name: "Move Alpha" }), { button: 0, clientX: 16, clientY: 16 });
    fireEvent.pointerMove(window, { clientX: 16, clientY: 104 });
    fireEvent.pointerUp(window, { clientX: 16, clientY: 104 });

    expect(onReorderProject).toHaveBeenCalledWith("alpha", "beta");
  });

  it("lets desktop users resize the sidebar and persists the width", () => {
    window.localStorage.clear();
    renderSidebar({ resizable: true });

    const resizeHandle = screen.getByRole("separator", { name: "Resize sidebar" });
    const sidebar = resizeHandle.closest("aside") as HTMLElement;
    expect(sidebar).toHaveStyle({ width: "264px" });

    fireEvent.keyDown(resizeHandle, { key: "ArrowRight" });
    expect(sidebar).toHaveStyle({ width: "280px" });
    expect(window.localStorage.getItem("cc-branch.sidebar.width")).toBe("280");

    fireEvent.doubleClick(resizeHandle);
    expect(sidebar).toHaveStyle({ width: "264px" });
  });

  it("marks the sidebar brand rail as a desktop window drag region", () => {
    renderSidebar({ desktopDragRegion: true });

    const dragRegion = screen.getByTestId("desktop-sidebar-drag-region");

    expect(dragRegion).toHaveAttribute("data-tauri-drag-region");
    expect(dragRegion).toHaveTextContent("cc-branch");
  });
});
