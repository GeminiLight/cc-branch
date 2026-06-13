import { afterEach, describe, expect, it, vi } from "vitest";
import { createClient, HTTPClient, TauriClient } from "./client";

const invokeMock = vi.hoisted(() => vi.fn());
const isTauriMock = vi.hoisted(() => vi.fn(() => false));

vi.mock("@tauri-apps/api/core", () => ({
  invoke: invokeMock,
  isTauri: isTauriMock,
}));

describe("HTTPClient workspace scope", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    invokeMock.mockReset();
    isTauriMock.mockReset();
    isTauriMock.mockReturnValue(false);
  });

  it("sends project and config path query parameters together", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ config_path: "/tmp/demo/.cc-branch/configs/review.yaml", state_path: "/tmp/demo/.cc-branch/states/review.yaml", slots: [] }),
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

  it("normalizes network failures into a product-level API error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(new HTTPClient().getStatus()).rejects.toThrow(
      "Cannot reach the local CC Branch backend. Retry from the desktop app or reinstall the desktop installer for this platform from the GitHub Releases page."
    );
  });

  it("preserves request aborts for query cancellation", async () => {
    const abortError = new Error("The operation was aborted");
    abortError.name = "AbortError";
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abortError));

    await expect(new HTTPClient().getStatus()).rejects.toBe(abortError);
  });

  it("reports HTTP errors when the API returns an empty body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      text: async () => "",
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(new HTTPClient().getStatus()).rejects.toThrow("HTTP 502");
  });

  it("does not expose browser JSON parser errors from response mocks", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => {
        throw new SyntaxError("Unexpected end of JSON input");
      },
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(new HTTPClient().getStatus()).rejects.toThrow("Invalid JSON response from API (200)");
  });

  it("keeps HTTP status errors when a json-only error response has an empty body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => {
        throw new SyntaxError("Unexpected end of JSON input");
      },
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(new HTTPClient().getStatus()).rejects.toThrow("HTTP 502");
  });

  it("normalizes missing workspace arrays from older status payloads", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({
        status: "ready",
        project: "demo",
        config_path: "/tmp/demo/.cc-branch/config.yaml",
        state_path: "/tmp/demo/.cc-branch/state.yaml",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const status = await new HTTPClient().getStatus("/tmp/demo");

    expect(status.slots).toEqual([]);
  });

  it("normalizes missing window arrays on status slots", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({
        status: "ready",
        config_path: "/tmp/demo/.cc-branch/config.yaml",
        state_path: "/tmp/demo/.cc-branch/state.yaml",
        slots: [{ name: "dev", runtime: "tmux", status: "running", session_name: "demo-dev" }],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const status = await new HTTPClient().getStatus("/tmp/demo");

    expect(status.slots[0].windows).toEqual([]);
  });

  it("loads the redacted diagnostic bundle with workspace scope", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({
        kind: "cc-branch-diagnostic-bundle",
        generated_at: "2026-05-19T00:00:00Z",
        app: { version: "0.1.3" },
        backend: { port: 5192 },
        schema: {},
        project: { path: "~/code/demo" },
        files: {},
        doctor: { status: "ready", report: "ok" },
        logs: { available: false },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const bundle = await new HTTPClient().getDiagnosticBundle({
      projectPath: "/tmp/demo",
      configPath: "/tmp/demo/.cc-branch/config.yaml",
    });

    expect(bundle.kind).toBe("cc-branch-diagnostic-bundle");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/diagnostics/bundle?project_path=%2Ftmp%2Fdemo&config_path=%2Ftmp%2Fdemo%2F.cc-branch%2Fconfig.yaml",
      { signal: undefined }
    );
  });

  it("reveals a local support path through the backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ success: true, path: "/tmp/demo" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await new HTTPClient().revealPath("/tmp/demo");

    expect(fetchMock).toHaveBeenCalledWith("/api/system/reveal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: "/tmp/demo" }),
    });
  });

  it("does not try to reveal the desktop app from HTTP mode", async () => {
    await expect(new HTTPClient().revealDesktopApp()).resolves.toBeNull();
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

  it("does not try to restart the backend from HTTP mode", async () => {
    await expect(new HTTPClient().restartBackend()).resolves.toBeNull();
  });

  it("opens external support URLs in browser mode", async () => {
    const open = vi.fn();
    vi.stubGlobal("open", open);

    await new HTTPClient().openExternalUrl("https://github.com/GeminiLight/cc-branch/releases");

    expect(open).toHaveBeenCalledWith(
      "https://github.com/GeminiLight/cc-branch/releases",
      "_blank",
      "noopener,noreferrer",
    );
  });

  it("marks HTTP mode as current-project scoped", () => {
    expect(new HTTPClient().shouldInjectCurrentProject()).toBe(true);
  });

  it("does not inject the current directory for app-scoped HTTP service mode", () => {
    (window as Window & { __CC_BRANCH_APP_SCOPE__?: boolean }).__CC_BRANCH_APP_SCOPE__ = true;

    expect(new HTTPClient().shouldInjectCurrentProject()).toBe(false);

    delete (window as Window & { __CC_BRANCH_APP_SCOPE__?: boolean }).__CC_BRANCH_APP_SCOPE__;
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

  it("pins and reorders projects through the project index endpoints", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ version: 1, active_project_id: "a", projects: [], storage_path: "/tmp/home/.cc-branch/app/projects.yaml" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = new HTTPClient();

    await client.setProjectPinned("a", true);
    await client.reorderProject("b", "a");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/projects/pin",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ id: "a", pinned: true }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/projects/reorder",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ id: "b", before_id: "a" }) }),
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

  it("loads global openers settings", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ path: "/tmp/home/.cc-branch/openers.yaml", exists: false, content: "openers: {}\n", openers: [], user_openers: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await new HTTPClient().getGlobalOpeners();

    expect(fetchMock).toHaveBeenCalledWith("/api/openers/global", { signal: undefined });
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

  it("lists remote directories through the backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        path: "/srv",
        parent: "/",
        entries: [{ name: "app", path: "/srv/app" }],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const listing = await new HTTPClient().listRemoteDirectories(
      { host: "gpu-dev", user: "ubuntu", port: 2222 },
      "/srv"
    );

    expect(listing.entries[0]).toEqual({ name: "app", path: "/srv/app" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/remote/list-directories",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          remote: { host: "gpu-dev", user: "ubuntu", port: 2222 },
          path: "/srv",
        }),
      })
    );
  });

  it("lets the backend derive project names when adding a project without a name", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ version: 1, active_project_id: "p1", projects: [], storage_path: "/tmp/home/.cc-branch/app/projects.yaml" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await new HTTPClient().addProject("/tmp/demo/");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/add",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ path: "/tmp/demo/" }),
      })
    );
  });

  it("posts remote project details when adding an SSH project", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ version: 1, active_project_id: "p1", projects: [], storage_path: "/tmp/home/.cc-branch/app/projects.yaml" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await new HTTPClient().addProject({
      name: "app",
      remote: { host: "gpu-dev", user: "ubuntu", port: 2222, cwd: "/srv/app" },
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/add",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          name: "app",
          remote: { host: "gpu-dev", user: "ubuntu", port: 2222, cwd: "/srv/app" },
        }),
      })
    );
  });

  it("posts send action messages to the backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, message: "Sent message to dev:reviewer" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await new HTTPClient().runWorkspaceAction({
      action: "send",
      target: "dev:reviewer",
      message: "Check planner output.",
      projectPath: "/tmp/demo",
      configPath: "/tmp/demo/.cc-branch/config.yaml",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/action?project_path=%2Ftmp%2Fdemo&config_path=%2Ftmp%2Fdemo%2F.cc-branch%2Fconfig.yaml",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          action: "send",
          target: "dev:reviewer",
          message: "Check planner output.",
          stop_removed: undefined,
        }),
      })
    );
  });

  it("loads agent bus events and triggers session restore", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({ events: [], inbox: [], storage_path: "/tmp/bus.jsonl" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({
          success: true,
          code: "agent_inbox_marked_read",
          message: "Marked 1 message(s) as read",
          receipt: { count: 1 },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({
          success: true,
          code: "sessions_restored",
          message: "Restored 1 session binding(s)",
          changed_targets: ["dev:planner"],
        }),
      });
    vi.stubGlobal("fetch", fetchMock);

    const client = new HTTPClient();
    await client.getAgentBus({ projectPath: "/tmp/demo", target: "dev:planner" });
    await client.markAgentInboxRead({ projectPath: "/tmp/demo" }, "dev:planner");
    await client.restoreSessions({ projectPath: "/tmp/demo" });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/agent-bus?project_path=%2Ftmp%2Fdemo&target=dev%3Aplanner",
      { signal: undefined },
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/agent-bus/read?project_path=%2Ftmp%2Fdemo",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target: "dev:planner" }),
      },
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/session/restore?project_path=%2Ftmp%2Fdemo",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      },
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

  it("saves global openers settings", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, path: "/tmp/home/.cc-branch/openers.yaml", exists: true, content: "openers: {}\n", openers: [], user_openers: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await new HTTPClient().saveGlobalOpeners("openers: {}\n", 123, "sha256:test");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/openers/global",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          content: "openers: {}\n",
          base_mtime: 123,
          base_content_hash: "sha256:test",
        }),
      })
    );
  });
});

