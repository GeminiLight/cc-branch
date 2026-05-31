import { useEffect } from "react";
import { useI18n } from "../i18n";
import { useToast } from "../components/ui/Toast";
import {
  isTauriRuntime,
  markAutoUpdateChecked,
  shouldAutoCheckForUpdates,
} from "../utils/desktopUpdatePrefs";

const DEFAULT_AUTO_UPDATE_DELAY_MS = 6000;

export function useDesktopAutoUpdateCheck(enabled = true, delayMs = DEFAULT_AUTO_UPDATE_DELAY_MS) {
  const { t } = useI18n();
  const toast = useToast();

  useEffect(() => {
    if (!enabled || !isTauriRuntime() || !shouldAutoCheckForUpdates()) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function run() {
      try {
        const { check } = await import("@tauri-apps/plugin-updater");
        const update = await check({ timeout: 30000 });
        if (!cancelled && update) {
          toast.info(t("updateAvailableToast", { version: update.version }), 8000);
        }
      } catch {
        // Keep startup quiet; manual update checks in Settings expose the error.
      } finally {
        markAutoUpdateChecked();
      }
    }

    timer = setTimeout(() => void run(), delayMs);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [delayMs, enabled, t, toast]);
}
