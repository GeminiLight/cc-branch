import { getLocalStorageItem, setLocalStorageItem } from "./browserStorage";

export const AUTO_UPDATE_ENABLED_KEY = "cc-branch.desktop.autoUpdate.enabled";
export const AUTO_UPDATE_LAST_CHECK_KEY = "cc-branch.desktop.autoUpdate.lastCheck";

const AUTO_CHECK_INTERVAL_MS = 12 * 60 * 60 * 1000;

interface WindowWithTauri extends Window {
  __TAURI__?: unknown;
  __TAURI_INTERNALS__?: unknown;
}

export function isTauriRuntime(): boolean {
  if (typeof window === "undefined") return false;
  const w = window as WindowWithTauri;
  return Boolean(w.__TAURI__ || w.__TAURI_INTERNALS__);
}

export function autoUpdateEnabled(): boolean {
  return getLocalStorageItem(AUTO_UPDATE_ENABLED_KEY) !== "false";
}

export function setAutoUpdateEnabled(enabled: boolean): void {
  setLocalStorageItem(AUTO_UPDATE_ENABLED_KEY, enabled ? "true" : "false");
}

export function markAutoUpdateChecked(now = Date.now()): void {
  setLocalStorageItem(AUTO_UPDATE_LAST_CHECK_KEY, String(now));
}

export function shouldAutoCheckForUpdates(now = Date.now()): boolean {
  if (!autoUpdateEnabled()) return false;
  const raw = getLocalStorageItem(AUTO_UPDATE_LAST_CHECK_KEY);
  const last = raw ? Number(raw) : 0;
  if (!Number.isFinite(last) || last <= 0) return true;
  return now - last >= AUTO_CHECK_INTERVAL_MS;
}
