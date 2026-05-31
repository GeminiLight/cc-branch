import { render, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n";
import { ToastProvider } from "../components/ui/Toast";
import { useDesktopAutoUpdateCheck } from "./useDesktopAutoUpdateCheck";

const desktopUpdatePrefsMock = vi.hoisted(() => ({
  isTauriRuntime: vi.fn(),
  shouldAutoCheckForUpdates: vi.fn(),
  markAutoUpdateChecked: vi.fn(),
}));

const updaterMock = vi.hoisted(() => ({
  check: vi.fn(),
}));

vi.mock("../utils/desktopUpdatePrefs", () => desktopUpdatePrefsMock);
vi.mock("@tauri-apps/plugin-updater", () => updaterMock);

function AutoUpdateProbe({ enabled, delayMs }: { enabled: boolean; delayMs: number }) {
  useDesktopAutoUpdateCheck(enabled, delayMs);
  return null;
}

function renderProbe(enabled = true, delayMs = 1000) {
  return render(
    <I18nProvider>
      <ToastProvider>
        <AutoUpdateProbe enabled={enabled} delayMs={delayMs} />
      </ToastProvider>
    </I18nProvider>
  );
}

describe("useDesktopAutoUpdateCheck", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    desktopUpdatePrefsMock.isTauriRuntime.mockReturnValue(true);
    desktopUpdatePrefsMock.shouldAutoCheckForUpdates.mockReturnValue(true);
    updaterMock.check.mockResolvedValue(null);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("waits for the startup delay before checking for desktop updates", async () => {
    renderProbe(true, 1000);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(999);
    });

    expect(updaterMock.check).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });

    expect(updaterMock.check).toHaveBeenCalledWith({ timeout: 30000 });
    expect(desktopUpdatePrefsMock.markAutoUpdateChecked).toHaveBeenCalledOnce();
  });

  it("does not check for desktop updates until the app enables it", async () => {
    const { rerender } = render(
      <I18nProvider>
        <ToastProvider>
          <AutoUpdateProbe enabled={false} delayMs={1000} />
        </ToastProvider>
      </I18nProvider>
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(updaterMock.check).not.toHaveBeenCalled();

    rerender(
      <I18nProvider>
        <ToastProvider>
          <AutoUpdateProbe enabled delayMs={1000} />
        </ToastProvider>
      </I18nProvider>
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(updaterMock.check).toHaveBeenCalledOnce();
  });
});