describe("TauriClient desktop behavior", () => {
  it("does not inject the backend process cwd as a project", () => {
    expect(new TauriClient().shouldInjectCurrentProject()).toBe(false);
  });
});

describe("client factory", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    invokeMock.mockReset();
    isTauriMock.mockReset();
    isTauriMock.mockReturnValue(false);
  });

  it("uses the Tauri client when the runtime exposes the official Tauri marker", () => {
    isTauriMock.mockReturnValue(true);

    expect(createClient()).toBeInstanceOf(TauriClient);
  });

  it("uses the Tauri client for the packaged app host", () => {
    vi.stubGlobal("location", { ...window.location, hostname: "tauri.localhost" });

    expect(createClient()).toBeInstanceOf(TauriClient);
  });

  it("uses the Tauri client for packaged app custom protocols", () => {
    vi.stubGlobal("location", { ...window.location, protocol: "tauri:", hostname: "localhost" });

    expect(createClient()).toBeInstanceOf(TauriClient);
  });

  it("uses the HTTP client in a normal browser runtime", () => {
    isTauriMock.mockReturnValue(false);

    expect(createClient()).toBeInstanceOf(HTTPClient);
  });
});

describe("TauriClient abort handling", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    invokeMock.mockReset();
    isTauriMock.mockReset();
    isTauriMock.mockReturnValue(false);
  });

  it("cancels query methods before resolving the local API port", async () => {
    const controller = new AbortController();
    const reason = new Error("cancelled before IPC");
    controller.abort(reason);

    await expect(new TauriClient().getStatus(undefined, controller.signal)).rejects.toBe(reason);
    expect(invokeMock).not.toHaveBeenCalled();
  });

  it("cancels query methods after resolving the local API port and before fetch", async () => {
    const controller = new AbortController();
    const reason = new Error("cancelled after IPC");
    invokeMock.mockImplementation(async () => {
      controller.abort(reason);
      return { port: 7777, config_path: "/tmp/demo/.cc-branch/config.yaml", state_path: "/tmp/demo/.cc-branch/state.yaml" };
    });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(new TauriClient().getStatus(undefined, controller.signal)).rejects.toBe(reason);
    expect(invokeMock).toHaveBeenCalledWith("get_api_info", undefined);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("passes live query cancellation signals to the local API fetch", async () => {
    invokeMock.mockResolvedValue({
      port: 7777,
      config_path: "/tmp/demo/.cc-branch/config.yaml",
      state_path: "/tmp/demo/.cc-branch/state.yaml",
    });
    const controller = new AbortController();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ slots: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await new TauriClient().getStatus(undefined, controller.signal);

    expect(invokeMock).toHaveBeenCalledWith("get_api_info", undefined);
    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:7777/api/status", {
      signal: controller.signal,
    });
  });

  it("adds desktop diagnostics when the local backend is ready but WebView fetch fails", async () => {
    invokeMock.mockResolvedValue({
      port: 7777,
      config_path: "/tmp/demo/.cc-branch/config.yaml",
      state_path: "/tmp/demo/.cc-branch/state.yaml",
      backend_source: "bundled-sidecar",
      backend_ready: true,
      startup_error: null,
      desktop_version: "1.0.0",
      desktop_platform: "darwin",
      desktop_arch: "aarch64",
    });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(new TauriClient().getStatus()).rejects.toThrow(
      [
        "Cannot reach the local CC Branch backend from the desktop WebView.",
        "Desktop version: 1.0.0",
        "Desktop platform: darwin/aarch64",
        "Backend source: bundled-sidecar",
        "Port: 7777",
        "Config: /tmp/demo/.cc-branch/config.yaml",
        "State: /tmp/demo/.cc-branch/state.yaml",
        "Check whether a proxy, VPN, firewall, or security tool is intercepting 127.0.0.1.",
      ].join("\n"),
    );
  });

  it("surfaces desktop backend startup failures before making API fetches", async () => {
    invokeMock.mockResolvedValue({
      port: 0,
      config_path: "/tmp/demo/.cc-branch/config.yaml",
      state_path: "/tmp/demo/.cc-branch/state.yaml",
      backend_source: "none",
      backend_ready: false,
      startup_error: "Bundled backend sidecar is not available",
      desktop_version: "1.0.0",
      desktop_platform: "darwin",
      desktop_arch: "aarch64",
    });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(new TauriClient().getStatus()).rejects.toThrow(
      [
        "CC Branch desktop backend did not start.",
        "Desktop version: 1.0.0",
        "Desktop platform: darwin/aarch64",
        "Backend source: none",
        "Port: 0",
        "Config: /tmp/demo/.cc-branch/config.yaml",
        "State: /tmp/demo/.cc-branch/state.yaml",
        "Error: Bundled backend sidecar is not available",
      ].join("\n"),
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("restarts the desktop backend through Tauri IPC", async () => {
    invokeMock.mockResolvedValue({
      port: 7778,
      config_path: "/tmp/demo/.cc-branch/config.yaml",
      state_path: "/tmp/demo/.cc-branch/state.yaml",
      backend_ready: true,
      startup_error: null,
    });

    const info = await new TauriClient().restartBackend();

    expect(info.port).toBe(7778);
    expect(invokeMock).toHaveBeenCalledWith("restart_backend", undefined);
  });

  it("opens external support URLs through Tauri IPC", async () => {
    invokeMock.mockResolvedValue(null);

    await new TauriClient().openExternalUrl("https://github.com/GeminiLight/cc-branch/releases/tag/v1.0.0");

    expect(invokeMock).toHaveBeenCalledWith("open_external_url", {
      url: "https://github.com/GeminiLight/cc-branch/releases/tag/v1.0.0",
    });
  });

  it("reveals the installed desktop app through Tauri IPC", async () => {
    invokeMock.mockResolvedValue({ success: true, path: "/Applications/CC Branch.app" });

    await expect(new TauriClient().revealDesktopApp()).resolves.toEqual({
      success: true,
      path: "/Applications/CC Branch.app",
    });

    expect(invokeMock).toHaveBeenCalledWith("reveal_desktop_app", undefined);
  });

  it("surfaces backend startup diagnostics when restart still fails", async () => {
    invokeMock.mockResolvedValue({
      port: 0,
      config_path: "/tmp/demo/.cc-branch/config.yaml",
      state_path: "/tmp/demo/.cc-branch/state.yaml",
      backend_source: "none",
      backend_ready: false,
      startup_error: "Bundled backend failed after retry",
      desktop_version: "1.0.0",
      desktop_platform: "windows",
      desktop_arch: "x86_64",
    });

    await expect(new TauriClient().restartBackend()).rejects.toThrow(
      [
        "CC Branch desktop backend did not start.",
        "Desktop version: 1.0.0",
        "Desktop platform: windows/x86_64",
        "Backend source: none",
        "Port: 0",
        "Config: /tmp/demo/.cc-branch/config.yaml",
        "State: /tmp/demo/.cc-branch/state.yaml",
        "Error: Bundled backend failed after retry",
      ].join("\n"),
    );
    expect(invokeMock).toHaveBeenCalledWith("restart_backend", undefined);
  });

  it("uses Tauri camelCase arguments for the native directory picker", async () => {
    invokeMock.mockResolvedValue("/tmp/demo");

    const picked = await new TauriClient().pickProjectDirectory("/tmp");

    expect(picked).toBe("/tmp/demo");
    expect(invokeMock).toHaveBeenCalledWith("pick_project_directory", { startingDir: "/tmp" });
  });
});
