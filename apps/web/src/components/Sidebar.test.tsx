import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { APIClient } from "../api/client";
import { I18nProvider } from "../i18n";
import Sidebar from "./Sidebar";
import type { ProjectItem } from "../stores/projectStore";

function renderSidebar({
  onOpenSettings,
  projects = [],
  activeProjectId = null,
  seedWorkspaceStatus = false,
}: {
  onOpenSettings?: () => void;
  projects?: ProjectItem[];
  activeProjectId?: string | null;
  seedWorkspaceStatus?: boolean;
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
    client.setQueryData(["workspace", "status", "/tmp/active", undefined], {
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
});
