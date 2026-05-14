import type { CSSProperties } from "react";

export type WorkspaceLayout =
  | "horizontal"
  | "vertical"
  | "main-left"
  | "main-top"
  | "grid";

type LayoutOwner = {
  layout?: string | null;
};

export function normalizeWorkspaceLayout(slot: LayoutOwner, paneLength: number): WorkspaceLayout {
  const layout = slot.layout;
  if (
    layout === "horizontal" ||
    layout === "vertical" ||
    layout === "main-left" ||
    layout === "main-top" ||
    layout === "grid"
  ) {
    return layout;
  }
  if (paneLength <= 2) return "horizontal";
  if (paneLength === 3) return "main-left";
  return "grid";
}

export function workspacePaneGridStyle(slot: LayoutOwner, paneLength: number): CSSProperties {
  const count = Math.max(paneLength, 1);
  const layout = normalizeWorkspaceLayout(slot, count);
  if (count === 1) return { gridTemplateColumns: "minmax(0, 1fr)" };
  if (layout === "vertical") {
    return { gridTemplateRows: `repeat(${count}, minmax(72px, 1fr))` };
  }
  if (layout === "main-left") {
    return {
      gridTemplateColumns: "minmax(150px, 1.18fr) minmax(116px, 0.82fr)",
      gridTemplateRows: `repeat(${Math.max(count - 1, 1)}, minmax(70px, 1fr))`,
    };
  }
  if (layout === "main-top") {
    return {
      gridTemplateColumns: `repeat(${Math.max(count - 1, 1)}, minmax(112px, 1fr))`,
      gridTemplateRows: "minmax(82px, 1.04fr) minmax(68px, 0.96fr)",
    };
  }
  if (layout === "grid") {
    const columns = count <= 4 ? 2 : 3;
    return { gridTemplateColumns: `repeat(${columns}, minmax(112px, 1fr))` };
  }
  return { gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 220px), 1fr))" };
}

export function workspacePaneCellStyle(
  slot: LayoutOwner,
  paneLength: number,
  index: number,
): CSSProperties {
  const count = Math.max(paneLength, 1);
  const layout = normalizeWorkspaceLayout(slot, count);
  if (index !== 0 || count <= 1) return {};
  if (layout === "main-left") return { gridRow: `1 / span ${Math.max(count - 1, 1)}` };
  if (layout === "main-top") return { gridColumn: `1 / span ${Math.max(count - 1, 1)}` };
  return {};
}
