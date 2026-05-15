import { describe, expect, it } from "vitest";
import { compactPathTail, pathBasename, pathSegments } from "./pathDisplay";

describe("pathDisplay", () => {
  it("splits POSIX and Windows path separators", () => {
    expect(pathSegments("/tmp/demo/.cc-branch/config.yaml")).toEqual(["tmp", "demo", ".cc-branch", "config.yaml"]);
    expect(pathSegments("C:\\work\\demo\\.cc-branch\\config.yaml")).toEqual(["C:", "work", "demo", ".cc-branch", "config.yaml"]);
  });

  it("returns the last path segment as a basename", () => {
    expect(pathBasename("/tmp/demo/.cc-branch/config.yaml")).toBe("config.yaml");
    expect(pathBasename("C:\\work\\demo\\.cc-branch\\config.yaml")).toBe("config.yaml");
  });

  it("compacts long paths using normalized separators", () => {
    expect(compactPathTail("C:\\work\\demo\\.cc-branch\\configs\\review.yaml")).toBe(".cc-branch/configs/review.yaml");
  });
});
