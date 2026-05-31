import { describe, expect, it } from "vitest";
import { projectDirFromConfigPath } from "./projectPath";

describe("projectDirFromConfigPath", () => {
  it("handles the current .cc-branch/config.yaml layout", () => {
    expect(projectDirFromConfigPath("/tmp/demo/.cc-branch/config.yaml")).toBe("/tmp/demo");
  });

  it("handles Windows paths", () => {
    expect(projectDirFromConfigPath("C:\\work\\demo\\.cc-branch\\config.yaml")).toBe("C:\\work\\demo");
  });

  it("falls back to the parent directory for custom config filenames", () => {
    expect(projectDirFromConfigPath("/tmp/demo/custom.yaml")).toBe("/tmp/demo");
  });
});
