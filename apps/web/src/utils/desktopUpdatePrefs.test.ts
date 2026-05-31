import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  AUTO_UPDATE_ENABLED_KEY,
  AUTO_UPDATE_LAST_CHECK_KEY,
  autoUpdateEnabled,
  isTauriRuntime,
  markAutoUpdateChecked,
  setAutoUpdateEnabled,
  shouldAutoCheckForUpdates,
} from "./desktopUpdatePrefs";

describe("desktop update preferences", () => {
  beforeEach(() => {
    localStorage.clear();
    delete (window as typeof window & { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__;
    delete (window as typeof window & { __TAURI__?: unknown }).__TAURI__;
    vi.restoreAllMocks();
  });

  it("defaults automatic update checks on", () => {
    expect(autoUpdateEnabled()).toBe(true);
    expect(shouldAutoCheckForUpdates(1000)).toBe(true);
  });

  it("persists disabled automatic update checks", () => {
    setAutoUpdateEnabled(false);

    expect(localStorage.getItem(AUTO_UPDATE_ENABLED_KEY)).toBe("false");
    expect(autoUpdateEnabled()).toBe(false);
    expect(shouldAutoCheckForUpdates(1000)).toBe(false);
  });

  it("throttles automatic update checks", () => {
    markAutoUpdateChecked(1000);

    expect(localStorage.getItem(AUTO_UPDATE_LAST_CHECK_KEY)).toBe("1000");
    expect(shouldAutoCheckForUpdates(1000 + 60_000)).toBe(false);
    expect(shouldAutoCheckForUpdates(1000 + 13 * 60 * 60 * 1000)).toBe(true);
  });

  it("detects the Tauri runtime marker", () => {
    expect(isTauriRuntime()).toBe(false);

    (window as typeof window & { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__ = {};

    expect(isTauriRuntime()).toBe(true);
  });
});
