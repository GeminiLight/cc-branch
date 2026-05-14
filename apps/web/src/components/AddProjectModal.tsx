import { useState, useRef, useCallback, useEffect } from "react";
import { FolderOpen, Loader2, Plus, X, MapPin, FolderSearch } from "lucide-react";
import type { APIClient } from "../api/client";
import { useI18n } from "../i18n";
import { projectDirFromConfigPath } from "../utils/projectPath";
import { useToast } from "./ui/Toast";

interface AddProjectModalProps {
  api: APIClient;
  isOpen: boolean;
  onClose: () => void;
  onAdd: (path: string) => Promise<void> | void;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export default function AddProjectModal({ api, isOpen, onClose, onAdd }: AddProjectModalProps) {
  const { t } = useI18n();
  const toast = useToast();
  const [path, setPath] = useState("");
  const [scanning, setScanning] = useState(false);
  const [picking, setPicking] = useState(false);
  const [adding, setAdding] = useState(false);
  const [currentDir, setCurrentDir] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<{
    path_exists: boolean;
    config_exists: boolean;
    project_name: string;
    slots: number;
    status: string;
  } | null>(null);
  const latestRequest = useRef(0);
  const modalRef = useRef<HTMLDivElement>(null);
  const canBrowseSystemDirectory = api.supportsNativeProjectDirectoryPicker();

  const handleScan = useCallback(async (value?: string) => {
    const target = (value ?? path).trim();
    if (!target) return;
    const reqId = ++latestRequest.current;
    setScanning(true);
    setScanResult(null);
    try {
      const data = await api.probeProject(target);
      if (reqId !== latestRequest.current) return;
      setScanResult({
        path_exists: data.path_exists,
        config_exists: data.config_exists,
        project_name: data.project_name,
        slots: data.slots,
        status: data.status,
      });
    } catch (e: unknown) {
      if (reqId !== latestRequest.current) return;
      setScanResult({
        path_exists: false,
        config_exists: false,
        project_name: target.split(/[\\/]/).pop() || "",
        slots: 0,
        status: "missing",
      });
      toast.error(errorMessage(e));
    } finally {
      if (reqId === latestRequest.current) {
        setScanning(false);
      }
    }
  }, [path, api, toast]);

  const handlePickDirectory = useCallback(async () => {
    const reqId = ++latestRequest.current;
    setPicking(true);
    try {
      const selected = await api.pickProjectDirectory(currentDir || undefined);
      if (reqId !== latestRequest.current || !selected) return;
      setPath(selected);
      await handleScan(selected);
    } catch (e: unknown) {
      if (reqId !== latestRequest.current) return;
      toast.error(errorMessage(e));
    } finally {
      if (reqId === latestRequest.current) {
        setPicking(false);
      }
    }
  }, [api, currentDir, handleScan, toast]);

  const handleAdd = useCallback(async () => {
    if (!path.trim() || !scanResult?.path_exists) return;
    setAdding(true);
    try {
      await onAdd(path.trim());
      setPath("");
      setScanResult(null);
      onClose();
      toast.success(t("projectAdded"));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setAdding(false);
    }
  }, [path, scanResult, onAdd, onClose, toast, t]);

  // Load current directory when modal opens
  useEffect(() => {
    if (!isOpen) return;
    api.getApiInfo()
      .then((info) => {
        if (info.config_path) {
          setCurrentDir(projectDirFromConfigPath(info.config_path));
        }
      })
      .catch(() => {
        setCurrentDir(null);
      });
  }, [isOpen, api]);

  // Focus trap
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key !== "Tab" || !modalRef.current) return;
      const focusable = modalRef.current.querySelectorAll<HTMLElement>(
        'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", handleKey);
    const timer = setTimeout(() => {
      const input = modalRef.current?.querySelector<HTMLInputElement>("input");
      input?.focus();
    }, 50);
    return () => {
      document.removeEventListener("keydown", handleKey);
      clearTimeout(timer);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label={t("addProject")}
    >
      <button
        type="button"
        className="absolute inset-0 w-full h-full bg-black/20 backdrop-blur-sm animate-fade-in cursor-default"
        onClick={onClose}
        aria-hidden="true"
        tabIndex={-1}
      />
      <div ref={modalRef} className="relative z-10 w-full max-w-sm surface-card border border-default rounded-lg animate-modal-in">
        <div className="px-5 py-3.5 border-b border-default flex items-center justify-between">
          <h3 className="text-sm font-semibold text-primary">{t("addProject")}</h3>
          <button
            type="button"
            onClick={onClose}
            className="w-6 h-6 rounded flex items-center justify-center text-tertiary hover:text-primary hover:surface-hover transition-colors"
            aria-label={t("cancel")}
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-3">
          <div>
            <label
              htmlFor="project-path-input"
              className="text-[10px] font-semibold text-tertiary uppercase tracking-wide mb-1.5 block"
            >
              {t("projectDirectory")}
            </label>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <FolderOpen className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-tertiary" />
                <input
                  id="project-path-input"
                  type="text"
                  value={path}
                  onChange={(e) => {
                    setPath(e.target.value);
                    setScanResult(null);
                  }}
                  placeholder={t("pathExample")}
                  autoComplete="off"
                  className="w-full h-8 pl-8 pr-3 rounded text-[13px] text-primary bg-[var(--bg-page)] border border-default focus:border-[var(--accent)] focus:outline-none transition-colors placeholder:text-muted"
                  onKeyDown={(e) => {
                    if (e.key !== "Enter") return;
                    if (scanResult?.path_exists) {
                      void handleAdd();
                    } else {
                      handleScan();
                    }
                  }}
                />
              </div>
              {canBrowseSystemDirectory && (
                <button
                  type="button"
                  onClick={() => { void handlePickDirectory(); }}
                  disabled={picking || scanning || adding}
                  className="h-8 px-2.5 rounded text-[11px] font-medium text-secondary hover:text-primary surface-hover transition-colors border border-default flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label={t("browseDirectory")}
                  title={t("browseDirectory")}
                >
                  {picking ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <FolderSearch className="w-3.5 h-3.5" />
                  )}
                </button>
              )}
              <button
                type="button"
                onClick={() => { void handleScan(); }}
                disabled={scanning || adding || !path.trim()}
                className="h-8 px-3 rounded text-[11px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
              >
                {scanning ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  t("scan")
                )}
              </button>
            </div>
          </div>

