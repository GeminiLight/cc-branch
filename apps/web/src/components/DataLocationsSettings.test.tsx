import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import DataLocationsSettings from "./DataLocationsSettings";
import { I18nProvider } from "../i18n";
import { useProjectStore } from "../stores/projectStore";

const mocks = vi.hoisted(() => ({
  invalidateQueries: vi.fn(),
  apiInfo: {
    current: {
      data: {
        port: 5192,
        config_path: "/tmp/demo/.cc-branch/config.yaml",
        state_path: "/tmp/demo/.cc-branch/state.yaml",
        backend_source: "bundled-sidecar",
        default_shell: "zsh",
      },
      isLoading: false,
      error: null,
    },
  },
  apiClient: {
    current: { revealPath: vi.fn(), restartBackend: vi.fn() },
  },
}));

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({ invalidateQueries: mocks.invalidateQueries }),
}));

vi.mock("../hooks", () => ({
  useApiClient: () => mocks.apiClient.current,
  useApiInfo: () => mocks.apiInfo.current,
}));

function renderSettings() {
  return render(
    <I18nProvider>
      <DataLocationsSettings />
    </I18nProvider>,
  );
}

describe("DataLocationsSettings", () => {
  beforeEach(() => {
    useProjectStore.setState({
      projects: [{ id: "demo", name: "demo", path: "/tmp/demo" }],
      activeProjectId: "demo",
    });
    mocks.apiInfo.current = {
      data: {
        port: 5192,
        config_path: "/tmp/demo/.cc-branch/config.yaml",
        state_path: "/tmp/demo/.cc-branch/state.yaml",
        backend_source: "bundled-sidecar",
        default_shell: "zsh",
      },
      isLoading: false,
      error: null,
    };
    mocks.apiClient.current = {
      revealPath: vi.fn().mockResolvedValue({ success: true }),
      restartBackend: vi.fn().mockResolvedValue({
        port: 5193,
        backend_source: "bundled-sidecar",
      }),
    };
    mocks.invalidateQueries.mockClear();
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  it("shows local data locations without long explanatory text", () => {
    renderSettings();

    expect(screen.getByText("Local data")).toBeInTheDocument();
    expect(screen.getByText("Project directory")).toBeInTheDocument();
    expect(screen.getByText("/tmp/demo")).toBeInTheDocument();
    expect(screen.getByText("Config file")).toBeInTheDocument();
    expect(screen.getByText("/tmp/demo/.cc-branch/config.yaml")).toBeInTheDocument();
    expect(screen.getByText("State file")).toBeInTheDocument();
    expect(screen.getByText("/tmp/demo/.cc-branch/state.yaml")).toBeInTheDocument();
    expect(screen.getByText("Backend")).toBeInTheDocument();
    expect(screen.getByText("127.0.0.1:5192")).toBeInTheDocument();
    expect(screen.getByText("Backend source")).toBeInTheDocument();
    expect(screen.getByText("Bundled sidecar")).toBeInTheDocument();
  });

  it("copies a selected local path", async () => {
    renderSettings();

    fireEvent.click(screen.getAllByRole("button", { name: "Copy" })[0]);

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith("/tmp/demo");
    });
  });

  it("reveals a selected local path in the system file manager", async () => {
    renderSettings();

    fireEvent.click(screen.getAllByRole("button", { name: "Reveal" })[0]);

    await waitFor(() => {
      expect(mocks.apiClient.current.revealPath).toHaveBeenCalledWith("/tmp/demo");
    });
  });

  it("restarts the desktop backend and refreshes runtime info", async () => {
    renderSettings();

    fireEvent.click(screen.getByRole("button", { name: "Restart backend" }));

    await waitFor(() => {
      expect(mocks.apiClient.current.restartBackend).toHaveBeenCalled();
      expect(mocks.invalidateQueries).toHaveBeenCalledWith({ queryKey: ["api", "info"] });
    });
  });

  it("does not show a fake backend restart action for CLI server mode", () => {
    mocks.apiInfo.current = {
      ...mocks.apiInfo.current,
      data: {
        ...mocks.apiInfo.current.data,
        backend_source: "cli",
      },
    };

    renderSettings();

    expect(screen.getByText("Backend source")).toBeInTheDocument();
    expect(screen.getByText("CLI server")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Restart backend" })).not.toBeInTheDocument();
  });
});
