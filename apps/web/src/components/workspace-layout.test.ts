import { describe, expect, it } from "vitest";
import {
  normalizeWorkspaceLayout,
  workspacePaneCellStyle,
  workspacePaneGridStyle,
} from "./workspace-layout";

describe("workspace layout", () => {
  it("uses one automatic layout rule for dashboard and config previews", () => {
    expect(normalizeWorkspaceLayout({}, 1)).toBe("horizontal");
    expect(normalizeWorkspaceLayout({}, 2)).toBe("horizontal");
    expect(normalizeWorkspaceLayout({}, 3)).toBe("main-left");
    expect(normalizeWorkspaceLayout({}, 4)).toBe("grid");
  });

  it("supports main-top in shared grid and cell styles", () => {
    expect(workspacePaneGridStyle({ layout: "main-top" }, 3)).toMatchObject({
      gridTemplateColumns: "repeat(2, minmax(112px, 1fr))",
      gridTemplateRows: "minmax(82px, 1.04fr) minmax(68px, 0.96fr)",
    });
    expect(workspacePaneCellStyle({ layout: "main-top" }, 3, 0)).toEqual({
      gridColumn: "1 / span 2",
    });
    expect(workspacePaneCellStyle({ layout: "main-top" }, 3, 1)).toEqual({});
  });

  it("keeps two auto panes side by side in constrained canvases", () => {
    expect(workspacePaneGridStyle({ layout: "auto" }, 2)).toEqual({
      gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
    });
  });

  it("keeps explicit horizontal panes side by side", () => {
    expect(workspacePaneGridStyle({ layout: "horizontal" }, 3)).toEqual({
      gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
    });
  });
});
