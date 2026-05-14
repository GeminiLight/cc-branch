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

  it("keeps horizontal panes readable on narrow canvases", () => {
    expect(workspacePaneGridStyle({ layout: "horizontal" }, 2)).toMatchObject({
      gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 220px), 1fr))",
    });
  });
});
