import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { I18nProvider } from "./i18n";
import { BackendFailurePanel, FirstRunEmptyState, PageSwitcher, PanelLoading } from "./App";

describe("PageSwitcher", () => {
  it("renders the four workspace modules as labeled primary navigation tabs", () => {
    const onSelect = vi.fn();

    render(
      <I18nProvider>
        <PageSwitcher tab="dashboard" onSelect={onSelect} />
      </I18nProvider>
    );

    const nav = screen.getByRole("navigation", { name: "Primary navigation" });
    expect(within(nav).getByRole("tab", { name: "Dashboard" })).toHaveTextContent("Dashboard");
    expect(within(nav).getByRole("tab", { name: "Workspace" })).toHaveTextContent("Workspace");
    expect(within(nav).getByRole("tab", { name: "Project config" })).toHaveTextContent("Project config");
    expect(within(nav).getByRole("tab", { name: "Doctor" })).toHaveTextContent("Doctor");

    fireEvent.click(within(nav).getByRole("tab", { name: "Workspace" }));

    expect(onSelect).toHaveBeenCalledWith("workspace");
  });
});

describe("BackendFailurePanel", () => {
  it("shows the backend startup error and retry action", () => {
    const onRetry = vi.fn();
    const onOpenRelease = vi.fn();

    render(
      <I18nProvider>
        <BackendFailurePanel
          message="Bundled backend failed: sidecar missing"
          onRetry={onRetry}
          onOpenRelease={onOpenRelease}
        />
      </I18nProvider>
    );

    expect(screen.getByRole("heading", { name: "CC Branch backend did not start" })).toBeInTheDocument();
    expect(screen.getByText(/localhost backend that listens on 127\.0\.0\.1/i)).toBeInTheDocument();
    expect(screen.getByText(/Project data stays on this machine/i)).toBeInTheDocument();
    expect(screen.getByText("Bundled backend failed: sidecar missing")).toBeInTheDocument();
    expect(screen.getByText(/reinstall the desktop installer for your platform/i)).toBeInTheDocument();
    expect(screen.queryByText(/cc-branch serve/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Download latest installer" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open GitHub Releases" })).toHaveAttribute(
      "href",
      "https://github.com/GeminiLight/cc-branch/releases",
    );

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(onRetry).toHaveBeenCalledOnce();

    fireEvent.click(screen.getByRole("link", { name: "Open GitHub Releases" }));

    expect(onOpenRelease).toHaveBeenCalledWith("https://github.com/GeminiLight/cc-branch/releases");
  });

  it("keeps the retry action disabled while backend restart is pending", async () => {
    let finishRetry: (() => void) | undefined;
    const onRetry = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finishRetry = resolve;
        }),
    );

    render(
      <I18nProvider>
        <BackendFailurePanel
          message="Bundled backend failed: sidecar missing"
          onRetry={onRetry}
          onOpenRelease={vi.fn()}
        />
      </I18nProvider>
    );

    const retry = screen.getByRole("button", { name: "Retry" });
    fireEvent.click(retry);
    fireEvent.click(retry);

    expect(onRetry).toHaveBeenCalledOnce();
    expect(screen.getByRole("button", { name: "Retrying..." })).toBeDisabled();

    finishRetry?.();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Retry" })).not.toBeDisabled();
    });
  });

  it("copies a backend startup diagnostics report", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(
      <I18nProvider>
        <BackendFailurePanel
          message={[
            "CC Branch desktop backend did not start.",
            "Desktop version: 1.0.0",
            "Desktop platform: darwin/aarch64",
            "Backend source: none",
            "Port: 0",
            "Config: /tmp/demo/.cc-branch/config.yaml",
            "State: /tmp/demo/.cc-branch/state.yaml",
            "Error: Bundled backend failed: sidecar missing",
          ].join("\n")}
          onRetry={vi.fn()}
          onOpenRelease={vi.fn()}
        />
      </I18nProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Copy report" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledOnce());
    expect(writeText.mock.calls[0][0]).toContain("CC Branch backend startup report");
    expect(writeText.mock.calls[0][0]).toContain("Desktop version: 1.0.0");
    expect(writeText.mock.calls[0][0]).toContain("Desktop platform: darwin/aarch64");
    expect(writeText.mock.calls[0][0]).toContain("Backend source: none");
    expect(writeText.mock.calls[0][0]).toContain("Config: /tmp/demo/.cc-branch/config.yaml");
    expect(writeText.mock.calls[0][0]).toContain("State: /tmp/demo/.cc-branch/state.yaml");
    expect(writeText.mock.calls[0][0]).toContain("Error: Bundled backend failed: sidecar missing");
    expect(writeText.mock.calls[0][0]).toContain("Open https://github.com/GeminiLight/cc-branch/releases/tag/v1.0.0 and reinstall the desktop installer for this platform.");
    expect(writeText.mock.calls[0][0]).toContain("Paste this report into the GitHub issue if the problem continues.");
    expect(writeText.mock.calls[0][0]).not.toContain("latest desktop installer");
    expect(writeText.mock.calls[0][0]).not.toContain("releases/latest");
    expect(writeText.mock.calls[0][0]).not.toContain("cc-branch serve");
    expect(await screen.findByText("Backend report copied.")).toBeInTheDocument();
  });

  it("links backend startup failures to the current desktop release when the version is known", () => {
    render(
      <I18nProvider>
        <BackendFailurePanel
          message={[
            "CC Branch desktop backend did not start.",
            "Desktop version: 1.0.0",
            "Error: Bundled backend failed: sidecar missing",
          ].join("\n")}
          onRetry={vi.fn()}
          onOpenRelease={vi.fn()}
        />
      </I18nProvider>
    );

    expect(screen.getByRole("link", { name: "Open GitHub Releases" })).toHaveAttribute(
      "href",
      "https://github.com/GeminiLight/cc-branch/releases/tag/v1.0.0",
    );
  });
});

describe("PanelLoading", () => {
  it("explains that desktop startup waits for a local-only backend", () => {
    render(
      <I18nProvider>
        <PanelLoading />
      </I18nProvider>
    );

    expect(screen.getByLabelText("Starting CC Branch")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Starting local backend" })).toBeInTheDocument();
    expect(screen.getByText(/macOS may ask for network permission/i)).toBeInTheDocument();
    expect(screen.getAllByText(/127\.0\.0\.1/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Project data stays on this machine/i)).toBeInTheDocument();
  });
});

describe("FirstRunEmptyState", () => {
  it("shows backend readiness and opens the add project flow", () => {
    const onAddProject = vi.fn();

    render(
      <I18nProvider>
        <FirstRunEmptyState onAddProject={onAddProject} />
      </I18nProvider>
    );

    expect(screen.getByText("Local backend ready")).toBeInTheDocument();
    expect(screen.getByText(/Local only/i)).toBeInTheDocument();
    expect(screen.getByText(/Project data stays on this machine/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Open a project and build your workspace." })).toBeInTheDocument();
    expect(screen.getByText("Local project")).toBeInTheDocument();
    expect(screen.getByText("SSH project")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Add project" }));

    expect(onAddProject).toHaveBeenCalledOnce();
  });
});
