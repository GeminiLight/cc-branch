export type AppTab = "dashboard" | "workspace" | "project" | "doctor";

const VALID_TABS: AppTab[] = ["dashboard", "workspace", "project", "doctor"];
const HASH_ALIASES: Record<string, AppTab> = {
  config: "project",
  "project-config": "project",
};

export function appTabFromHash(hash: string): AppTab | null {
  const raw = hash.replace(/^#/, "").trim().toLowerCase();
  if (!raw) return null;
  if (raw in HASH_ALIASES) return HASH_ALIASES[raw];
  return VALID_TABS.includes(raw as AppTab) ? (raw as AppTab) : null;
}

export function appTabHash(tab: AppTab): string {
  return tab === "dashboard" ? "" : `#${tab}`;
}
