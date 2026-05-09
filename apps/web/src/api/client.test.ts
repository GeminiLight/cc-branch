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
});
