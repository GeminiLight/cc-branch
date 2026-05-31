import type { SlotConfig, WindowConfig } from "./types";

function renameWindowAgentReference(
  window: WindowConfig,
  rename: { from: string; to: string },
): WindowConfig {
  const next: WindowConfig = {
    ...window,
    agent: window.agent === rename.from ? rename.to : window.agent,
  };
  if (window.windows) {
    next.windows = window.windows.map((child) => renameWindowAgentReference(child, rename));
  }
  return next;
}

export function renameSlotAgentReferences(
  slots: SlotConfig[],
  rename: { from: string; to: string },
): SlotConfig[] {
  return slots.map((slot) => ({
    ...slot,
    agent: slot.agent === rename.from ? rename.to : slot.agent,
    windows: slot.windows.map((window) => renameWindowAgentReference(window, rename)),
  }));
}

function collectWindowAgents(window: WindowConfig, agents: Set<string>) {
  if (window.agent) agents.add(window.agent);
  for (const child of window.windows ?? []) {
    collectWindowAgents(child, agents);
  }
}

export function collectReferencedAgents(slots: SlotConfig[]): string[] {
  const agents = new Set<string>();
  for (const slot of slots) {
    if (slot.agent) agents.add(slot.agent);
    for (const window of slot.windows) {
      collectWindowAgents(window, agents);
    }
  }
  return [...agents];
}
