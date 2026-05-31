import { describe, expect, it } from "vitest";
import { visibleProjectsFromIndex } from "./projects";

describe("visibleProjectsFromIndex", () => {
  it("keeps a persisted current project in desktop project indexes", () => {
    const projects = [
      {
        id: "current",
        name: "cli-workspace",
        path: "/Users/geminilight/code/cli-workspace",
        selected_config_path: "/Users/geminilight/code/cli-workspace/.cc-branch/config.yaml",
      },
      {
        id: "proj_1",
        name: "research-projects",
        path: "/Users/geminilight/code/research-projects",
      },
    ];

    expect(visibleProjectsFromIndex(projects)).toEqual(projects);
  });
});
