import { useState, useCallback, useRef, memo, useEffect } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  CircleStop,
  Copy,
  FolderGit2,
  Monitor,
  OctagonAlert,
  PencilLine,
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
  configPath?: string;
  isActive?: boolean;
  onEditTarget?: (target: { slotName: string; windowName?: string }) => void;
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

function openerStorageKey(projectPath?: string, configPath?: string): string {
  return `cc-branch.open.tool.${projectPath || "current"}:${configPath || "default"}`;
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
  if (opener.kind === "editor" && openerSupports(opener, "open_project")) {
    return t("openProjectIn", { app: opener.label });
  }
  return t("openWorkspaceIn", { app: opener.label });
}

function workspaceOpenButtonLabel(t: (key: string, vars?: Record<string, string | number>) => string, opener: OpenerInfo): string {
  return opener.kind === "editor" && openerSupports(opener, "open_project")
    ? t("openProject")
    : t("openWorkspace");
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
      {isRunning ? t("running") : isExternal ? t("openOnDemand") : t("stopped")}
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

function displayAgentName(agent: string): string {
  return agent ? agent.charAt(0).toUpperCase() + agent.slice(1) : agent;
}

function windowSummary(
  t: (key: string, vars?: Record<string, string | number>) => string,
  window: SlotInfo["windows"][number]
): string {
  if (window.agent) {
    return `${displayAgentName(window.agent)} · ${
      window.session_id ? t("sessionBound") : t("newSessionOnStart")
    }`;
  }
  return t("commandSummary", { command: window.command || "-" });
}

function terminalTaskSummary(
  t: (key: string, vars?: Record<string, string | number>) => string,
  window?: SlotInfo["windows"][number]
): string {
  if (!window) return t("terminalTask");
  if (window.agent) {
    return `${displayAgentName(window.agent)} · ${t("terminalTask")} · ${
      window.session_id ? t("sessionBound") : t("newSessionOnStart")
    }`;
  }
  return `${t("terminalTask")} · ${t("commandSummary", { command: window.command || "-" })}`;
}

function windowCountLabel(t: (key: string, vars?: Record<string, string | number>) => string, count: number): string {
  return t(count === 1 ? "windowCountShortOne" : "windowCountShort", { count });
}

function detailValue(value: string | null | undefined): string {
  return value && value.trim() ? value : "-";
}

function CopyValueButton({
  value,
  label,
  onCopy,
}: {
  value: string;
  label: string;
  onCopy: (value: string, label: string) => void;
}) {
  const disabled = value === "-";
  const { t } = useI18n();
  return (
    <button
      type="button"
      onClick={() => onCopy(value, label)}
      disabled={disabled}
      className="icon-touch sm:min-h-7 sm:min-w-7 rounded text-tertiary hover:text-primary hover:surface-hover transition-colors flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed"
      aria-label={t("copyValue", { name: label })}
      title={t("copyValue", { name: label })}
    >
      <Copy className="w-3.5 h-3.5" />
    </button>
  );
}

function DetailItem({
  label,
  value,
  mono = false,
  onCopy,
}: {
  label: string;
  value: string;
  mono?: boolean;
  onCopy?: (value: string, label: string) => void;
}) {
  return (
    <div className="min-w-0 rounded-md bg-[var(--bg-hover)]/55 px-3 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{label}</p>
      <div className="mt-1 flex items-center gap-1.5 min-w-0">
        <p className={`text-[12px] text-secondary truncate ${mono ? "font-mono" : ""}`} title={value}>
          {value}
        </p>
        {onCopy && <CopyValueButton value={value} label={label} onCopy={onCopy} />}
      </div>
    </div>
  );
}

const SlotCard = memo(function SlotCard({
  slot,
  onRunAction,
  onConfirmAction,
  onEditTarget,
  onCopy,
  busy,
  openerId,
  tmuxRuntimeUnavailable,
}: {
  slot: SlotInfo;
  onRunAction: (action: WorkspaceAction, target: string, opener?: string, intent?: OpenIntent) => void;
  onConfirmAction: (action: WorkspaceAction, target: string | undefined, label: string) => void;
  onEditTarget?: (target: { slotName: string; windowName?: string }) => void;
  onCopy: (value: string, label: string) => void;
  busy: boolean;
  openerId: string;
  tmuxRuntimeUnavailable: boolean;
}) {
  const isRunning = slot.status === "running";
  const { t } = useI18n();
  const slotTarget = slot.name;
  const slotRuntimeUnavailable = slot.runtime === "tmux" && tmuxRuntimeUnavailable;
  const [detailsOpen, setDetailsOpen] = useState(false);

  if (slot.runtime === "terminal") {
    const primaryWindow = slot.windows[0];
    return (
      <div
        className={`surface-card border rounded-lg overflow-hidden transition-all duration-200 ease-out hover:shadow-md hover:border-[var(--border-strong)] ${
          isRunning ? "border-[var(--accent-border)] shadow-sm" : "border-default"
        }`}
      >
        <div
          className={`px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
            isRunning ? "accent-bg" : "surface-elevated"
          }`}
        >
          <button
            type="button"
            onClick={() => setDetailsOpen((open) => !open)}
            className="flex items-center gap-3 min-w-0 text-left rounded-md -m-1 p-1 hover:surface-hover transition-colors"
            aria-expanded={detailsOpen}
            aria-label={detailsOpen ? t("hideDetails") : t("showDetails")}
          >
            <div
              className={`w-9 h-9 rounded-md border flex items-center justify-center shrink-0 ${
                isRunning
                  ? "bg-[var(--bg-card)] border-[var(--accent-border)]"
                  : "bg-[var(--bg-card)] border-default"
              }`}
            >
              <SquareTerminal
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
              <p
                className="text-[11px] text-tertiary mt-0.5 truncate"
                title={primaryWindow?.session_id || primaryWindow?.command}
              >
                {terminalTaskSummary(t, primaryWindow)}
              </p>
            </div>
            <ChevronDown className={`w-3.5 h-3.5 text-tertiary shrink-0 transition-transform ${detailsOpen ? "" : "-rotate-90"}`} />
          </button>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => onRunAction("open", slotTarget, openerId, "attach_target")}
              disabled={busy}
              className="control-touch px-3 rounded-md text-[12px] font-medium text-secondary hover:text-primary surface-card border border-default hover:border-[var(--border-strong)] transition-colors flex items-center gap-1.5 disabled:opacity-50"
              aria-label={`${t("openTerminal")} ${slotTarget}`}
            >
              <ExternalLink className="w-3.5 h-3.5" />
              {t("open")}
            </button>
            {onEditTarget && (
              <button
                type="button"
                onClick={() => onEditTarget({ slotName: slot.name })}
                className="control-touch px-3 rounded-md text-[12px] font-medium text-secondary hover:text-primary surface-card border border-default transition-colors flex items-center gap-1.5"
                aria-label={t("editSlotNamed", { name: slotTarget })}
                title={t("editSlotNamed", { name: slotTarget })}
              >
                <PencilLine className="w-3.5 h-3.5" />
                {t("edit")}
              </button>
            )}
          </div>
        </div>
        {detailsOpen && (
          <div className="border-t border-default bg-[var(--bg-card)] px-4 py-3 animate-stagger">
            <div className="grid grid-cols-1 lg:grid-cols-[minmax(180px,240px)_minmax(0,1fr)] gap-3">
              <div className="rounded-md bg-[var(--accent-bg)]/45 px-3 py-2.5">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("runtimeDetails")}</p>
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <StatusBadge status={primaryWindow?.status || slot.status} />
                  <span className="inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold bg-[var(--bg-card)] text-secondary">
                    {displayAgentName(primaryWindow?.agent || "") || t("noAgent")}
                  </span>
                </div>
                <p className="mt-2 text-[11px] text-tertiary truncate" title={primaryWindow?.label || slot.name}>
                  {primaryWindow?.label || slot.name}
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
                <div className="md:col-span-2 xl:col-span-3 rounded-md bg-[var(--bg-hover)]/55 px-3 py-2">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("command")}</p>
                  <div className="mt-1 flex items-center gap-2 min-w-0">
                    <code className="min-w-0 flex-1 truncate text-[12px] text-primary" title={detailValue(primaryWindow?.command)}>
                      {detailValue(primaryWindow?.command)}
                    </code>
                    <CopyValueButton value={detailValue(primaryWindow?.command)} label={t("command")} onCopy={onCopy} />
                  </div>
                </div>
                <DetailItem label={t("sessionId")} value={detailValue(primaryWindow?.session_id)} mono onCopy={onCopy} />
                <DetailItem label={t("workingDirectory")} value={detailValue(primaryWindow?.cwd)} mono onCopy={onCopy} />
                <DetailItem label={t("windowName")} value={detailValue(primaryWindow?.name)} onCopy={onCopy} />
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

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
            <p className="text-[11px] text-tertiary mt-0.5 truncate">
              <span className="font-mono">{slot.session_name}</span>
              <span className="text-muted mx-1">·</span>
              <span>{t("tmuxSession")}</span>
              <span className="text-muted mx-1">·</span>
              <span>{windowCountLabel(t, slot.windows.length)}</span>
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
          {onEditTarget && (
            <button
              type="button"
              onClick={() => onEditTarget({ slotName: slot.name })}
              className="control-touch px-3 rounded-md text-[12px] font-medium text-secondary hover:text-primary surface-card border border-default transition-colors flex items-center gap-1.5"
              aria-label={t("editSlotNamed", { name: slotTarget })}
              title={t("editSlotNamed", { name: slotTarget })}
            >
              <PencilLine className="w-3.5 h-3.5" />
              {t("edit")}
            </button>
          )}
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
                  <SyncBadge status={w.sync_status} />
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <p className="text-[11px] text-tertiary truncate" title={w.session_id || w.command}>
                    {windowSummary(t, w)}
                  </p>
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
              {onEditTarget && (
                <button
                  type="button"
                  onClick={() => onEditTarget({ slotName: slot.name, windowName: w.name })}
                  className="control-touch px-3 rounded-md text-[12px] font-medium text-secondary hover:text-primary surface-card border border-default transition-colors flex items-center justify-center gap-1.5"
                  aria-label={t("editWindowNamed", { name: windowTarget })}
                  title={t("editWindowNamed", { name: windowTarget })}
                >
                  <PencilLine className="w-3.5 h-3.5" />
                  <span>{t("edit")}</span>
                </button>
              )}
              <button
                type="button"
                onClick={() => onRunAction("open", windowTarget, openerId, "attach_target")}
                disabled={busy || slotRuntimeUnavailable}
                className="icon-touch sm:min-h-9 sm:min-w-9 rounded-md text-tertiary hover:text-primary hover:surface-hover transition-colors flex items-center justify-center disabled:opacity-50"
                aria-label={`${t("openTerminal")} ${windowTarget}`}
                title={slotRuntimeUnavailable ? t("tmuxRuntimeUnavailable") : `${t("openTerminal")} ${windowTarget}`}
              >
                <ExternalLink className="w-3.5 h-3.5" />
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

export default function Dashboard({ projectPath, configPath, isActive = true, onEditTarget }: DashboardProps) {
  const { t } = useI18n();
  const toast = useToast();
  const scope = { projectPath, configPath };
  const { data, error, isLoading, isError, refetch } =
    useWorkspace(scope, isActive);
  const { data: openersData } = useOpeners(scope, isActive);
  const actionMutation = useWorkspaceAction();

  const [modalOpen, setModalOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [lastActionMessage, setLastActionMessage] = useState<string | null>(null);
  const [selectedOpenerId, setSelectedOpenerId] = useState<string>(() => {
    if (typeof window === "undefined") return "auto-terminal";
    return (
      window.localStorage.getItem(openerStorageKey(projectPath, configPath)) ||
      window.localStorage.getItem(`cc-branch.open.tool.${projectPath || "current"}`) ||
      "auto-terminal"
    );
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
        ...(configPath ? { configPath } : {}),
        stopRemoved,
      });
      toast.success(result.message);
      setLastActionMessage(result.message);
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = setTimeout(() => refetch(), 500);
    } catch (e: unknown) {
      toast.error(String(e));
    }
  }, [projectPath, configPath, actionMutation, toast, refetch]);

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
      const textArea = document.createElement("textarea");
      textArea.value = value;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
    }
    toast.success(t("copiedValue", { name: label }));
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
    if (isNoConfig) return <SetupGuide projectPath={projectPath} configPath={configPath} onRefresh={refetch} />;
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
    return <SetupGuide projectPath={projectPath} configPath={configPath} onRefresh={refetch} />;
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
  const externalCount = data.slots.filter((s) => s.status === "external").length;
  const totalWindows = data.slots.reduce((count, slot) => count + slot.windows.length, 0);
  const hasTmuxSlots = data.slots.some((s) => s.runtime === "tmux");
  const hasOnlyTerminalSlots = data.slots.every((s) => s.runtime === "terminal");
  const tmuxRuntimeUnavailable = hasTmuxSlots && data.runtimes?.tmux?.available === false;
  const canManageTmuxSlots = hasTmuxSlots && !tmuxRuntimeUnavailable;
  const canRestartWorkspace = canManageTmuxSlots && runningCount > 0;
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
  const runtimeActionCount = syncCount + extraCount;
  const workspaceStateLabel = tmuxRuntimeUnavailable
    ? t("workspaceStateUnavailable")
    : runtimeSyncNotices.length > 0
      ? t("workspaceStateNeedsAttention")
      : hasOnlyTerminalSlots
        ? t("workspaceStateReady")
      : runningCount > 0
        ? t("workspaceStateRunning")
        : t("workspaceStateStopped");
  const workspaceStateClass = tmuxRuntimeUnavailable
    ? "danger-bg danger"
    : runtimeSyncNotices.length > 0
      ? "bg-[var(--warning-bg)] text-[var(--warning)]"
      : hasOnlyTerminalSlots
        ? "accent-bg accent"
      : runningCount > 0
        ? "success-bg success"
        : "bg-[var(--bg-hover)] text-tertiary";
  const workspaceSyncLabel = runtimeActionCount > 0 || tmuxRuntimeUnavailable
    ? t("workspaceSyncNeedsAction", { count: runtimeActionCount || 1 })
    : hasOnlyTerminalSlots
      ? t("workspaceSyncTerminalClean")
    : t("workspaceSyncClean");
  const openers = openersData?.openers?.length ? openersData.openers : [DEFAULT_OPENER];
  const defaultOpenerId = openersData?.default || "auto-terminal";
  const availableOpeners = openers.filter((opener) => opener.available);
  const workspaceOpeners = openers.filter(canOfferWorkspaceOpen);
  const availableWorkspaceOpeners = workspaceOpeners.filter((opener) => opener.available);
  const selectedOpener = availableWorkspaceOpeners.find((opener) => opener.id === selectedOpenerId)
    || availableWorkspaceOpeners.find((opener) => opener.id === defaultOpenerId)
    || availableWorkspaceOpeners[0]
    || DEFAULT_OPENER;
  const projectDirectoryOpener = openerSupports(selectedOpener, "open_project")
    ? selectedOpener
    : availableOpeners.find((opener) => opener.id === "system-file-manager") || selectedOpener;
  const openerItems = workspaceOpeners.map((opener) => ({
    label: opener.label,
    value: opener.id,
    disabled: !opener.available,
    description: opener.reason,
  }));

  const setDefaultOpener = (value: string) => {
    setSelectedOpenerId(value);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(openerStorageKey(projectPath, configPath), value);
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
              <div className="flex flex-wrap items-center gap-2 min-w-0">
                <p className="text-[16px] font-semibold text-primary leading-tight truncate">
                  {data.project || data.project_name}
                </p>
                <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold ${workspaceStateClass}`}>
                  {workspaceStateLabel}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-tertiary">
                <span>{t("workspaceCounts", { running: runningCount, total: data.slots.length, windows: totalWindows })}</span>
                {externalCount > 0 && <span>{t("workspaceTerminalSummary", { count: externalCount })}</span>}
                <span className={runtimeActionCount > 0 || tmuxRuntimeUnavailable ? "text-[var(--warning)] font-medium" : "success font-medium"}>
                  {workspaceSyncLabel}
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[12px] text-tertiary shrink-0 rounded-full bg-[var(--bg-card)]/70 px-3 py-1.5">
            <span>{t("lastCheckedAt", { time: lastUpdated || "--" })}</span>
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
                <span className="truncate">{workspaceOpenButtonLabel(t, selectedOpener)}</span>
              </button>
              <Dropdown
                align="left"
                value={selectedOpener.id}
                items={openerItems}
                onChange={setDefaultOpener}
                ariaLabel={t("selectedTool", { app: selectedOpener.label })}
                trigger={
                  <span className="control-touch w-[168px] sm:w-[184px] min-w-0 px-3 rounded-r-md rounded-l-none border-l border-white/20 bg-[var(--accent)] text-[var(--text-on-accent)] hover:bg-[var(--accent-light)] transition-colors flex items-center justify-between gap-2">
                    <span className="min-w-0 flex-1 truncate text-left text-[13px] font-semibold">{selectedOpener.label}</span>
                    <ChevronDown className="ml-auto w-3 h-3 shrink-0 opacity-80" />
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
                disabled={actionMutation.isPending || !canRestartWorkspace}
                className="icon-touch rounded text-secondary hover:text-primary hover:surface-hover transition-colors flex items-center justify-center disabled:opacity-50"
                title={
                  tmuxRuntimeUnavailable
                    ? t("tmuxRuntimeUnavailable")
                    : hasTmuxSlots
                      ? runningCount > 0 ? t("restart") : t("restartNoRunning")
                      : t("tmuxOnlyAction")
                }
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
                className="icon-touch rounded text-secondary hover:text-primary hover:surface-hover transition-colors flex items-center justify-center"
                title={t("refresh")}
                aria-label={t("refresh")}
              >
                <RefreshCw className="w-4 h-4" />
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
            onEditTarget={onEditTarget}
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
