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
} from "lucide-react";
import type { OpenIntent, OpenerInfo, SlotInfo, WorkspaceAction } from "../types";
// Dashboard uses hooks only; api prop kept for SetupGuide compatibility
import { useI18n } from "../i18n";
import { useToast } from "./ui/Toast";
import { useWorkspace, useWorkspaceAction, useRelativeTime, useOpeners } from "../hooks";
import Modal from "./ui/Modal";
import SetupGuide from "./SetupGuide";
import { SkeletonCard } from "./ui/Skeleton";
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
  return `cc-branch.open.default.${projectPath || "current"}`;
}

function openerSupports(opener: OpenerInfo | undefined, capability: string): boolean {
  return Boolean(opener?.available && opener.capabilities.includes(capability));
}

function workspaceIntent(opener: OpenerInfo): OpenIntent {
  return openerSupports(opener, "dashboard") ? "workspace_dashboard" : "project_folder";
}

function workspaceOpenLabel(t: (key: string, vars?: Record<string, string | number>) => string, opener: OpenerInfo): string {
  if (workspaceIntent(opener) === "project_folder") {
    return t("openProjectIn", { app: opener.label });
  }
  return t("openWorkspace");
}

function StatusBadge({ status }: { status: "running" | "stopped" }) {
  const isRunning = status === "running";
  const { t } = useI18n();
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-semibold ${
        isRunning
          ? "success-bg success"
          : "text-tertiary bg-[var(--border-subtle)]"
      }`}
    >
      <span
        className={`w-1 h-1 rounded-full ${
          isRunning ? "bg-[var(--success)]" : "bg-tertiary"
        }`}
      />
      {isRunning ? t("running") : t("stopped")}
    </span>
  );
}

const SlotCard = memo(function SlotCard({
  slot,
  onRunAction,
  onConfirmAction,
  onCopy,
  busy,
  attachOpenerId,
}: {
  slot: SlotInfo;
  onRunAction: (action: WorkspaceAction, target: string, opener?: string, intent?: OpenIntent) => void;
  onConfirmAction: (action: WorkspaceAction, target: string, label: string) => void;
  onCopy: (value: string, label: string) => void;
  busy: boolean;
  attachOpenerId: string;
}) {
  const isRunning = slot.status === "running";
  const { t } = useI18n();
  const slotTarget = slot.name;

  return (
    <div
      className={`surface-card border rounded-lg overflow-hidden transition-all hover:shadow-sm hover:-translate-y-px ${
        isRunning ? "border-[var(--accent-border)] shadow-sm" : "border-default"
      }`}
    >
      {/* Header */}
      <div
        className={`px-4 py-3 border-b border-default flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
          isRunning ? "accent-bg" : "surface-elevated"
        }`}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div
            className={`w-8 h-8 rounded-md border flex items-center justify-center shrink-0 ${
              isRunning
                ? "bg-[var(--bg-card)] border-[var(--accent-border)]"
                : "bg-[var(--bg-card)] border-default"
            }`}
          >
            <Monitor
              className={`w-4 h-4 shrink-0 ${
                isRunning ? "success" : "text-tertiary"
              }`}
            />
          </div>
          <div className="min-w-0">
            <h3 className="text-[14px] font-semibold text-primary leading-tight truncate">
              {slot.name}
            </h3>
            <p className="text-[10px] text-tertiary font-mono mt-px truncate">
              {slot.session_name}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0 flex-wrap self-start sm:self-auto">
          <span className="text-[10px] px-1.5 py-px rounded bg-[var(--border-subtle)] text-tertiary font-medium">
            {slot.backend}
          </span>
          <StatusBadge status={slot.status} />
          <button
            type="button"
            onClick={() => onCopy(slotTarget, `${slotTarget} target`)}
            className="h-6 w-6 rounded text-tertiary hover:text-primary hover:surface-hover transition-colors flex items-center justify-center"
            aria-label={`Copy target ${slotTarget}`}
            title="Copy target"
          >
            <Clipboard className="w-3 h-3" />
          </button>
          {isRunning ? (
            <>
              <button
                type="button"
                onClick={() => onRunAction("open", slotTarget, attachOpenerId, "attach_target")}
                disabled={busy}
                className="h-7 px-2.5 rounded-md text-[11px] font-semibold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity flex items-center gap-1 disabled:opacity-50 shadow-sm"
                aria-label={`${t("openTerminal")} ${slotTarget}`}
              >
                <ExternalLink className="w-3 h-3" />
                {t("open")}
              </button>
              <button
                type="button"
                onClick={() => onRunAction("restart", slotTarget)}
                disabled={busy}
                className="h-7 px-2.5 rounded-md text-[11px] font-medium text-secondary hover:text-primary surface-card border border-default transition-colors flex items-center gap-1 disabled:opacity-50"
                aria-label={`Restart ${slotTarget}`}
              >
                <RotateCcw className="w-3 h-3" />
                {t("restart")}
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => onRunAction("open", slotTarget, attachOpenerId, "attach_target")}
              disabled={busy}
              className="h-7 px-2.5 rounded-md text-[11px] font-semibold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity flex items-center gap-1 disabled:opacity-50 shadow-sm"
              aria-label={`${t("openTerminal")} ${slotTarget}`}
            >
              <ExternalLink className="w-3 h-3" />
              {t("open")}
            </button>
          )}
          {isRunning && (
            <button
              type="button"
              onClick={() => onConfirmAction("stop", slotTarget, slotTarget)}
              disabled={busy}
              className="h-7 px-2.5 rounded-md text-[11px] font-medium danger danger-bg hover:opacity-80 transition-opacity flex items-center gap-1"
              aria-label={`${t("stop")} ${slotTarget}`}
            >
              <CircleStop className="w-3 h-3" />
              {t("stop")}
            </button>
          )}
        </div>
      </div>

      {/* Windows */}
      <div className="divide-y divide-default">
        {slot.windows.map((w) => {
          const windowTarget = `${slot.name}:${w.name}`;
          return (
          <div
            key={w.name}
            className="group px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 hover:surface-hover transition-colors"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-7 h-7 rounded-md bg-[var(--border-subtle)] flex items-center justify-center shrink-0 group-hover:bg-[var(--bg-card)] group-hover:shadow-sm transition-all">
                <SquareTerminal className="w-3.5 h-3.5 text-tertiary shrink-0" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-semibold text-primary">
                    {w.name}
                  </span>
                  {w.agent && (
                    <span className="text-[10px] px-1.5 py-px rounded-md accent-bg accent font-semibold">
                      {w.agent}
                    </span>
                  )}
                </div>
                {w.label && (
                  <p className="text-[11px] text-tertiary truncate">{w.label}</p>
                )}
                {w.session_id && (
                  <p className="text-[10px] font-mono text-muted">
                    {w.session_id.slice(0, 14)}…
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto justify-end">
              <div className="text-right hidden sm:block">
                <p
                  className="text-[11px] font-mono text-secondary truncate max-w-[100px] md:max-w-[160px]"
                  title={w.command || "-"}
                >
                  {w.command || "-"}
                </p>
                <p
                  className="text-[10px] text-tertiary truncate max-w-[100px] md:max-w-[160px]"
                  title={w.cwd}
                >
                  {w.cwd}
                </p>
              </div>
              <button
                type="button"
                onClick={() => onRunAction("open", windowTarget, attachOpenerId, "attach_target")}
                disabled={busy}
                className="h-7 px-2.5 rounded-md text-[11px] font-medium text-secondary hover:text-primary surface-card border border-default transition-colors flex items-center gap-1 disabled:opacity-50"
                aria-label={`${t("openTerminal")} ${windowTarget}`}
                title={`${t("openTerminal")} ${windowTarget}`}
              >
                <ExternalLink className="w-3 h-3" />
                <span className="hidden sm:inline">{t("open")}</span>
              </button>
              <button
                type="button"
                onClick={() => onCopy(`cc-branch attach ${windowTarget}`, `attach command for ${windowTarget}`)}
                className="h-7 w-7 rounded-md text-tertiary hover:text-primary hover:surface-card border border-transparent hover:border-default transition-colors flex items-center justify-center"
                aria-label={`Copy attach command for ${windowTarget}`}
                title="Copy attach command"
              >
                <Copy className="w-3 h-3" />
              </button>
            </div>
          </div>
          );
        })}
      </div>
    </div>
  );
});

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

  const requestConfirmedAction = useCallback((action: WorkspaceAction, target: string, label: string) => {
    setPendingAction({ action, target, label, danger: action === "stop" });
    setModalOpen(true);
  }, []);

  const runAction = useCallback(async (
    action: WorkspaceAction,
    target: string | undefined,
    opener?: string,
    intent?: OpenIntent,
  ) => {
    if (!projectPath) return;
    try {
      const result = await actionMutation.mutateAsync({
        action,
        target,
        opener,
        intent,
        projectPath,
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
    await runAction(pendingAction.action, pendingAction.target);
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
    return (
      <div className="space-y-3 max-w-3xl animate-stagger">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
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
          className="inline-flex items-center gap-1.5 h-8 px-3 rounded-md text-[13px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
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
          className="inline-flex items-center gap-1.5 h-8 px-3 rounded-md text-[13px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          {t("refresh")}
        </button>
      </div>
    );
  }

  if (!data || data.slots.length === 0) {
    return (
      <div className="text-center py-20">
        <div className="w-10 h-10 rounded-lg bg-[var(--border-subtle)] flex items-center justify-center mx-auto mb-3">
          <Activity className="w-5 h-5 text-tertiary" />
        </div>
        <p className="text-[13px] text-secondary">{t("noSlots")}</p>
      </div>
    );
  }

  const runningCount = data.slots.filter((s) => s.status === "running").length;
  const totalCount = data.slots.length;
  const openers = openersData?.openers?.length ? openersData.openers : [DEFAULT_OPENER];
  const defaultOpenerId = openersData?.default || "auto-terminal";
  const selectedOpener = openers.find((opener) => opener.id === selectedOpenerId && opener.available)
    || openers.find((opener) => opener.id === defaultOpenerId && opener.available)
    || openers.find((opener) => opener.available)
    || DEFAULT_OPENER;
  const attachOpener = openerSupports(selectedOpener, "attach_target")
    ? selectedOpener
    : openers.find((opener) => opener.id === "auto-terminal" && opener.available)
      || openers.find((opener) => opener.available && opener.capabilities.includes("attach_target"))
      || DEFAULT_OPENER;
  const openerItems = openers.map((opener) => ({
    label: opener.label,
    value: opener.id,
    disabled: !opener.available,
    description: opener.reason,
  }));
  const selectedWorkspaceIntent = workspaceIntent(selectedOpener);

  const setDefaultOpener = (value: string) => {
    setSelectedOpenerId(value);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(openerStorageKey(projectPath), value);
    }
  };

  const runWorkspaceOpen = () => {
    runAction("open", undefined, selectedOpener.id, selectedWorkspaceIntent);
  };

  return (
    <div className="space-y-3 max-w-5xl">
      {/* Project summary */}
      <div className="surface-command border border-strong rounded-lg px-4 py-3 flex flex-col gap-3 shadow-sm relative overflow-hidden">
        <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-[var(--accent)]" />
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-md bg-[var(--accent-bg)] border border-[var(--accent-border)] flex items-center justify-center shrink-0">
              <FolderGit2 className="w-4 h-4 text-[var(--accent)]" />
            </div>
            <div>
              <p className="text-[15px] font-semibold text-primary leading-tight">
                {data.project || data.project_name}
              </p>
              <p className="text-[11px] text-tertiary">
                {runningCount} {t("running")} · {totalCount - runningCount}{" "}
                {t("stopped")}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-tertiary shrink-0">
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
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              onClick={runWorkspaceOpen}
              disabled={actionMutation.isPending}
              className="h-8 px-3 rounded-md text-[12px] font-semibold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity flex items-center gap-1.5 disabled:opacity-50 shadow-sm"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              {workspaceOpenLabel(t, selectedOpener)}
            </button>
            <Dropdown
              align="left"
              value={selectedOpener.id}
              items={openerItems}
              onChange={setDefaultOpener}
              trigger={
                <span className="h-8 px-3 rounded-md text-[12px] font-medium text-secondary hover:text-primary surface-hover transition-colors border border-default flex items-center gap-1.5">
                  <span>{t("openWith", { app: selectedOpener.label })}</span>
                  <ChevronDown className="w-3 h-3 text-tertiary" />
                </span>
              }
            />
            <button
              type="button"
              onClick={() => runAction("launch", undefined)}
              disabled={actionMutation.isPending}
              className="h-8 px-3 rounded-md text-[12px] font-medium text-secondary hover:text-primary surface-hover transition-colors border border-default flex items-center gap-1.5 disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              {t("startOnly")}
            </button>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              onClick={() => runAction("restart", undefined)}
              disabled={actionMutation.isPending}
              className="h-8 px-3 rounded-md text-[12px] font-medium text-secondary hover:text-primary surface-hover transition-colors border border-default flex items-center gap-1.5 disabled:opacity-50"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              {t("restart")}
            </button>
            <button
              type="button"
              onClick={() => {
                setPendingAction({ action: "stop", label: "workspace", danger: true });
                setModalOpen(true);
              }}
              disabled={actionMutation.isPending || runningCount === 0}
              className="h-8 px-3 rounded-md text-[12px] font-medium danger danger-bg hover:opacity-80 transition-opacity flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <CircleStop className="w-3.5 h-3.5" />
              {t("stopWorkspace")}
            </button>
            <button
              type="button"
              onClick={() => refetch()}
              disabled={isFetching}
              className="h-8 px-3 rounded-md text-[12px] font-medium text-secondary hover:text-primary surface-hover transition-colors border border-default flex items-center gap-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin" : ""}`} />
              {t("refresh")}
            </button>
          </div>
        </div>
        {lastActionMessage && (
          <div className="flex items-center gap-2 rounded-md border border-[var(--success)]/10 success-bg px-2.5 py-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-[var(--success)] shrink-0" />
            <p className="text-[11px] font-medium text-secondary">{lastActionMessage}</p>
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
            attachOpenerId={attachOpener.id}
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
        title={pendingAction?.action === "stop" ? t("stop") : t("confirm")}
        description={t("confirmAction", { action: pendingAction?.action || "", name: pendingAction?.label || "" })}
        icon={<AlertTriangle className="w-5 h-5 danger" />}
        confirmText={pendingAction?.action === "stop" ? t("stop") : t("confirm")}
        cancelText={t("cancel")}
        onConfirm={confirmAction}
        variant={pendingAction?.danger ? "danger" : "default"}
      />
    </div>
  );
}
