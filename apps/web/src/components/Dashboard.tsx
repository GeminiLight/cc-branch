import { useState, useCallback, useRef, memo, useEffect } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Eye,
  FolderGit2,
  Monitor,
  OctagonAlert,
  PencilLine,
  RefreshCw,
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
import claudeIconUrl from "../assets/agent-icons/claude.svg";
import cursorIconUrl from "../assets/agent-icons/cursor.svg";
import geminiIconUrl from "../assets/agent-icons/gemini.svg";
import kimiIconUrl from "../assets/agent-icons/kimi.svg";
import openaiIconUrl from "../assets/agent-icons/openai.svg";

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
  return t("launchWorkspaceIn", { app: opener.label });
}

function workspaceOpenButtonLabel(t: (key: string, vars?: Record<string, string | number>) => string): string {
  return t("launch");
}

function isActionableSyncStatus(status?: SyncStatus): boolean {
  return status === "changed" || status === "missing" || status === "untracked";
}

function SyncBadge({ status, slotStatus }: { status?: SyncStatus; slotStatus?: SlotInfo["status"] }) {
  const { t } = useI18n();
  if (!status || status === "current" || status === "external") return null;
  if (status === "missing" && slotStatus && slotStatus !== "running") return null;
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

function paneCountLabel(t: (key: string, vars?: Record<string, string | number>) => string, count: number): string {
  return t(count === 1 ? "paneCountShortOne" : "paneCountShort", { count });
}

function tabPaneCount(slot: SlotInfo): number {
  return slot.runtime === "tmux" ? 1 : 1;
}

function tabDisplayName(t: (key: string, vars?: Record<string, string | number>) => string, index: number): string {
  return t("tabDisplayName", { index: index + 1 });
}

function normalizeAgentKey(agent: string | null | undefined): string {
  const value = (agent || "").toLowerCase();
  const compact = value.replace(/[\s_-]+/g, "");
  if (value.includes("codex")) return "codex";
  if (compact.includes("claude") || compact.includes("cloudcode") || compact.includes("anthropic")) return "claude";
  if (compact.includes("gemini") || compact.includes("antigravity")) return "gemini";
  if (compact.includes("cursor")) return "cursor";
  if (compact.includes("kimi")) return "kimi";
  return value;
}

function agentIdentity(agent: string | null | undefined) {
  const key = normalizeAgentKey(agent);
  if (key === "codex") return { label: "Codex", initials: "Cx", iconUrl: openaiIconUrl, tone: "bg-white text-zinc-950 border-zinc-200 dark:bg-zinc-100 dark:text-zinc-950 dark:border-zinc-300" };
  if (key === "claude") return { label: "Claude", initials: "Cl", iconUrl: claudeIconUrl, tone: "bg-[#f4eee7] text-[#8a4b25] border-[#dfcabc] dark:bg-[#2a1d17] dark:text-[#f2c6a4] dark:border-[#5f3b2a]" };
  if (key === "gemini") return { label: "Gemini", initials: "G", iconUrl: geminiIconUrl, tone: "bg-[#eef4ff] text-[#2459c7] border-[#c8d9ff] dark:bg-[#101a2e] dark:text-[#9bbcff] dark:border-[#293d66]" };
  if (key === "cursor") return { label: "Cursor", initials: "Cu", iconUrl: cursorIconUrl, tone: "bg-zinc-950 text-white border-zinc-800 dark:bg-zinc-100 dark:text-zinc-950 dark:border-zinc-300" };
  if (key === "kimi") return { label: "Kimi", initials: "Ki", iconUrl: kimiIconUrl, tone: "bg-[#f2efff] text-[#5d48b1] border-[#d7cff7] dark:bg-[#191329] dark:text-[#c8bbff] dark:border-[#3e3268]" };
  if (agent) {
    const label = displayAgentName(agent);
    return { label, initials: label.slice(0, 2) || "A", tone: "bg-[var(--bg-elevated)] text-secondary border-default" };
  }
  return { label: "Shell", initials: "$", tone: "bg-[var(--accent-bg)] text-[var(--accent)] border-[var(--accent-border)]" };
}

function AgentMark({ agent }: { agent?: string | null }) {
  const identity = agentIdentity(agent);
  return (
    <span
      className={`inline-flex h-5 w-5 shrink-0 items-center justify-center overflow-hidden rounded border text-[9px] font-bold ${identity.tone}`}
      title={identity.label}
      aria-label={identity.label}
    >
      {"iconUrl" in identity && identity.iconUrl ? (
        <img src={identity.iconUrl} alt="" className="h-3.5 w-3.5 object-contain" draggable={false} />
      ) : (
        identity.initials
      )}
    </span>
  );
}

function PaneStatus({ status }: { status: SlotInfo["status"] }) {
  const { t } = useI18n();
  const isRunning = status === "running";
  const isExternal = status === "external";
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-semibold ${isRunning ? "success" : "text-tertiary"}`}>
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          isRunning ? "bg-[var(--success)]" : isExternal ? "bg-[var(--accent)]" : "bg-[var(--text-muted)]"
        }`}
        aria-hidden="true"
      />
      {isRunning ? t("running") : isExternal ? t("ready") : t("notStarted")}
    </span>
  );
}

