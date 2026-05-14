import type { SlotInfo, SyncStatus, WindowInfo, WorkspaceStatus } from "../types";

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

export function tabPaneCount(slot: SlotInfo): number {
  if (slot.runtime === "tmux") return 1;
  return Math.max(slot.windows.length, 1);
}

function tabGroupName(slot: SlotInfo): string {
  return slot.split_group || slot.name;
}

export function workspaceTabCount(slots: SlotInfo[]): number {
  return new Set(slots.map(tabGroupName)).size;
}

export function runningWorkspaceTabCount(slots: SlotInfo[]): number {
  const runningTabs = new Set<string>();
  for (const slot of slots) {
    if (slot.status === "running") {
      runningTabs.add(tabGroupName(slot));
    }
  }
  return runningTabs.size;
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
    driftCount,
    syncCount,
    issueCount: syncCount + extraCount + (tmuxRuntimeUnavailable ? 1 : 0),
  };
}
