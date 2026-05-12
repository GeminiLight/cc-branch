import { afterEach, describe, expect, it, vi } from "vitest";
import { HTTPClient } from "./client";

describe("HTTPClient workspace scope", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends project and config path query parameters together", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ config_path: "/tmp/demo/.cc-branch/configs/review.yaml", state_path: "/tmp/demo/.cc-branch/states/review.yaml", slots: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await new HTTPClient().getStatus({
      projectPath: "/tmp/demo",
      configPath: "/tmp/demo/.cc-branch/configs/review.yaml",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/status?project_path=%2Ftmp%2Fdemo&config_path=%2Ftmp%2Fdemo%2F.cc-branch%2Fconfigs%2Freview.yaml",
      { signal: undefined }
    );
  });

  it("loads global projects index from backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ version: 1, active_project_id: null, projects: [], storage_path: "/tmp/home/.cc-branch/app/projects.yaml" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await new HTTPClient().getProjectsIndex();

    expect(fetchMock).toHaveBeenCalledWith("/api/projects", { signal: undefined });
  });

  it("injects current project with selected scope", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ version: 1, active_project_id: "current", projects: [], storage_path: "/tmp/home/.cc-branch/app/projects.yaml" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await new HTTPClient().injectCurrentProject({
      projectPath: "/tmp/demo",
      configPath: "/tmp/demo/.cc-branch/configs/review.yaml",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/current?project_path=%2Ftmp%2Fdemo&config_path=%2Ftmp%2Fdemo%2F.cc-branch%2Fconfigs%2Freview.yaml",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("loads global agents settings", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ path: "/tmp/home/.cc-branch/agents.yaml", exists: false, content: "agents: {}\n", agents: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await new HTTPClient().getGlobalAgents();

    expect(fetchMock).toHaveBeenCalledWith("/api/agents/global", { signal: undefined });
  });

  it("creates, renames, and deletes workspace configs through project-scoped endpoints", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ project_path: "/tmp/demo", selected_config_path: "/tmp/demo/.cc-branch/configs/review.yaml", configs: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = new HTTPClient();

    await client.createWorkspaceConfig("/tmp/demo", "review", "/tmp/demo/.cc-branch/config.yaml");
    await client.renameWorkspaceConfig("/tmp/demo", "/tmp/demo/.cc-branch/configs/review.yaml", "release");
    await client.deleteWorkspaceConfig("/tmp/demo", "/tmp/demo/.cc-branch/configs/release.yaml");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/configs/create?project_path=%2Ftmp%2Fdemo",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          name: "review",
          source_config_path: "/tmp/demo/.cc-branch/config.yaml",
        }),
      })
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/configs/rename?project_path=%2Ftmp%2Fdemo",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          config_path: "/tmp/demo/.cc-branch/configs/review.yaml",
          name: "release",
        }),
      })
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/configs/delete?project_path=%2Ftmp%2Fdemo",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          config_path: "/tmp/demo/.cc-branch/configs/release.yaml",
        }),
      })
    );
  });

  it("uses backend native directory picker in the browser client", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ path: "/tmp/demo" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const client = new HTTPClient();
    const picked = await client.pickProjectDirectory("/tmp");

    expect(client.supportsNativeProjectDirectoryPicker()).toBe(true);
    expect(picked).toBe("/tmp/demo");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/project/pick-directory",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ starting_dir: "/tmp" }),
      })
    );
  });

  it("saves global agents settings", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, path: "/tmp/home/.cc-branch/agents.yaml", exists: true, content: "agents: {}\n", agents: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await new HTTPClient().saveGlobalAgents("agents: {}\n", 123, "sha256:test");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/agents/global",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          content: "agents: {}\n",
          base_mtime: 123,
          base_content_hash: "sha256:test",
        }),
      })
    );
  });
});