function windowSummary(
  t: (key: string, vars?: Record<string, string | number>) => string,
  window: SlotInfo["windows"][number]
): string {
  if (window.agent) {
    return window.session_id ? t("sessionBound") : t("newSessionOnStart");
  }
  return t("commandSummary", { command: window.command || "-" });
}

function terminalTaskSummary(
  t: (key: string, vars?: Record<string, string | number>) => string,
  window?: SlotInfo["windows"][number]
): string {
  if (!window) return t("terminalTask");
  if (window.agent) {
    return window.session_id ? t("sessionBound") : t("newSessionOnStart");
  }
  return t("commandSummary", { command: window.command || "-" });
}

const SlotCard = memo(function SlotCard({
  slot,
  index,
  onRunAction,
  onRepairTarget,
  onEditTarget,
  busy,
  openerId,
  tmuxRuntimeUnavailable,
}: {
  slot: SlotInfo;
  index: number;
  onRunAction: (action: WorkspaceAction, target: string, opener?: string, intent?: OpenIntent) => void;
  onRepairTarget: (target: string) => void;
  onEditTarget?: (target: { slotName: string; windowName?: string }) => void;
  busy: boolean;
  openerId: string;
  tmuxRuntimeUnavailable: boolean;
}) {
  const isRunning = slot.status === "running";
  const { t } = useI18n();
  const slotTarget = slot.name;
  const slotRuntimeUnavailable = slot.runtime === "tmux" && tmuxRuntimeUnavailable;
  const primaryActionLabel = t("open");
  const paneActionClassName = "icon-touch sm:min-h-8 sm:min-w-8 rounded-md text-tertiary hover:text-primary hover:surface-hover transition-colors flex items-center justify-center disabled:opacity-50";
  const primaryWindow = slot.windows[0];
  const paneCount = tabPaneCount(slot);
  const tabName = slot.name || tabDisplayName(t, index);
  const terminalSummary = terminalTaskSummary(t, primaryWindow);
  const internalWindowCount = slot.runtime === "tmux" ? slot.windows.length : 0;
  const slotNeedsAction = isActionableSyncStatus(slot.sync_status) || slot.windows.some((w) => isActionableSyncStatus(w.sync_status));
  const primaryWindowNeedsAction = isActionableSyncStatus(primaryWindow?.sync_status) || (slot.runtime === "terminal" && isActionableSyncStatus(slot.sync_status));

  return (
    <div
      className={`relative grid grid-cols-1 lg:grid-cols-[154px_minmax(0,1fr)] surface-card border rounded-lg overflow-hidden transition-all duration-200 ease-out ${
        slotNeedsAction ? "border-[var(--warning)]/55 shadow-[0_0_0_3px_var(--warning-bg)]" : isRunning ? "border-[var(--accent-border)]" : "border-default"
      }`}
    >
      <div className={`absolute left-0 top-0 bottom-0 w-0.5 ${isRunning ? "bg-[var(--success)]" : "bg-[var(--border-subtle)]"}`} aria-hidden="true" />
      <div className="bg-[var(--bg-card)]/70 px-4 py-3 border-b lg:border-b-0 lg:border-r border-subtle">
        <div className="flex lg:flex-col gap-3 min-w-0">
          <div
            className={`w-8 h-8 rounded-md border flex items-center justify-center shrink-0 ${
              isRunning
                ? "bg-[var(--bg-card)] border-[var(--accent-border)]"
                : "bg-transparent border-default"
            }`}
          >
            <Monitor className={`w-4 h-4 shrink-0 ${isRunning ? "text-[var(--accent)]" : "text-tertiary"}`} />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded bg-[var(--bg-hover)] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-tertiary">
                {t("tabLabel")}
              </span>
              <h3 className="text-[14px] font-semibold text-primary leading-tight truncate">
                {tabName}
              </h3>
              <SyncBadge status={slot.sync_status} slotStatus={slot.status} />
            </div>
            <p className="text-[11px] text-tertiary mt-0.5 truncate">
              <span>{paneCountLabel(t, paneCount)}</span>
              {internalWindowCount > 0 && (
                <>
                  <span className="text-muted mx-1">·</span>
                  <span>{t("tmuxWindowCount", { count: internalWindowCount })}</span>
                </>
              )}
            </p>
          </div>
        </div>
      </div>

      <div className="bg-[var(--bg-card)] p-3">
        {slot.runtime === "terminal" ? (
          <div className={`rounded-md border bg-[var(--bg-elevated)] px-3 py-2.5 ${
            primaryWindowNeedsAction ? "border-[var(--warning)]/55 shadow-[0_0_0_2px_var(--warning-bg)]" : "border-default"
          }`}>
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-7 h-7 rounded-md border border-default bg-[var(--bg-card)] text-[var(--accent)] flex items-center justify-center shrink-0">
                  <SquareTerminal className="w-4 h-4 shrink-0" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <AgentMark agent={primaryWindow?.agent} />
                    <span className="text-[13px] font-semibold text-primary">{t("terminalLabel")}</span>
                    <PaneStatus status={primaryWindow?.status || slot.status} />
                  </div>
                  <p className="mt-0.5 text-[11px] text-tertiary truncate" title={primaryWindow?.session_id || primaryWindow?.command || undefined}>
                    {terminalSummary}
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-end gap-1 shrink-0">
                {primaryWindowNeedsAction && (
                  <button
                    type="button"
                    onClick={() => onRepairTarget(slotTarget)}
                    disabled={busy || slotRuntimeUnavailable}
                    className="control-touch px-2 rounded-md text-[11px] font-semibold bg-[var(--warning-bg)] text-[var(--warning)] hover:border-[var(--warning)]/30 border border-transparent transition-colors disabled:opacity-50"
                    title={t("repairItem")}
                    aria-label={t("repairItem")}
                  >
                    {t("repair")}
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => onRunAction("open", slotTarget, openerId, "attach_target")}
                  disabled={busy || slotRuntimeUnavailable}
                  className={paneActionClassName}
                  aria-label={`${primaryActionLabel} ${slotTarget}`}
                  title={slotRuntimeUnavailable ? t("tmuxRuntimeUnavailable") : primaryActionLabel}
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
                {onEditTarget && (
                  <button
                    type="button"
                    onClick={() => onEditTarget({ slotName: slot.name })}
                    className={paneActionClassName}
                    aria-label={t("editSlotNamed", { name: slotTarget })}
                    title={t("editSlotNamed", { name: slotTarget })}
                  >
                    <PencilLine className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className={`rounded-md border bg-[var(--bg-elevated)] px-3 py-2.5 ${
            slotNeedsAction ? "border-[var(--warning)]/55 shadow-[0_0_0_2px_var(--warning-bg)]" : "border-default"
          }`}>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-7 h-7 rounded-md border border-default bg-[var(--bg-card)] text-[var(--accent)] flex items-center justify-center shrink-0">
                  <Monitor className="w-4 h-4 shrink-0" />
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-[13px] font-semibold text-primary">{t("tmuxPane")}</span>
                    <PaneStatus status={slot.status} />
                  </div>
                  <div className="mt-1 flex min-w-0 items-center gap-1.5 text-[10px] text-tertiary">
                    <span>{t("tmuxSession")}</span>
                    <span className="text-muted">·</span>
                    <span className="truncate font-mono" title={slot.session_name}>{slot.session_name}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-end gap-1">
                {isActionableSyncStatus(slot.sync_status) && !slot.windows.some((w) => isActionableSyncStatus(w.sync_status)) && (
                  <button
                    type="button"
                    onClick={() => onRepairTarget(slotTarget)}
                    disabled={busy || slotRuntimeUnavailable}
                    className="control-touch px-2 rounded-md text-[11px] font-semibold bg-[var(--warning-bg)] text-[var(--warning)] hover:border-[var(--warning)]/30 border border-transparent transition-colors disabled:opacity-50"
                    title={t("repairItem")}
                    aria-label={t("repairItem")}
                  >
                    {t("repair")}
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => onRunAction("open", slotTarget, openerId, "attach_target")}
                  disabled={busy || slotRuntimeUnavailable}
                  className={paneActionClassName}
                  aria-label={`${primaryActionLabel} ${slotTarget}`}
                  title={slotRuntimeUnavailable ? t("tmuxRuntimeUnavailable") : primaryActionLabel}
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
                {onEditTarget && (
                  <button
                    type="button"
                    onClick={() => onEditTarget({ slotName: slot.name })}
                    className={paneActionClassName}
                    aria-label={t("editSlotNamed", { name: slotTarget })}
                    title={t("editSlotNamed", { name: slotTarget })}
                  >
                    <PencilLine className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            <div className="mt-2 rounded-md border border-subtle bg-[var(--bg-card)]">
              <div className="flex items-center justify-between gap-2 border-b border-subtle px-2.5 py-1.5">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary">{t("tmuxWindows")}</p>
                <span className="text-[10px] text-muted">{t("tmuxWindowCount", { count: slot.windows.length })}</span>
              </div>
              <div className="divide-y divide-[var(--border-subtle)]">
                {slot.windows.map((w) => {
                  const windowTarget = `${slot.name}:${w.name}`;
                  const windowNeedsAction = isActionableSyncStatus(w.sync_status);
                  return (
                    <div
                      key={w.name}
                      className={`flex flex-col lg:flex-row lg:items-center justify-between gap-2 px-2.5 py-2 ${
                        windowNeedsAction ? "bg-[var(--warning-bg)]/45 ring-1 ring-inset ring-[var(--warning)]/25" : ""
                      }`}
                    >
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <AgentMark agent={w.agent} />
                          <span className="text-[12px] font-semibold text-primary truncate">{w.name}</span>
                          <SyncBadge status={w.sync_status} slotStatus={slot.status} />
                        </div>
                        <p className="mt-0.5 text-[11px] text-tertiary truncate" title={w.session_id || w.command}>
                          {windowSummary(t, w)}
                        </p>
                      </div>
                      <div className="flex items-center justify-end gap-1 shrink-0">
                        {windowNeedsAction && (
                          <button
                            type="button"
                            onClick={() => onRepairTarget(windowTarget)}
                            disabled={busy || slotRuntimeUnavailable}
                            className="control-touch px-2 rounded-md text-[11px] font-semibold bg-[var(--warning-bg)] text-[var(--warning)] hover:border-[var(--warning)]/30 border border-transparent transition-colors disabled:opacity-50"
                            title={t("repairItem")}
                            aria-label={t("repairItem")}
                          >
                            {t("repair")}
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => onRunAction("open", windowTarget, openerId, "attach_target")}
                          disabled={busy || slotRuntimeUnavailable}
                          className={paneActionClassName}
                          aria-label={`${primaryActionLabel} ${windowTarget}`}
                          title={slotRuntimeUnavailable ? t("tmuxRuntimeUnavailable") : `${primaryActionLabel} ${windowTarget}`}
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </button>
                        {onEditTarget && (
                          <button
                            type="button"
                            onClick={() => onEditTarget({ slotName: slot.name, windowName: w.name })}
                            className={paneActionClassName}
                            aria-label={t("editWindowNamed", { name: windowTarget })}
                            title={t("editWindowNamed", { name: windowTarget })}
                          >
                            <PencilLine className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
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
  const slotsSectionRef = useRef<HTMLDivElement | null>(null);

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
  const totalWindows = data.slots.reduce((count, slot) => count + tabPaneCount(slot), 0);
  const hasTmuxSlots = data.slots.some((s) => s.runtime === "tmux");
  const tmuxRuntimeUnavailable = hasTmuxSlots && data.runtimes?.tmux?.available === false;
  const syncSummary = data.runtime_sync?.summary;
  const changedCount = syncSummary?.changed || 0;
  const missingCount = syncSummary?.missing || 0;
  const untrackedCount = syncSummary?.untracked || 0;
  const extraCount = syncSummary?.extra || 0;
  const syncCount = changedCount + missingCount + untrackedCount;
  const issueCount = Math.max(syncCount + extraCount, tmuxRuntimeUnavailable ? 1 : 0);
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
  const projectDirectoryOpener = availableOpeners.find((opener) => opener.id === "system-file-manager");
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

  const viewIssues = () => {
    slotsSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const requestRepair = (target: string) => {
    requestConfirmedAction("sync", target, t("repairItem"), {
      confirmText: t("repair"),
      description: t("repairConfirmDescription", { target }),
    });
  };

  const runProjectOpen = () => {
    if (!projectDirectoryOpener || !openerSupports(projectDirectoryOpener, "open_project")) return;
    runAction("open", undefined, projectDirectoryOpener.id, "project_folder");
  };

  return (
    <div className="page-shell space-y-3">
      {/* Project summary */}
      <div className="surface-command border border-default rounded-lg px-4 sm:px-5 py-4 flex flex-col gap-3">
        <div className="flex flex-col xl:flex-row xl:items-start justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-md bg-[var(--accent-bg)] border border-[var(--accent-border)] flex items-center justify-center shrink-0">
              <FolderGit2 className="w-4 h-4 text-[var(--accent)]" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2 min-w-0">
                <p className="text-[16px] font-semibold text-primary leading-tight truncate">
                  {data.project || data.project_name}
                </p>
              </div>
              <div className="mt-2 grid grid-cols-3 gap-1.5 w-full max-w-[460px]">
                <div className="rounded-md bg-[var(--bg-hover)]/55 px-2.5 py-1.5">
                  <p className="text-[9px] font-semibold uppercase tracking-wide text-tertiary">{t("workspaceRunning")}</p>
                  <p className="mt-0.5 text-[13px] font-semibold text-primary">{runningCount}/{data.slots.length}</p>
                </div>
                <div className="rounded-md bg-[var(--bg-hover)]/55 px-2.5 py-1.5">
                  <p className="text-[9px] font-semibold uppercase tracking-wide text-tertiary">{t("workspaceNeedsAction")}</p>
                  <div className="mt-0.5 flex items-center gap-1.5">
                    <p className={`text-[13px] font-semibold ${issueCount > 0 ? "text-[var(--warning)]" : "text-primary"}`}>{issueCount}</p>
                    {issueCount > 0 && (
                      <button
                        type="button"
                        onClick={viewIssues}
                        className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold text-[var(--warning)] hover:bg-[var(--warning-bg)] transition-colors"
                      >
                        <Eye className="w-3 h-3" />
                        {t("viewIssues")}
                      </button>
                    )}
                  </div>
                </div>
                <div className="rounded-md bg-[var(--bg-hover)]/55 px-2.5 py-1.5">
                  <p className="text-[9px] font-semibold uppercase tracking-wide text-tertiary">{t("workspaceWindows")}</p>
                  <p className="mt-0.5 text-[13px] font-semibold text-primary">{totalWindows}</p>
                </div>
              </div>
            </div>
          </div>
          <div className="w-full xl:w-auto xl:min-w-[500px] flex flex-col items-stretch sm:items-end gap-2">
            <div className="flex flex-col sm:flex-row sm:justify-end gap-1.5">
              <div className="flex items-center justify-end gap-1.5">
                <button
                  type="button"
                  onClick={runProjectOpen}
                  disabled={actionMutation.isPending || !projectDirectoryOpener || !openerSupports(projectDirectoryOpener, "open_project")}
                  title={projectDirectoryOpener
                    ? (openerSupports(projectDirectoryOpener, "open_project")
                      ? t("openProjectDirectory")
                      : t("toolCannotOpenProject", { app: projectDirectoryOpener.label }))
                    : t("systemFileManagerUnavailable")}
                  aria-label={t("openProjectDirectory")}
                  className="control-touch px-2.5 rounded-md text-[12px] font-semibold text-secondary hover:text-primary surface-card border border-default hover:border-[var(--border-strong)] transition-colors flex items-center justify-center gap-1.5 disabled:opacity-45 disabled:cursor-not-allowed"
                >
                  {actionMutation.isPending ? (
                    <div className="w-3.5 h-3.5 border-2 border-current/30 border-t-current rounded-full animate-spin" />
                  ) : (
                    <FolderGit2 className="w-3.5 h-3.5 shrink-0" />
                  )}
                  <span>{t("openDirectory")}</span>
                </button>
                <button
                  type="button"
                  onClick={() => refetch()}
                  className="control-touch px-2.5 rounded-md text-[12px] font-semibold text-secondary hover:text-primary surface-card border border-default hover:border-[var(--border-strong)] transition-colors flex items-center justify-center gap-1.5"
                  title={t("lastCheckedAt", { time: lastUpdated || "--" })}
                  aria-label={t("refreshStatus")}
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>{t("refreshStatus")}</span>
                </button>
              </div>
              <div className="inline-flex min-w-0 rounded-md">
                <Dropdown
                  align="left"
                  value={selectedOpener.id}
                  items={openerItems}
                  onChange={setDefaultOpener}
                  ariaLabel={t("selectedTool", { app: selectedOpener.label })}
                  trigger={
                    <span className="control-touch w-[112px] sm:w-[132px] min-w-0 px-2.5 rounded-l-md rounded-r-none surface-card border border-default border-r-0 text-secondary hover:text-primary hover:border-[var(--border-strong)] transition-colors flex items-center justify-between gap-2">
                      <span className="min-w-0 flex-1 truncate text-left text-[12px] font-medium">{selectedOpener.label}</span>
                      <ChevronDown className="ml-auto w-3 h-3 shrink-0 opacity-70" />
                    </span>
                  }
                />
                <button
                  type="button"
                  onClick={runWorkspaceOpen}
                  disabled={actionMutation.isPending || !canOpenWorkspace(selectedOpener)}
                  className="control-touch min-w-[82px] px-3 rounded-r-md rounded-l-none text-[13px] font-semibold bg-[var(--accent)] text-[var(--text-on-accent)] border border-[var(--accent)] hover:opacity-90 transition-opacity flex items-center justify-center gap-2 disabled:opacity-50"
                  title={!canOpenWorkspace(selectedOpener) ? t("toolCannotOpenWorkspace", { app: selectedOpener.label }) : workspaceOpenLabel(t, selectedOpener)}
                  aria-label={workspaceOpenLabel(t, selectedOpener)}
                >
                  {actionMutation.isPending ? (
                    <div className="w-4 h-4 border-2 border-current/30 border-t-current rounded-full animate-spin" />
                  ) : (
                    <ExternalLink className="w-4 h-4 shrink-0" />
                  )}
                  <span className="truncate">{workspaceOpenButtonLabel(t)}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
        {lastActionMessage && (
          <div className="flex items-center gap-2 rounded-md success-bg px-2.5 py-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-[var(--success)] shrink-0" />
            <p className="text-[11px] font-medium text-secondary">{lastActionMessage}</p>
          </div>
        )}
      </div>

      {/* Slot cards */}
      <div ref={slotsSectionRef} className="flex items-center justify-between gap-2 px-0.5 pt-1 scroll-mt-24">
        <div className="flex items-center gap-2 min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-tertiary">{t("workspaceTabs")}</p>
          {runtimeSyncNotices.length > 0 && (
            <span className="inline-flex items-center gap-1 rounded-md bg-[var(--warning-bg)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--warning)]">
              <AlertTriangle className="w-3 h-3" />
              {t("workspaceSyncNeedsAction", { count: issueCount })}
            </span>
          )}
        </div>
        <span className="text-[11px] text-muted">{t("workspaceCounts", { total: data.slots.length, windows: totalWindows })}</span>
      </div>
      {runtimeSyncNotices.length > 0 && (
        <div className="sr-only" aria-live="polite">
          {runtimeSyncNotices.map((notice) => (
            <span key={notice}>{notice}</span>
          ))}
        </div>
      )}
      {data.slots.map((slot, i) => (
        <div key={slot.name} className="animate-stagger" style={{ animationDelay: `${i * 60}ms`, opacity: 0 }}>
          <SlotCard
            slot={slot}
            index={i}
            onRunAction={runAction}
            onEditTarget={onEditTarget}
            busy={actionMutation.isPending}
            openerId={selectedOpener.id}
            onRepairTarget={requestRepair}
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
