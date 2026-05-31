import { useQueryClient } from "@tanstack/react-query";
import { Copy, Database, Folder, FileText, FolderOpen, RotateCcw, Server } from "lucide-react";
import { useState, type ReactNode } from "react";
import { useApiClient, useApiInfo } from "../hooks";
import { useI18n } from "../i18n";
import { getActiveProject, useProjectStore } from "../stores/projectStore";
import { useToast } from "./ui/Toast";

interface LocationRow {
  key: string;
  label: string;
  value: string;
  icon: ReactNode;
  revealable?: boolean;
}

function backendSourceLabel(source: string, t: (key: string) => string): string {
  if (source === "bundled-sidecar") return t("backendSourceBundledSidecar");
  if (source === "python-fallback") return t("backendSourcePythonFallback");
  if (source === "cli") return t("backendSourceCli");
  return source;
}

function backendCanRestart(source: string | undefined): boolean {
  return source === "bundled-sidecar" || source === "python-fallback";
}

function LocationItem({
  row,
  onCopy,
  onReveal,
}: {
  row: LocationRow;
  onCopy: (value: string) => void;
  onReveal: (value: string) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="rounded-md border border-subtle bg-[var(--bg-page)]/45 px-2.5 py-2 flex items-center gap-2 min-w-0">
      <span className="w-7 h-7 rounded-md bg-[var(--bg-hover)] flex items-center justify-center text-tertiary shrink-0">
        {row.icon}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{row.label}</p>
        <p className="mt-0.5 text-[11px] font-mono text-primary truncate" title={row.value}>
          {row.value}
        </p>
      </div>
      <button
        type="button"
        aria-label={t("copy")}
        onClick={() => onCopy(row.value)}
        className="w-8 h-8 rounded-md flex items-center justify-center text-tertiary hover:text-primary hover:bg-[var(--bg-hover)] transition-colors shrink-0"
      >
        <Copy className="w-3.5 h-3.5" />
      </button>
      {row.revealable && (
        <button
          type="button"
          aria-label={t("reveal")}
          onClick={() => onReveal(row.value)}
          className="w-8 h-8 rounded-md flex items-center justify-center text-tertiary hover:text-primary hover:bg-[var(--bg-hover)] transition-colors shrink-0"
        >
          <FolderOpen className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}

export default function DataLocationsSettings() {
  const { t } = useI18n();
  const api = useApiClient();
  const toast = useToast();
  const queryClient = useQueryClient();
  const activeProject = useProjectStore(getActiveProject);
  const { data, isLoading, error } = useApiInfo();
  const [restartingBackend, setRestartingBackend] = useState(false);
  const canRestartBackend = backendCanRestart(data?.backend_source);

  const rows: LocationRow[] = [];
  if (activeProject?.path) {
    rows.push({
      key: "project",
      label: t("localDataProjectDirectory"),
      value: activeProject.path,
      icon: <Folder className="w-3.5 h-3.5" />,
      revealable: true,
    });
  }
  if (data?.config_path) {
    rows.push({
      key: "config",
      label: t("configFile"),
      value: data.config_path,
      icon: <FileText className="w-3.5 h-3.5" />,
      revealable: true,
    });
  }
  if (data?.state_path) {
    rows.push({
      key: "state",
      label: t("stateFilePath"),
      value: data.state_path,
      icon: <Database className="w-3.5 h-3.5" />,
      revealable: true,
    });
  }
  if (data?.port) {
    rows.push({
      key: "backend",
      label: t("backend"),
      value: `127.0.0.1:${data.port}`,
      icon: <Server className="w-3.5 h-3.5" />,
    });
  }
  if (data?.backend_source) {
    rows.push({
      key: "backend-source",
      label: t("backendSource"),
      value: backendSourceLabel(data.backend_source, t),
      icon: <Server className="w-3.5 h-3.5" />,
    });
  }

  const copyValue = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      toast.success(t("copied"));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  };

  const revealValue = async (value: string) => {
    try {
      await api.revealPath(value);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  };

  const restartBackend = async () => {
    setRestartingBackend(true);
    try {
      await api.restartBackend();
      await queryClient.invalidateQueries({ queryKey: ["api", "info"] });
      toast.success(t("backendRestarted"));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setRestartingBackend(false);
    }
  };

  return (
    <section className="surface-card border border-default rounded-lg p-3.5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg border border-[var(--accent-border)] bg-[var(--accent-bg)] flex items-center justify-center shrink-0">
            <Database className="w-4 h-4 text-[var(--accent)]" />
          </div>
          <div className="min-w-0">
            <h4 className="text-[12px] font-semibold text-primary">{t("localData")}</h4>
          </div>
        </div>
        {canRestartBackend && (
          <button
            type="button"
            onClick={restartBackend}
            disabled={restartingBackend}
            className="h-8 px-2.5 rounded-md border border-default text-[11px] font-medium text-secondary hover:text-primary hover:bg-[var(--bg-hover)] disabled:opacity-60 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5 shrink-0"
            aria-label={t("restartBackend")}
          >
            <RotateCcw className={`w-3.5 h-3.5 ${restartingBackend ? "animate-spin" : ""}`} />
            {restartingBackend ? t("backendRestarting") : t("restartBackend")}
          </button>
        )}
      </div>

      <div className="mt-3 grid gap-2">
        {isLoading ? (
          <div className="h-11 rounded-md bg-[var(--border-subtle)] animate-skeleton" />
        ) : error ? (
          <div className="rounded-md border border-[var(--danger)]/15 danger-bg px-3 py-2 text-[12px] text-primary">
            {String(error)}
          </div>
        ) : (
          rows.map((row) => <LocationItem key={row.key} row={row} onCopy={copyValue} onReveal={revealValue} />)
        )}
      </div>
    </section>
  );
}
