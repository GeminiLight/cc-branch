export type AppTab = "dashboard" | "workspace" | "project" | "doctor";

const VALID_TABS: AppTab[] = ["dashboard", "workspace", "project", "doctor"];
const HASH_ALIASES: Record<string, AppTab> = {
  config: "project",
  "project-config": "project",
};

function appTabFromRaw(value: string): AppTab | null {
  const raw = value.trim().toLowerCase();
  if (!raw) return null;
  if (raw in HASH_ALIASES) return HASH_ALIASES[raw];
  return VALID_TABS.includes(raw as AppTab) ? (raw as AppTab) : null;
}

export function appTabFromHash(hash: string): AppTab | null {
  return appTabFromRaw(hash.replace(/^#/, ""));
}

export function appTabFromSearch(search: string): AppTab | null {
  return appTabFromRaw(new URLSearchParams(search).get("tab") || "");
}

export function appTabFromUrl(hash: string, search: string): AppTab | null {
  return appTabFromHash(hash) || appTabFromSearch(search);
}

export function appTabHash(tab: AppTab): string {
  return tab === "dashboard" ? "" : `#${tab}`;
}
