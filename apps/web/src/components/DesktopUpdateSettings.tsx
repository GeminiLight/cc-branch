import { useEffect, useState } from "react";
import type { DownloadEvent, Update } from "@tauri-apps/plugin-updater";
import { CheckCircle2, Download, FolderOpen, Loader2, RefreshCw, RotateCw, ShieldCheck, Trash2 } from "lucide-react";
import { useApiClient } from "../hooks";
import { useI18n } from "../i18n";
import {
  autoUpdateEnabled,
  isTauriRuntime,
  markAutoUpdateChecked,
  setAutoUpdateEnabled,
} from "../utils/desktopUpdatePrefs";
import { useToast } from "./ui/Toast";

type UpdateStatus = "idle" | "checking" | "current" | "available" | "installing" | "installed" | "error" | "unsupported";

function statusTone(status: UpdateStatus): string {
  if (status === "available") return "warning-bg border-[var(--warning)]/15";
  if (status === "error") return "danger-bg border-[var(--danger)]/15";
  if (status === "current" || status === "installed") return "success-bg border-[var(--success)]/15";
  return "bg-[var(--bg-page)] border-default";
}

export default function DesktopUpdateSettings() {
  const { t } = useI18n();
  const api = useApiClient();
  const toast = useToast();
  const supported = isTauriRuntime();
  const [enabled, setEnabled] = useState(autoUpdateEnabled);
  const [status, setStatus] = useState<UpdateStatus>(supported ? "idle" : "unsupported");
  const [currentVersion, setCurrentVersion] = useState<string>("--");
  const [pendingUpdate, setPendingUpdate] = useState<Update | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revealingApp, setRevealingApp] = useState(false);

  useEffect(() => {
    if (!supported) return;
    let cancelled = false;
    import("@tauri-apps/api/app")
      .then(({ getVersion }) => getVersion())
      .then((version) => {
        if (!cancelled) setCurrentVersion(version);
      })
      .catch(() => {
        if (!cancelled) setCurrentVersion("--");
      });
    return () => {
      cancelled = true;
    };
  }, [supported]);

  function handleToggle(next: boolean) {
    setEnabled(next);
    setAutoUpdateEnabled(next);
  }

  async function handleCheck() {
    if (!supported) return;
    setStatus("checking");
    setError(null);
    setPendingUpdate(null);
    setProgress(null);
    try {
      const { check } = await import("@tauri-apps/plugin-updater");
      const update = await check({ timeout: 30000 });
      markAutoUpdateChecked();
      if (update) {
        setPendingUpdate(update);
        setStatus("available");
      } else {
        setStatus("current");
      }
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleInstall() {
    if (!pendingUpdate) return;
    setStatus("installing");
    setError(null);
    setProgress(0);
    let total = 0;
    let downloaded = 0;
    const onEvent = (event: DownloadEvent) => {
      if (event.event === "Started") {
        total = event.data.contentLength || 0;
        downloaded = 0;
        setProgress(total ? 0 : null);
      } else if (event.event === "Progress") {
        downloaded += event.data.chunkLength;
        if (total) setProgress(Math.min(100, Math.round((downloaded / total) * 100)));
      } else if (event.event === "Finished") {
        setProgress(100);
      }
    };

    try {
      await pendingUpdate.downloadAndInstall(onEvent, { timeout: 120000 });
      setStatus("installed");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleRelaunch() {
    const { relaunch } = await import("@tauri-apps/plugin-process");
    await relaunch();
  }

  async function handleRevealDesktopApp() {
    if (!supported) return;
    setRevealingApp(true);
    try {
      await api.revealDesktopApp();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setRevealingApp(false);
    }
  }

  const busy = status === "checking" || status === "installing";
  const statusText = {
    idle: t("updatesIdle"),
    checking: t("updatesChecking"),
    current: t("updatesCurrent"),
    available: pendingUpdate ? t("updatesAvailable", { version: pendingUpdate.version }) : t("updatesAvailableUnknown"),
    installing: progress === null ? t("updatesInstalling") : t("updatesInstallingProgress", { progress }),
    installed: t("updatesInstalled"),
    error: error || t("updatesError"),
    unsupported: t("updatesDesktopOnly"),
  }[status];

  return (
    <section className="surface-card border border-default rounded-lg p-3.5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg border border-[var(--accent-border)] bg-[var(--accent-bg)] flex items-center justify-center shrink-0">
            <ShieldCheck className="w-4 h-4 text-[var(--accent)]" />
          </div>
          <div className="min-w-0">
            <h4 className="text-[12px] font-semibold text-primary">{t("desktopUpdates")}</h4>
          </div>
        </div>
        <button
          type="button"
          onClick={() => handleToggle(!enabled)}
          disabled={!supported}
          className={`relative w-10 h-6 rounded-full border transition-colors disabled:opacity-50 ${
            enabled ? "bg-[var(--accent)] border-[var(--accent)]" : "bg-[var(--bg-page)] border-default"
          }`}
          aria-pressed={enabled}
          aria-label={t("autoCheckUpdates")}
        >
          <span
            className={`absolute top-0.5 h-[18px] w-[18px] rounded-full bg-white shadow-sm transition-transform ${
              enabled ? "translate-x-[18px]" : "translate-x-0.5"
            }`}
          />
        </button>
      </div>

      <div className={`mt-3 rounded-md border px-3 py-2 ${statusTone(status)}`}>
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[12px] font-medium text-primary truncate">{statusText}</p>
            <p className="text-[10px] font-mono text-tertiary mt-px">{t("currentVersion", { version: currentVersion })}</p>
          </div>
          {status === "current" || status === "installed" ? (
            <CheckCircle2 className="w-4 h-4 text-[var(--success)] shrink-0" />
          ) : null}
        </div>
        {status === "installing" && progress !== null && (
          <div className="mt-2 h-1.5 rounded-full bg-[var(--border-subtle)] overflow-hidden">
            <div className="h-full bg-[var(--accent)] transition-[width]" style={{ width: `${progress}%` }} />
          </div>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
        <button
          type="button"
          onClick={() => { void handleCheck(); }}
          disabled={!supported || busy}
          className="control-touch px-3 rounded-md border border-default text-[12px] font-medium text-secondary hover:text-primary hover:surface-hover disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
        >
          {status === "checking" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
          {t("checkForUpdates")}
        </button>
        {pendingUpdate && status === "available" && (
          <button
            type="button"
            onClick={() => { void handleInstall(); }}
            className="control-touch px-3 rounded-md bg-[var(--accent)] text-white text-[12px] font-semibold inline-flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            {t("installUpdate")}
          </button>
        )}
        {status === "installed" && (
          <button
            type="button"
            onClick={() => { void handleRelaunch(); }}
            className="control-touch px-3 rounded-md bg-[var(--accent)] text-white text-[12px] font-semibold inline-flex items-center gap-1.5"
          >
            <RotateCw className="w-3.5 h-3.5" />
            {t("restartNow")}
          </button>
        )}
      </div>

      <div className="mt-3 rounded-md border border-default bg-[var(--bg-page)] px-3 py-2">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-2">
          <Trash2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-tertiary" />
          <div className="min-w-0">
            <p className="text-[12px] font-semibold text-primary">{t("uninstallDesktop")}</p>
            <p className="mt-0.5 text-[11px] leading-relaxed text-tertiary">{t("uninstallDesktopHint")}</p>
          </div>
          </div>
          <button
            type="button"
            onClick={() => { void handleRevealDesktopApp(); }}
            disabled={!supported || revealingApp}
            className="h-8 shrink-0 rounded-md border border-default px-2.5 text-[11px] font-medium text-secondary transition-colors hover:bg-[var(--bg-hover)] hover:text-primary disabled:cursor-not-allowed disabled:opacity-50 inline-flex items-center gap-1.5"
          >
            {revealingApp ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FolderOpen className="h-3.5 w-3.5" />}
            {t("revealDesktopApp")}
          </button>
        </div>
      </div>
    </section>
  );
}
