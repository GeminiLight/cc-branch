import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, CopyPlus, FileCode2, PencilLine, Plus, Trash2 } from "lucide-react";
import type { ConfigOption } from "../types";
import { useI18n } from "../i18n";
import { useToast } from "./ui/Toast";
import Modal from "./ui/Modal";
import { compactPathTail } from "../utils/pathDisplay";

interface ConfigSelectorProps {
  projectPath?: string;
  configs: ConfigOption[];
  selectedPath?: string;
  onSelect: (path: string) => void;
  onCreate?: (name: string, sourceConfigPath?: string) => Promise<void> | void;
  onRename?: (path: string, name: string) => Promise<void> | void;
  onDelete?: (path: string) => Promise<void> | void;
}

type InlineAction = "create" | "duplicate" | "rename" | null;
type PendingAction = "delete" | null;

function selectedConfig(configs: ConfigOption[], selectedPath?: string): ConfigOption | undefined {
  return configs.find((item) => item.path === selectedPath) || configs.find((item) => item.selected) || configs[0];
}

function configCountText(t: (key: string, vars?: Record<string, string | number>) => string, count: number): string {
  return t(count === 1 ? "configCountOne" : "configCount", { count });
}

function displayLabel(config: ConfigOption | undefined, t: (key: string) => string): string {
  if (!config) return "";
  return config.is_default ? t("defaultConfig") : config.label;
}

