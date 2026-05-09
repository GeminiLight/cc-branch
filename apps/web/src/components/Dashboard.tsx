import { useState, useCallback, useRef, memo, useEffect } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  CircleStop,
  Clipboard,
  Copy,
  FolderGit2,
  Monitor,
  OctagonAlert,
  Play,
  RefreshCw,
  RotateCcw,
  ExternalLink,
  SquareTerminal,
  Wand2,
} from "lucide-react";
import type { OpenIntent, OpenerInfo, SlotInfo, SyncStatus, WorkspaceAction } from "../types";
// Dashboard uses hooks only; api prop kept for SetupGuide compatibility
import { useI18n } from "../i18n";
import { useToast } from "./ui/Toast";
import EmptyState from "./ui/EmptyState";
import { useWorkspace, useWorkspaceAction, useRelativeTime, useOpeners } from "../hooks";
import Modal from "./ui/Modal";
import SetupGuide from "./SetupGuide";
import Skeleton from "./ui/Skeleton";
import Dropdown from "./ui/Dropdown";

interface DashboardProps {
  api?: unknown;
  projectPath?: string;
  isActive?: boolean;
}

type PendingAction = {
  action: WorkspaceAction;
  target?: string;
  label: string;
  danger?: boolean;
  description?: string;
  confirmText?: string;
  stopRemoved?: boolean;
} | null;

const DEFAULT_OPENER: OpenerInfo = {
  id: "auto-terminal",
  label: "System Terminal",
  kind: "terminal",
  available: true,
  capabilities: ["run_command", "dashboard", "attach_target"],
  source: "builtin",
};

function openerStorageKey(projectPath?: string): string {
  return `cc-branch.open.tool.${projectPath || "current"}`;
}

function openerSupports(opener: OpenerInfo | undefined, capability: string): boolean {
  return Boolean(opener?.available && opener.capabilities.includes(capability));
}

function canOpenWorkspace(opener: OpenerInfo | undefined): boolean {
  return Boolean(
    openerSupports(opener, "dashboard") ||
    openerSupports(opener, "layout") ||
    openerSupports(opener, "workspace_file")
  );
}

function canOfferWorkspaceOpen(opener: OpenerInfo | undefined): boolean {
  return Boolean(
    opener?.capabilities.includes("dashboard") ||
    opener?.capabilities.includes("layout") ||
    opener?.capabilities.includes("workspace_file")
  );
}

function workspaceOpenLabel(t: (key: string, vars?: Record<string, string | number>) => string, opener: OpenerInfo): string {
  return t("openWorkspaceIn", { app: opener.label });
}

function StatusBadge({ status }: { status: SlotInfo["status"] }) {
  const isRunning = status === "running";
  const isExternal = status === "external";
  const { t } = useI18n();
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-semibold ${
        isRunning
          ? "success-bg success"
          : isExternal
            ? "accent-bg accent"
          : "text-tertiary bg-[var(--border-subtle)]"
      }`}
      title={isExternal ? t("externalTerminal") : undefined}
    >
      {isRunning ? (
        <Activity className="w-3 h-3" />
      ) : isExternal ? (
        <Monitor className="w-3 h-3" />
      ) : (
        <CircleStop className="w-3 h-3" />
      )}
      {isRunning ? t("running") : isExternal ? t("external") : t("stopped")}
    </span>
  );
}

function SyncBadge({ status }: { status?: SyncStatus }) {
  const { t } = useI18n();
  if (!status || status === "current" || status === "external") return null;
  const isActionable = status === "changed" || status === "missing" || status === "untracked";
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold ${
        isActionable
          ? "bg-[var(--warning-bg)] text-[var(--warning)]"
          : "bg-[var(--bg-hover)] text-tertiary"
      }`}
      title={t(`syncStatus_${status}`)}
    >
      {isActionable && <AlertTriangle className="w-3 h-3" />}
      {t(`syncStatus_${status}`)}
    </span>
  );
}