          {/* Quick actions */}
          <div className="flex items-center gap-2">
            {currentDir && (
              <button
                type="button"
                onClick={() => {
                  setPath(currentDir);
                  void handleScan(currentDir);
                }}
                className="h-6 px-2 rounded text-[11px] font-medium text-secondary hover:text-primary surface-hover transition-colors border border-default flex items-center gap-1"
              >
                <MapPin className="w-3 h-3" />
                {t("useCurrentDir")}
              </button>
            )}
          </div>

          {scanResult && (
            <div
              className={`p-2.5 rounded text-[13px] ${
                scanResult.config_exists
                  ? "success-bg border border-[var(--success)]/10"
                  : !scanResult.path_exists
                    ? "danger-bg border border-[var(--danger)]/10"
                    : "warning-bg border border-[var(--warning)]/10"
              }`}
            >
              <p className="font-semibold text-primary">{scanResult.project_name}</p>
              <p className="text-[11px] text-secondary mt-px">
                {scanResult.config_exists
                  ? `${scanResult.slots} ${t("slots")}`
                  : !scanResult.path_exists
                    ? t("pathNotFound")
                    : t("canInitializeAfterAdd")}
              </p>
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="h-8 px-3 rounded text-[13px] font-medium text-secondary hover:text-primary surface-hover transition-colors"
            >
              {t("cancel")}
            </button>
            <button
              type="button"
              onClick={() => { void handleAdd(); }}
              disabled={adding || !scanResult?.path_exists}
              className="h-8 px-3 rounded text-[13px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {adding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
              {t("addProject")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