export function ConfigContextNotice({ configs, selectedPath }: Omit<ConfigSelectorProps, "onSelect">) {
  const { t } = useI18n();
  const selected = selectedConfig(configs, selectedPath);

  if (!selected) return null;

  return (
    <div className="page-shell">
      <div className="min-h-10 rounded-md border border-default surface-card px-3 py-2 flex flex-col lg:flex-row lg:items-center gap-2 lg:gap-3 text-[12px]">
        <div className="flex items-center gap-2 min-w-0">
          <FileCode2 className="w-3.5 h-3.5 shrink-0 text-tertiary" />
          <span className="text-tertiary font-medium">{t("activeWorkspaceProfile")}</span>
          <span className="rounded-md bg-[var(--accent-bg)] px-1.5 py-0.5 text-[11px] font-semibold text-[var(--accent)]">
            {selected.label}
          </span>
          <span className="text-tertiary">{configCountText(t, configs.length)}</span>
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2 min-w-0 text-[11px] font-mono text-tertiary">
          <span className="truncate" title={selected.path}>{selected.path}</span>
          <span className="hidden sm:inline text-muted">·</span>
          <span className="text-muted">{t("stateFile")}:</span>
          <span className="truncate" title={selected.state_path}>
            {selected.state_path}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function ConfigSelector({
  projectPath,
  configs,
  selectedPath,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: ConfigSelectorProps) {
  const { t } = useI18n();
  const toast = useToast();
  const menuRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const inlineInputRef = useRef<HTMLInputElement | null>(null);
  const [open, setOpen] = useState(false);
  const [inlineAction, setInlineAction] = useState<InlineAction>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [draftName, setDraftName] = useState("");
  const [busy, setBusy] = useState(false);
  const selected = selectedConfig(configs, selectedPath);
  const canManage = Boolean(projectPath);
  const canModifySelected = Boolean(selected && !selected.is_default && selected.exists);
  const countLabel = configCountText(t, configs.length);

  useEffect(() => {
    if (!open) return;
    function handlePointerDown(event: PointerEvent) {
      const target = event.target as Node;
      if (menuRef.current?.contains(target) || triggerRef.current?.contains(target)) return;
      setOpen(false);
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  useEffect(() => {
    if (!inlineAction) return;
    inlineInputRef.current?.focus();
    inlineInputRef.current?.select();
  }, [inlineAction]);

  function openInlineAction(action: Exclude<InlineAction, null>) {
    setOpen(true);
    setPendingAction(null);
    setInlineAction(action);
    if (action === "create") {
      setDraftName("");
    } else if (action === "duplicate") {
      setDraftName(`${selected?.is_default ? "workspace" : selected?.label || "workspace"}-copy`);
    } else if (action === "rename") {
      setDraftName(selected?.is_default ? "" : selected?.label || "");
    }
  }

  function openDeleteAction() {
    setOpen(false);
    setInlineAction(null);
    setDraftName("");
    setPendingAction("delete");
  }

  async function confirmInlineAction() {
    if (!inlineAction || busy) return;
    const name = draftName.trim();
    if (!name) return;
    try {
      setBusy(true);
      if (inlineAction === "create") {
        await onCreate?.(name, undefined);
        toast.success(t("workspaceProfileCreated"));
      } else if (inlineAction === "duplicate" && selected) {
        await onCreate?.(name, selected.path);
        toast.success(t("workspaceProfileCreated"));
      } else if (inlineAction === "rename" && selected) {
        await onRename?.(selected.path, name);
        toast.success(t("workspaceProfileRenamed"));
      }
      setInlineAction(null);
      setDraftName("");
      setOpen(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }

  async function confirmDeleteAction() {
    if (!selected || busy) return;
    try {
      setBusy(true);
      await onDelete?.(selected.path);
      toast.success(t("workspaceProfileDeleted"));
      setPendingAction(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }

  function selectConfig(config: ConfigOption) {
    if (!config.exists) return;
    setOpen(false);
    onSelect(config.path);
  }

  const modalTitle =
    t("deleteWorkspaceProfile");
  const inlineTitle =
    inlineAction === "create"
      ? t("newWorkspaceProfile")
      : inlineAction === "duplicate"
        ? t("duplicateWorkspaceProfile")
        : t("renameWorkspaceProfile");
  const inlineDescription =
    inlineAction === "create"
      ? t("newWorkspaceProfileInlineDesc")
      : inlineAction === "duplicate"
        ? t("duplicateWorkspaceProfileInlineDesc")
        : t("renameWorkspaceProfileInlineDesc");
  const inlineConfirmText =
    inlineAction === "rename"
      ? t("renameWorkspaceProfile")
      : inlineAction === "duplicate"
        ? t("duplicateWorkspaceProfile")
        : t("createWorkspaceProfile");
  const inlineConfirmDisabled = busy || draftName.trim().length === 0;
  const confirmDisabled = busy;

  return (
    <>
      <div className="relative">
        <button
          ref={triggerRef}
          type="button"
          onClick={() => setOpen((next) => !next)}
          className={`control-touch w-[152px] sm:w-auto sm:min-w-[176px] max-w-[260px] rounded-lg border px-2.5 flex items-center gap-2 text-left text-[12px] transition-colors ${
            open
              ? "border-[var(--accent-border)] bg-[var(--accent-bg)] text-primary"
              : "border-default text-secondary hover:text-primary hover:bg-[var(--bg-hover)]"
          }`}
          aria-label={t("workspaceProfile")}
          aria-expanded={open}
          aria-haspopup="dialog"
          title={selected?.path}
        >
          <span className="w-7 h-7 rounded-md bg-[var(--bg-card)] border border-default flex items-center justify-center shrink-0">
            <FileCode2 className="w-3.5 h-3.5 text-tertiary" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-[10px] leading-3 font-semibold uppercase tracking-wide text-tertiary">
              {t("workspaceProfileShort")}
            </span>
            <span className="block truncate text-[12px] leading-4 font-semibold text-primary">
              {displayLabel(selected, t) || t("defaultWorkspaceProfile")}
            </span>
          </span>
          <span className="hidden sm:inline-flex rounded-md bg-[var(--bg-hover)] px-1.5 py-0.5 text-[10px] font-semibold text-tertiary shrink-0">
            {countLabel}
          </span>
          <ChevronDown className={`w-3.5 h-3.5 text-tertiary transition-transform ${open ? "rotate-180" : ""}`} />
        </button>

        {open && (
          <div
            ref={menuRef}
            role="dialog"
            aria-label={t("workspaceProfiles")}
            className="absolute right-0 top-[calc(100%+8px)] z-50 w-[360px] max-w-[calc(100vw-24px)] overflow-hidden rounded-xl border border-default bg-[var(--bg-card)] shadow-xl"
          >
            <div className="px-3 py-2.5 border-b border-default">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[12px] font-semibold text-primary leading-tight">{t("workspaceProfiles")}</p>
                  <p className="mt-0.5 text-[11px] text-tertiary truncate" title={selected?.path}>
                    {selected ? compactPathTail(selected.path) : t("noConfigSelected")}
                  </p>
                </div>
                <span className="rounded-md bg-[var(--bg-hover)] px-1.5 py-0.5 text-[10px] font-semibold text-tertiary shrink-0">
                  {countLabel}
                </span>
              </div>
            </div>

            <div className="p-2">
              <p className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wide text-tertiary">
                {t("workspaceProfilesChoose")}
              </p>
              <div className="max-h-[240px] overflow-y-auto pr-1 space-y-1" role="listbox" aria-label={t("workspaceProfilesChoose")}>
                {configs.map((config) => {
                  const isSelected = selected?.path === config.path;
                  return (
                    <button
                      key={config.path}
                      type="button"
                      role="option"
                      aria-selected={isSelected}
                      disabled={!config.exists}
                      onClick={() => selectConfig(config)}
                      className={`w-full min-h-12 rounded-lg px-2.5 py-2 flex items-center gap-2 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-55 ${
                        isSelected
                          ? "bg-[var(--accent-bg)] text-primary"
                          : "text-secondary hover:bg-[var(--bg-hover)] hover:text-primary"
                      }`}
                      title={config.path}
                    >
                      <span className={`w-8 h-8 rounded-md border flex items-center justify-center shrink-0 ${
                        isSelected
                          ? "border-[var(--accent-border)] bg-[var(--bg-card)]"
                          : "border-default bg-[var(--bg-elevated)]"
                      }`}>
                        {isSelected ? (
                          <Check className="w-4 h-4 text-[var(--accent)]" />
                        ) : (
                          <FileCode2 className="w-3.5 h-3.5 text-tertiary" />
                        )}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-1.5">
                          <span className="text-[12px] font-semibold truncate">{config.label}</span>
                          {config.is_default && (
                            <span className="rounded bg-[var(--bg-hover)] px-1.5 py-px text-[9px] font-semibold text-tertiary shrink-0">
                              {t("defaultConfig")}
                            </span>
                          )}
                        </span>
                        <span className="block mt-0.5 truncate text-[10px] text-tertiary">
                          {config.exists ? compactPathTail(config.path) : t("missing")}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="border-t border-default bg-[var(--bg-elevated)] p-2">
              <p className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wide text-tertiary">
                {t("workspaceProfilesManage")}
              </p>
              <div className="grid grid-cols-2 gap-1.5">
                <button
                  type="button"
                  onClick={() => openInlineAction("create")}
                  disabled={!canManage || !onCreate || busy}
                  className={`control-touch rounded-lg border px-2 flex items-center justify-center gap-1.5 text-[12px] font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                    inlineAction === "create"
                      ? "border-[var(--accent-border)] bg-[var(--accent-bg)] text-primary"
                      : "border-default bg-[var(--bg-card)] text-secondary hover:text-primary hover:border-[var(--accent-border)]"
                  }`}
                >
                  <Plus className="w-3.5 h-3.5" />
                  {t("newWorkspaceProfile")}
                </button>
                <button
                  type="button"
                  onClick={() => openInlineAction("duplicate")}
                  disabled={!canManage || !onCreate || !selected?.exists || busy}
                  className={`control-touch rounded-lg border px-2 flex items-center justify-center gap-1.5 text-[12px] font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                    inlineAction === "duplicate"
                      ? "border-[var(--accent-border)] bg-[var(--accent-bg)] text-primary"
                      : "border-default bg-[var(--bg-card)] text-secondary hover:text-primary hover:border-[var(--accent-border)]"
                  }`}
                >
                  <CopyPlus className="w-3.5 h-3.5" />
                  {t("duplicateWorkspaceProfile")}
                </button>
                <button
                  type="button"
                  onClick={() => openInlineAction("rename")}
                  disabled={!canModifySelected || !onRename || busy}
                  className={`control-touch rounded-lg border px-2 flex items-center justify-center gap-1.5 text-[12px] font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                    inlineAction === "rename"
                      ? "border-[var(--accent-border)] bg-[var(--accent-bg)] text-primary"
                      : "border-default bg-[var(--bg-card)] text-secondary hover:text-primary hover:border-[var(--accent-border)]"
                  }`}
                  title={selected?.is_default ? t("defaultWorkspaceProfileLocked") : selected?.path}
                >
                  <PencilLine className="w-3.5 h-3.5" />
                  {t("renameWorkspaceProfile")}
                </button>
                <button
                  type="button"
                  onClick={openDeleteAction}
                  disabled={!canModifySelected || !onDelete || busy}
                  className="control-touch rounded-lg border border-default bg-[var(--bg-card)] px-2 flex items-center justify-center gap-1.5 text-[12px] font-semibold text-secondary hover:text-danger hover:border-[var(--danger)]/40 hover:danger-bg disabled:opacity-50 disabled:cursor-not-allowed"
                  title={selected?.is_default ? t("defaultWorkspaceProfileLocked") : selected?.path}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  {t("deleteWorkspaceProfile")}
                </button>
              </div>

              {inlineAction && (
                <div className="mt-2 rounded-lg border border-[var(--accent-border)] bg-[var(--bg-card)] p-2.5 shadow-sm">
                  <div className="flex items-start gap-2">
                    <span className="mt-0.5 w-7 h-7 rounded-md bg-[var(--accent-bg)] border border-[var(--accent-border)] flex items-center justify-center shrink-0">
                      {inlineAction === "rename" ? (
                        <PencilLine className="w-3.5 h-3.5 text-[var(--accent)]" />
                      ) : inlineAction === "duplicate" ? (
                        <CopyPlus className="w-3.5 h-3.5 text-[var(--accent)]" />
                      ) : (
                        <Plus className="w-3.5 h-3.5 text-[var(--accent)]" />
                      )}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-[12px] font-semibold text-primary leading-tight">{inlineTitle}</p>
                      <p className="mt-0.5 text-[10px] text-tertiary leading-snug">{inlineDescription}</p>
                    </div>
                  </div>

                  <div className="mt-2 flex items-center gap-1.5">
                    <input
                      ref={inlineInputRef}
                      value={draftName}
                      onChange={(event) => setDraftName(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && !inlineConfirmDisabled) {
                          void confirmInlineAction();
                        }
                        if (event.key === "Escape") {
                          setInlineAction(null);
                          setDraftName("");
                        }
                      }}
                      aria-label={t("workspaceProfileName")}
                      placeholder={t("workspaceProfileNamePlaceholder")}
                      className="min-w-0 flex-1 h-8 rounded-md border border-default bg-[var(--bg-card)] px-2.5 text-[12px] text-primary placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-[var(--accent-border)]"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        setInlineAction(null);
                        setDraftName("");
                      }}
                      className="h-8 px-2 rounded-md text-[12px] font-medium text-tertiary hover:text-primary hover:bg-[var(--bg-hover)] transition-colors"
                    >
                      {t("cancel")}
                    </button>
                    <button
                      type="button"
                      onClick={() => void confirmInlineAction()}
                      disabled={inlineConfirmDisabled}
                      className="h-8 px-2.5 rounded-md bg-[var(--accent)] text-[var(--text-on-accent)] text-[12px] font-semibold hover:bg-[var(--accent-light)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {busy ? t("loading") : inlineConfirmText}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <Modal
        isOpen={pendingAction !== null}
        onClose={() => !busy && setPendingAction(null)}
        title={modalTitle}
        description={
          t("deleteWorkspaceProfileDesc", { name: selected?.label || "" })
        }
        icon={
          pendingAction === "delete"
            ? <Trash2 className="w-5 h-5 text-[var(--danger)]" />
            : <FileCode2 className="w-5 h-5 text-[var(--accent)]" />
        }
        confirmText={busy ? t("loading") : t("confirm")}
        confirmDisabled={confirmDisabled}
        onConfirm={confirmDeleteAction}
        variant={pendingAction === "delete" ? "danger" : "default"}
      >
      </Modal>
    </>
  );
}