const SlotCard = memo(function SlotCard({
  slot,
  onRunAction,
  onConfirmAction,
  onCopy,
  busy,
  openerId,
  tmuxRuntimeUnavailable,
}: {
  slot: SlotInfo;
  onRunAction: (action: WorkspaceAction, target: string, opener?: string, intent?: OpenIntent) => void;
  onConfirmAction: (action: WorkspaceAction, target: string | undefined, label: string) => void;
  onCopy: (value: string, label: string) => void;
  busy: boolean;
  openerId: string;
  tmuxRuntimeUnavailable: boolean;
}) {
  const isRunning = slot.status === "running";
  const { t } = useI18n();
  const slotTarget = slot.name;
  const slotRuntimeUnavailable = slot.runtime === "tmux" && tmuxRuntimeUnavailable;

  return (
    <div
      className={`surface-card border rounded-lg overflow-hidden transition-all duration-200 ease-out hover:shadow-md hover:border-[var(--border-strong)] ${
        isRunning ? "border-[var(--accent-border)] shadow-sm" : "border-default"
      }`}
    >
      {/* Header */}
      <div
        className={`px-4 py-3 border-b border-default flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
          isRunning ? "accent-bg" : "surface-elevated"
        }`}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={`w-9 h-9 rounded-md border flex items-center justify-center shrink-0 ${
              isRunning
                ? "bg-[var(--bg-card)] border-[var(--accent-border)]"
                : "bg-[var(--bg-card)] border-default"
            }`}
          >
            <Monitor
              className={`w-4 h-4 shrink-0 ${
                isRunning ? "text-[var(--accent)]" : "text-tertiary"
              }`}
            />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-[14px] font-semibold text-primary leading-tight truncate">
                {slot.name}
              </h3>
              <StatusBadge status={slot.status} />
              <SyncBadge status={slot.sync_status} />
            </div>
            <p className="text-[11px] text-tertiary font-mono mt-0.5 truncate">
              {slot.session_name}
              <span className="text-muted mx-1">·</span>
              <span className="text-muted">{slot.runtime}</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {isRunning ? (
            <>
              <button
                type="button"
                onClick={() => onRunAction("open", slotTarget, openerId, "attach_target")}
                disabled={busy || slotRuntimeUnavailable}
                className="control-touch px-3 rounded-md text-[12px] font-semibold bg-[var(--accent)] text-[var(--text-on-accent)] hover:bg-[var(--accent-light)] transition-colors flex items-center gap-1.5 disabled:opacity-50 shadow-sm"
                aria-label={`${t("openTerminal")} ${slotTarget}`}
                title={slotRuntimeUnavailable ? t("tmuxRuntimeUnavailable") : undefined}
              >
                <ExternalLink className="w-3.5 h-3.5" />
                {t("open")}
              </button>
              <div className="flex items-center gap-1 p-0.5 rounded-md border border-default surface-card">
                <button
                  type="button"
                  onClick={() => onRunAction("restart", slotTarget, openerId)}
                  disabled={busy || slotRuntimeUnavailable}
                  className="icon-touch sm:min-h-9 sm:min-w-9 rounded text-[11px] font-medium text-secondary hover:text-primary hover:surface-hover transition-colors flex items-center justify-center disabled:opacity-50"
                  aria-label={`${t("restart")} ${slotTarget}`}
                  title={slotRuntimeUnavailable ? t("tmuxRuntimeUnavailable") : t("restart")}
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => onConfirmAction("stop", slotTarget, slotTarget)}
                  disabled={busy || slotRuntimeUnavailable}
                  className="icon-touch sm:min-h-9 sm:min-w-9 rounded text-[11px] font-medium danger hover:danger-bg transition-colors flex items-center justify-center disabled:opacity-50"
                  aria-label={`${t("stop")} ${slotTarget}`}
                  title={slotRuntimeUnavailable ? t("tmuxRuntimeUnavailable") : t("stop")}
                >
                  <CircleStop className="w-4 h-4" />
                </button>
              </div>
            </>
          ) : (
            <button
              type="button"
              onClick={() => onRunAction("open", slotTarget, openerId, "attach_target")}
              disabled={busy || slotRuntimeUnavailable}
              className="control-touch px-3 rounded-md text-[12px] font-semibold bg-[var(--accent)] text-[var(--text-on-accent)] hover:bg-[var(--accent-light)] transition-colors flex items-center gap-1.5 disabled:opacity-50 shadow-sm"
              aria-label={`${t("openTerminal")} ${slotTarget}`}
              title={slotRuntimeUnavailable ? t("tmuxRuntimeUnavailable") : undefined}
            >
              <ExternalLink className="w-3.5 h-3.5" />
              {t("open")}
            </button>
          )}
          <button
            type="button"
            onClick={() => onCopy(slotTarget, `${slotTarget} target`)}
            className="icon-touch sm:min-h-9 sm:min-w-9 rounded-md text-tertiary hover:text-primary hover:surface-hover transition-colors flex items-center justify-center"
            aria-label={`${t("copyTarget")} ${slotTarget}`}
            title={t("copyTarget")}
          >
            <Clipboard className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Windows */}
      <div className="p-1.5 space-y-1">
        {slot.windows.map((w) => {
          const windowTarget = `${slot.name}:${w.name}`;
          return (
          <div
            key={w.name}
            className="group rounded-md border border-transparent px-2.5 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 hover:bg-[var(--accent-bg)] hover:border-[var(--accent-border)] focus-within:bg-[var(--accent-bg)] focus-within:border-[var(--accent-border)] transition-[background-color,border-color,box-shadow] duration-150"
            role="listitem"
          >
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="w-8 h-8 rounded-md border border-default bg-[var(--bg-elevated)] text-tertiary flex items-center justify-center shrink-0 group-hover:bg-[var(--bg-card)] group-hover:border-[var(--accent-border)] group-hover:text-[var(--accent)] group-hover:shadow-sm group-focus-within:bg-[var(--bg-card)] group-focus-within:border-[var(--accent-border)] group-focus-within:text-[var(--accent)] transition-[background-color,border-color,color,box-shadow] duration-150">
                <SquareTerminal className="w-4 h-4 shrink-0" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-semibold text-primary">
                    {w.name}
                  </span>
                  {w.agent && (
                    <span className="text-[10px] px-1.5 py-px rounded-md accent-bg accent font-semibold">
                      {w.agent}
                    </span>
                  )}
                  <SyncBadge status={w.sync_status} />
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  {w.label && (
                    <p className="text-[11px] text-tertiary truncate">{w.label}</p>
                  )}
                  {w.session_id && (
                    <p className="text-[10px] font-mono text-muted" title={w.session_id}>
                      {w.session_id.slice(0, 10)}…
                    </p>
                  )}
                </div>
                <div className="hidden lg:flex items-center gap-1.5 mt-1 min-w-0 text-[10px] text-tertiary font-mono">
                  <span className="truncate max-w-[360px]" title={w.command || "-"}>
                    {w.command || "-"}
                  </span>
                  <span className="text-muted">·</span>
                  <span className="truncate max-w-[360px]" title={w.cwd}>
                    {w.cwd}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0 lg:justify-end">
              <button
                type="button"
                onClick={() => onRunAction("open", windowTarget, openerId, "attach_target")}
                disabled={busy || slotRuntimeUnavailable}
                className="control-touch min-w-11 sm:min-w-0 px-3 rounded-md text-[12px] font-medium text-secondary hover:text-primary surface-card border border-default transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
                aria-label={`${t("openTerminal")} ${windowTarget}`}
                title={slotRuntimeUnavailable ? t("tmuxRuntimeUnavailable") : `${t("openTerminal")} ${windowTarget}`}
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{t("open")}</span>
              </button>
              <button
                type="button"
                onClick={() => onCopy(`cc-branch attach ${windowTarget}`, `attach command for ${windowTarget}`)}
                className="icon-touch sm:min-h-9 sm:min-w-9 rounded-md text-tertiary hover:text-primary hover:surface-hover transition-colors flex items-center justify-center"
                aria-label={`${t("copyAttachCommand")} ${windowTarget}`}
                title={t("copyAttachCommand")}
              >
                <Copy className="w-4 h-4" />
              </button>
            </div>
          </div>
          );
        })}
      </div>
    </div>
  );
});

