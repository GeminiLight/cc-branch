import type { SlotInfo, SyncStatus, WindowInfo, WorkspaceStatus } from "../types";
import {
  runningWorkspaceTabCount,
  tabPaneCount,
  workspaceTabCount,
} from "./workspace-status-view-model";

export {
  runningWorkspaceTabCount,
  tabPaneCount,
  workspaceTabCount,
} from "./workspace-status-view-model";

type Translate = (key: string, vars?: Record<string, string | number>) => string;

export interface DashboardRuntimeSummary {
  runningCount: number;
  totalTabs: number;
  totalPanes: number;
  hasTmuxSlots: boolean;
  tmuxRuntimeUnavailable: boolean;
  changedCount: number;
  untrackedCount: number;
  extraCount: number;
  orphanedCount: number;
  driftCount: number;
  syncCount: number;
  issueCount: number;
}

export function isActionableSyncStatus(status?: SyncStatus, slotStatus?: SlotInfo["status"]): boolean {
  if (status === "missing") return slotStatus === "running";
  return status === "changed" || status === "untracked";
}

export function isActionableWindowSync(window: WindowInfo | undefined, slot: SlotInfo): boolean {
  if (!window) return false;
  return isActionableSyncStatus(window.sync_status, slot.status);
}

export function actionableRuntimeDriftCount(slots: SlotInfo[]): number {
  return slots.reduce((count, slot) => {
    const slotDrift = isActionableSyncStatus(slot.sync_status, slot.status)
      && !slot.windows.some((window) => isActionableWindowSync(window, slot))
      ? 1
      : 0;
    const windowDrift = slot.windows.filter((window) => isActionableWindowSync(window, slot)).length;
    return count + slotDrift + windowDrift;
  }, 0);
}

export function workspaceCountLabel(t: Translate, tabs: number, panes: number): string {
  const tabLabel = t(tabs === 1 ? "tabCountOne" : "tabCount", { count: tabs });
  const paneLabel = t(panes === 1 ? "workspacePaneCountOne" : "workspacePaneCount", { count: panes });
  return `${tabLabel} · ${paneLabel}`;
}

export function buildDashboardRuntimeSummary(data: WorkspaceStatus): DashboardRuntimeSummary {
  const syncSummary = data.runtime_sync?.summary;
  const changedCount = syncSummary?.changed || 0;
  const untrackedCount = syncSummary?.untracked || 0;
  const extraCount = syncSummary?.extra || 0;
  const orphanedCount = Math.max(syncSummary?.orphaned || 0, data.runtime_sync?.orphaned_state?.length || 0);
  const driftCount = actionableRuntimeDriftCount(data.slots);
  const summaryActionCount = changedCount + untrackedCount;
  const syncCount = Math.max(driftCount, summaryActionCount);
  const hasTmuxSlots = data.slots.some((slot) => slot.runtime === "tmux");
  const tmuxRuntimeUnavailable = hasTmuxSlots && data.runtimes?.tmux?.available === false;
  const totalTabs = workspaceTabCount(data.slots);

  return {
    runningCount: runningWorkspaceTabCount(data.slots),
    totalTabs,
    totalPanes: data.slots.reduce((count, slot) => count + tabPaneCount(slot), 0),
    hasTmuxSlots,
    tmuxRuntimeUnavailable,
    changedCount,
    untrackedCount,
    extraCount,
    orphanedCount,
    driftCount,
    syncCount,
    issueCount: syncCount + extraCount + orphanedCount + (tmuxRuntimeUnavailable ? 1 : 0),
  };
}
