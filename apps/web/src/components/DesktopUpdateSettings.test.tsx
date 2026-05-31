import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import DesktopUpdateSettings from "./DesktopUpdateSettings";
import { I18nProvider } from "../i18n";

const mocks = vi.hoisted(() => ({
  check: vi.fn(),
  getVersion: vi.fn(),
  relaunch: vi.fn(),
  revealDesktopApp: vi.fn(),
}));

vi.mock("@tauri-apps/plugin-updater", () => ({
  check: mocks.check,
}));

vi.mock("@tauri-apps/plugin-process", () => ({
  relaunch: mocks.relaunch,
}));

vi.mock("@tauri-apps/api/app", () => ({
  getVersion: mocks.getVersion,
}));

vi.mock("../hooks", () => ({
  useApiClient: () => ({
    revealDesktopApp: mocks.revealDesktopApp,
  }),
}));

function renderSettings() {
  return render(
    <I18nProvider>
      <DesktopUpdateSettings />
    </I18nProvider>
  );
}

describe("DesktopUpdateSettings", () => {
  beforeEach(() => {
    localStorage.clear();
    mocks.check.mockReset();
    mocks.getVersion.mockReset();
    mocks.relaunch.mockReset();
    mocks.revealDesktopApp.mockReset();
    mocks.getVersion.mockResolvedValue("0.1.2");
    delete (window as typeof window & { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__;
  });

  it("shows desktop-only state in the browser", () => {
    renderSettings();

    expect(screen.getByText("Updates are available in the desktop app.")).toBeInTheDocument();
    expect(screen.getByText("Uninstall")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reveal app" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Check updates" })).toBeDisabled();
  });

  it("reveals the installed app from the uninstall section in desktop", async () => {
    (window as typeof window & { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__ = {};
    mocks.revealDesktopApp.mockResolvedValue({ success: true });

    renderSettings();
    fireEvent.click(screen.getByRole("button", { name: "Reveal app" }));

    await waitFor(() => expect(mocks.revealDesktopApp).toHaveBeenCalledTimes(1));
  });

  it("checks updates and shows the available version", async () => {
    (window as typeof window & { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__ = {};
    mocks.check.mockResolvedValue({
      version: "0.1.3",
      downloadAndInstall: vi.fn(),
    });

    renderSettings();
    fireEvent.click(screen.getByRole("button", { name: "Check updates" }));

    await waitFor(() => {
      expect(mocks.check).toHaveBeenCalledWith({ timeout: 30000 });
      expect(screen.getByText("Version 0.1.3 is available.")).toBeInTheDocument();
    });
  });

  it("installs an available update and exposes relaunch", async () => {
    (window as typeof window & { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__ = {};
    const downloadAndInstall = vi.fn(async (onEvent: (event: unknown) => void) => {
      onEvent({ event: "Started", data: { contentLength: 100 } });
      onEvent({ event: "Progress", data: { chunkLength: 100 } });
      onEvent({ event: "Finished" });
    });
    mocks.check.mockResolvedValue({ version: "0.1.3", downloadAndInstall });

    renderSettings();
    fireEvent.click(screen.getByRole("button", { name: "Check updates" }));
    fireEvent.click(await screen.findByRole("button", { name: "Install update" }));

    await waitFor(() => {
      expect(downloadAndInstall).toHaveBeenCalled();
      expect(screen.getByText("Update installed. Restart to finish.")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Restart now" }));
    await waitFor(() => expect(mocks.relaunch).toHaveBeenCalledTimes(1));
  });
});