function DashboardLoading() {
  return (
    <div className="page-shell space-y-3 pt-1" aria-label="Loading workspace">
      <div className="surface-command border border-default rounded-lg px-4 sm:px-5 py-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <Skeleton width={36} height={36} />
            <div className="space-y-2 min-w-0 flex-1">
              <Skeleton width={180} height={14} />
              <Skeleton width={280} height={10} className="max-w-full" />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Skeleton width={138} height={36} />
            <Skeleton width={96} height={36} />
            <Skeleton width={112} height={36} />
          </div>
        </div>
      </div>

      <div className="surface-card border border-default rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-default flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Skeleton width={34} height={34} />
            <div className="space-y-2">
              <Skeleton width={150} height={13} />
              <Skeleton width={220} height={10} />
            </div>
          </div>
          <Skeleton width={120} height={34} />
        </div>
        <div className="divide-y divide-[var(--border-subtle)]">
          {[0, 1, 2].map((row) => (
            <div key={row} className="px-4 py-3 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <Skeleton width={30} height={30} />
                <div className="space-y-2 min-w-0 flex-1">
                  <Skeleton width={row === 1 ? "48%" : "36%"} height={12} />
                  <Skeleton width={row === 2 ? "62%" : "74%"} height={9} />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Skeleton width={64} height={32} />
                <Skeleton width={32} height={32} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Dashboard({ projectPath, isActive = true }: DashboardProps) {
  const { t } = useI18n();
  const toast = useToast();
  const { data, error, isLoading, isError, refetch, isFetching } =
    useWorkspace(projectPath, isActive);
  const { data: openersData } = useOpeners(projectPath, isActive);
  const actionMutation = useWorkspaceAction();

  const [modalOpen, setModalOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [lastActionMessage, setLastActionMessage] = useState<string | null>(null);
  const [selectedOpenerId, setSelectedOpenerId] = useState<string>(() => {
    if (typeof window === "undefined") return "auto-terminal";
    return window.localStorage.getItem(openerStorageKey(projectPath)) || "auto-terminal";
  });
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, []);

  const requestConfirmedAction = useCallback((
    action: WorkspaceAction,
    target: string | undefined,
    label: string,
    options: Pick<NonNullable<PendingAction>, "description" | "confirmText" | "stopRemoved" | "danger"> = {},
  ) => {
    setPendingAction({ action, target, label, danger: action === "stop", ...options });
    setModalOpen(true);
  }, []);

  const runAction = useCallback(async (
    action: WorkspaceAction,
    target: string | undefined,
    opener?: string,
    intent?: OpenIntent,
    stopRemoved?: boolean,
  ) => {
    if (!projectPath) return;
    try {
      const result = await actionMutation.mutateAsync({
        action,
        target,
        opener,
        intent,
        projectPath,
        stopRemoved,
      });
      toast.success(result.message);
      setLastActionMessage(result.message);
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = setTimeout(() => refetch(), 500);
    } catch (e: unknown) {
      toast.error(String(e));
    }
  }, [projectPath, actionMutation, toast, refetch]);

  const confirmAction = useCallback(async () => {
    if (!pendingAction) return;
    await runAction(pendingAction.action, pendingAction.target, undefined, undefined, pendingAction.stopRemoved);
    setPendingAction(null);
    setModalOpen(false);
  }, [pendingAction, runAction]);

  const copyToClipboard = useCallback(async (value: string, label: string) => {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = value;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    toast.success(`${t("copied")} ${label}`);
  }, [toast, t]);

  const [updateTime, setUpdateTime] = useState<number | null>(null);
  const lastUpdated = useRelativeTime(updateTime);
  const prevDataRef = useRef(data);

  useEffect(() => {
    if (data && data !== prevDataRef.current) {
      prevDataRef.current = data;
      setUpdateTime(Date.now());
    }
  }, [data]);

  if (isLoading) {
    return <DashboardLoading />;
  }

  if (isError) {
    const errMsg = String(error);
    const isNoConfig =
      errMsg.includes("No such file") ||
      errMsg.includes("does not exist");
    if (isNoConfig) return <SetupGuide projectPath={projectPath} onRefresh={refetch} />;
    return (
      <div className="max-w-sm mx-auto text-center py-20">
        <div className="w-10 h-10 rounded-lg danger-bg flex items-center justify-center mx-auto mb-3">
          <OctagonAlert className="w-5 h-5 danger" />
        </div>
        <h3 className="text-sm font-semibold text-primary mb-1">
          {t("errorLoading")}
        </h3>
        <p className="text-[13px] text-secondary mb-4">{errMsg}</p>
        <button
          type="button"
          onClick={() => refetch()}
          className="inline-flex items-center gap-1.5 h-8 px-3 rounded-md text-[13px] font-medium bg-[var(--accent)] text-[var(--text-on-accent)] hover:opacity-90 transition-opacity"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          {t("refresh")}
        </button>
      </div>
    );
  }

  if (data?.status === "needs_init") {
    return <SetupGuide projectPath={projectPath} onRefresh={refetch} />;
  }

  if (data?.status === "missing" || data?.status === "invalid_config") {
    const message = data.error || (data.status === "missing" ? t("pathNotFound") : t("errorLoading"));
    return (
      <div className="max-w-sm mx-auto text-center py-20">
        <div className="w-10 h-10 rounded-lg danger-bg flex items-center justify-center mx-auto mb-3">
          <OctagonAlert className="w-5 h-5 danger" />
        </div>
        <h3 className="text-sm font-semibold text-primary mb-1">
          {t("errorLoading")}
        </h3>
        <p className="text-[13px] text-secondary mb-4">{message}</p>
        <button
          type="button"
          onClick={() => refetch()}
          className="inline-flex items-center gap-1.5 h-8 px-3 rounded-md text-[13px] font-medium bg-[var(--accent)] text-[var(--text-on-accent)] hover:opacity-90 transition-opacity"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          {t("refresh")}
        </button>
      </div>
    );
  }

  if (!data || data.slots.length === 0) {
    return (
      <EmptyState
        icon={<Activity className="w-6 h-6" />}
        title={t("noSlots")}
        description={t("noSlotsHint")}
        action={
          <p className="text-[12px] text-tertiary mt-2">
            {t("configureInConfigTab")}
          </p>
        }
      />
    );
  }

  const runningCount = data.slots.filter((s) => s.status === "running").length;
  const stoppedCount = data.slots.filter((s) => s.status === "stopped").length;
  const externalCount = data.slots.filter((s) => s.status === "external").length;
  const hasTmuxSlots = data.slots.some((s) => s.runtime === "tmux");
  const tmuxRuntimeUnavailable = hasTmuxSlots && data.runtimes?.tmux?.available === false;
  const canManageTmuxSlots = hasTmuxSlots && !tmuxRuntimeUnavailable;
  const syncSummary = data.runtime_sync?.summary;
  const changedCount = syncSummary?.changed || 0;
  const missingCount = syncSummary?.missing || 0;
  const untrackedCount = syncSummary?.untracked || 0;
  const extraCount = syncSummary?.extra || 0;
  const syncCount = changedCount + missingCount + untrackedCount;
  const runtimeSyncNotices = [
    tmuxRuntimeUnavailable ? t("tmuxRuntimeUnavailable") : null,
    changedCount > 0 ? t("runtimeChangedPending", { count: changedCount }) : null,
    missingCount > 0 ? t("runtimeMissingPending", { count: missingCount }) : null,
    untrackedCount > 0 ? t("runtimeUntracked", { count: untrackedCount }) : null,
    extraCount > 0 ? t("runtimeExtraWindows", { count: extraCount }) : null,
  ].filter((notice): notice is string => Boolean(notice));
  const openers = openersData?.openers?.length ? openersData.openers : [DEFAULT_OPENER];
  const defaultOpenerId = openersData?.default || "auto-terminal";
  const availableOpeners = openers.filter((opener) => opener.available);
  const workspaceOpeners = openers.filter(canOfferWorkspaceOpen);
  const availableWorkspaceOpeners = workspaceOpeners.filter((opener) => opener.available);
  const selectedOpener = availableWorkspaceOpeners.find((opener) => opener.id === selectedOpenerId)
    || availableWorkspaceOpeners.find((opener) => opener.id === defaultOpenerId)
    || availableWorkspaceOpeners[0]
    || DEFAULT_OPENER;
  const projectDirectoryOpener = availableOpeners.find((opener) => opener.id === "system-file-manager")
    || selectedOpener;
  const openerItems = workspaceOpeners.map((opener) => ({
    label: opener.label,
    value: opener.id,
    disabled: !opener.available,
    description: opener.reason,
  }));

  const setDefaultOpener = (value: string) => {
    setSelectedOpenerId(value);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(openerStorageKey(projectPath), value);
    }
  };

  const runWorkspaceOpen = () => {
    runAction("open", undefined, selectedOpener.id, "workspace_dashboard");
  };

  const runProjectOpen = () => {
    if (!openerSupports(projectDirectoryOpener, "open_project")) return;
    runAction("open", undefined, projectDirectoryOpener.id, "project_folder");
  };

  return (
    <div className="page-shell space-y-4">
      {/* Project summary */}
      <div className="surface-command border border-default rounded-lg px-4 sm:px-5 py-4 flex flex-col gap-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-md bg-[var(--accent-bg)] border border-[var(--accent-border)] flex items-center justify-center shrink-0">
              <FolderGit2 className="w-4 h-4 text-[var(--accent)]" />
            </div>
            <div className="min-w-0">
              <p className="text-[16px] font-semibold text-primary leading-tight truncate">
                {data.project || data.project_name}
              </p>
              <p className="text-[12px] text-tertiary mt-0.5">
                {runningCount} {t("running")} · {stoppedCount} {t("stopped")}
                {externalCount > 0 ? ` · ${externalCount} ${t("external")}` : ""}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[12px] text-tertiary shrink-0 rounded-full bg-[var(--bg-card)]/70 px-3 py-1.5">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isFetching ? "bg-[var(--accent)] animate-pulse" : "bg-[var(--success)]"
              }`}
            />
            {isFetching ? t("refreshing") : t("connected")}
            <span className="text-muted">·</span>
            <span>{lastUpdated || "--"}</span>
          </div>
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_auto] items-start xl:items-center gap-3">
          {/* Primary actions */}
          <div className="grid grid-cols-1 sm:flex sm:flex-wrap items-center gap-2 min-w-0 max-w-full">
            <div className="inline-flex max-w-full rounded-md shadow-sm">
              <button
                type="button"
                onClick={runWorkspaceOpen}
                disabled={actionMutation.isPending || !canOpenWorkspace(selectedOpener)}
                className="control-touch min-w-0 px-4 rounded-l-md rounded-r-none text-[13px] font-semibold bg-[var(--accent)] text-[var(--text-on-accent)] hover:bg-[var(--accent-light)] transition-colors flex items-center justify-center sm:justify-start gap-2 disabled:opacity-50"
                title={!canOpenWorkspace(selectedOpener) ? t("toolCannotOpenWorkspace", { app: selectedOpener.label }) : workspaceOpenLabel(t, selectedOpener)}
                aria-label={workspaceOpenLabel(t, selectedOpener)}
              >
                {actionMutation.isPending ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <ExternalLink className="w-4 h-4 shrink-0" />
                )}
                <span className="truncate">{t("openWorkspace")}</span>
              </button>
              <Dropdown
                align="left"
                value={selectedOpener.id}
                items={openerItems}
                onChange={setDefaultOpener}
                ariaLabel={t("selectedTool", { app: selectedOpener.label })}
                trigger={
                  <span className="control-touch w-[176px] min-w-0 px-3 rounded-r-md rounded-l-none border-l border-white/20 bg-[var(--accent)] text-[var(--text-on-accent)] hover:bg-[var(--accent-light)] transition-colors flex items-center gap-1.5">
                    <span className="truncate text-[13px] font-semibold">{selectedOpener.label}</span>
                    <ChevronDown className="w-3 h-3 shrink-0 opacity-80" />
                  </span>
                }
              />
            </div>
            <button
              type="button"
              onClick={runProjectOpen}
              disabled={actionMutation.isPending || !openerSupports(projectDirectoryOpener, "open_project")}
              title={openerSupports(projectDirectoryOpener, "open_project") ? t("openProjectDirectory") : t("toolCannotOpenProject", { app: projectDirectoryOpener.label })}
              aria-label={t("openProjectDirectory")}
              className="control-touch px-4 rounded-md text-[13px] font-medium text-secondary hover:text-primary surface-card border border-default hover:border-[var(--border-strong)] transition-all flex items-center justify-center sm:justify-start gap-2 disabled:opacity-45 disabled:cursor-not-allowed"
            >
              {actionMutation.isPending ? (
                <div className="w-3.5 h-3.5 border-2 border-current/30 border-t-current rounded-full animate-spin" />
              ) : (
                <FolderGit2 className="w-3.5 h-3.5 shrink-0" />
              )}
              <span className="truncate">{t("openProjectDirectory")}</span>
            </button>
            {syncCount > 0 && (
              <button
                type="button"
                onClick={() => requestConfirmedAction("sync", undefined, t("runtimeChanges"))}
                disabled={actionMutation.isPending || !canManageTmuxSlots}
                className="control-touch px-4 rounded-md text-[13px] font-semibold bg-[var(--warning-bg)] text-[var(--warning)] hover:border-[var(--warning)]/30 border border-transparent transition-colors flex items-center justify-center sm:justify-start gap-2 disabled:opacity-50 shadow-sm max-w-full"
                title={t("syncChangesHint", { count: syncCount })}
                aria-label={t("syncChanges")}
              >
                <Wand2 className="w-4 h-4 shrink-0" />
                <span className="truncate">{t("syncChanges")}</span>
                <span className="rounded-md bg-[var(--bg-card)] px-1.5 py-0.5 text-[10px] font-bold">
                  {syncCount}
                </span>
              </button>
            )}
            {extraCount > 0 && (
              <button
                type="button"
                onClick={() => requestConfirmedAction("sync", undefined, t("extraWindows"), {
                  danger: true,
                  stopRemoved: true,
                  description: t("stopExtraConfirmDescription", { count: extraCount }),
                  confirmText: t("stopExtra"),
                })}
                disabled={actionMutation.isPending || !canManageTmuxSlots}
                className="control-touch px-4 rounded-md text-[13px] font-semibold danger hover:danger-bg border border-transparent transition-colors flex items-center justify-center sm:justify-start gap-2 disabled:opacity-50 max-w-full"
                title={t("stopExtraWindowsHint", { count: extraCount })}
                aria-label={t("stopExtraWindows")}
              >
                <CircleStop className="w-4 h-4 shrink-0" />
                <span className="truncate">{t("stopExtraWindows")}</span>
                <span className="rounded-md bg-[var(--bg-card)] px-1.5 py-0.5 text-[10px] font-bold">
                  {extraCount}
                </span>
              </button>
            )}
          </div>
          {/* Secondary actions */}
          <div className="flex flex-wrap items-center gap-2 justify-self-stretch xl:justify-self-end xl:justify-items-end">
            <div className="flex items-center gap-1 p-1 rounded-md bg-[var(--bg-card)]/80 shadow-sm">
              <button
                type="button"
                onClick={() => runAction("launch", undefined)}
                disabled={actionMutation.isPending || !canManageTmuxSlots}
                className="icon-touch rounded text-secondary hover:text-primary hover:surface-hover transition-colors flex items-center justify-center disabled:opacity-50"
                title={tmuxRuntimeUnavailable ? t("tmuxRuntimeUnavailable") : hasTmuxSlots ? t("startOnly") : t("tmuxOnlyAction")}
                aria-label={t("startOnly")}
              >
                <Play className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => runAction("restart", undefined)}
                disabled={actionMutation.isPending || !canManageTmuxSlots}
                className="icon-touch rounded text-secondary hover:text-primary hover:surface-hover transition-colors flex items-center justify-center disabled:opacity-50"
                title={tmuxRuntimeUnavailable ? t("tmuxRuntimeUnavailable") : hasTmuxSlots ? t("restart") : t("tmuxOnlyAction")}
                aria-label={t("restart")}
              >
                <RotateCcw className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => {
                  setPendingAction({ action: "stop", label: "workspace", danger: true });
                  setModalOpen(true);
                }}
                disabled={actionMutation.isPending || runningCount === 0}
                className="icon-touch rounded danger hover:danger-bg transition-colors flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed"
                title={t("stopWorkspace")}
                aria-label={t("stopWorkspace")}
              >
                <CircleStop className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => refetch()}
                disabled={isFetching}
                className="icon-touch rounded text-secondary hover:text-primary hover:surface-hover transition-colors flex items-center justify-center disabled:opacity-50"
                title={t("refresh")}
                aria-label={t("refresh")}
              >
                <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
              </button>
            </div>
          </div>
        </div>
        {lastActionMessage && (
          <div className="flex items-center gap-2 rounded-md border border-[var(--success)]/10 success-bg px-2.5 py-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-[var(--success)] shrink-0" />
            <p className="text-[11px] font-medium text-secondary">{lastActionMessage}</p>
          </div>
        )}
        {runtimeSyncNotices.length > 0 && (
          <div className="flex items-start gap-2 rounded-md border border-[var(--warning)]/10 bg-[var(--warning-bg)] px-2.5 py-2">
            <AlertTriangle className="w-3.5 h-3.5 text-[var(--warning)] shrink-0 mt-0.5" />
            <ul className="space-y-0.5 text-[11px] font-medium text-secondary leading-relaxed">
              {runtimeSyncNotices.map((notice) => (
                <li key={notice}>{notice}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Slot cards */}
      {data.slots.map((slot, i) => (
        <div key={slot.name} className="animate-stagger" style={{ animationDelay: `${i * 60}ms`, opacity: 0 }}>
          <SlotCard
            slot={slot}
            onRunAction={runAction}
            onConfirmAction={requestConfirmedAction}
            onCopy={copyToClipboard}
            busy={actionMutation.isPending}
            openerId={selectedOpener.id}
            tmuxRuntimeUnavailable={tmuxRuntimeUnavailable}
          />
        </div>
      ))}

      {/* Stop Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setPendingAction(null);
        }}
        title={pendingAction?.confirmText || (pendingAction?.action === "stop" ? t("stop") : pendingAction?.action === "sync" ? t("syncChanges") : t("confirm"))}
        description={
          pendingAction?.description || (pendingAction?.action === "sync"
            ? t("syncConfirmDescription", { count: syncCount })
            : t("confirmAction", { action: pendingAction?.action || "", name: pendingAction?.label || "" }))
        }
        icon={
          pendingAction?.action === "sync" ? (
            <Wand2 className="w-5 h-5 text-[var(--warning)]" />
          ) : (
            <AlertTriangle className="w-5 h-5 danger" />
          )
        }
        confirmText={pendingAction?.confirmText || (pendingAction?.action === "stop" ? t("stop") : pendingAction?.action === "sync" ? t("syncChanges") : t("confirm"))}
        cancelText={t("cancel")}
        onConfirm={confirmAction}
        variant={pendingAction?.danger ? "danger" : "default"}
      />
    </div>
  );
}
