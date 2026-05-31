import { describe, expect, it } from "vitest";
import { appTabFromHash, appTabFromSearch, appTabFromUrl, appTabHash } from "./tabRoute";

describe("tabRoute", () => {
  it("parses supported app tab hashes", () => {
    expect(appTabFromHash("#workspace")).toBe("workspace");
    expect(appTabFromHash("project")).toBe("project");
    expect(appTabFromHash("#doctor")).toBe("doctor");
  });

  it("keeps old config hashes usable", () => {
    expect(appTabFromHash("#config")).toBe("project");
    expect(appTabFromHash("#project-config")).toBe("project");
  });

  it("parses tab query parameters for direct links", () => {
    expect(appTabFromSearch("?tab=workspace")).toBe("workspace");
    expect(appTabFromSearch("?project_path=/tmp/demo&tab=project-config")).toBe("project");
    expect(appTabFromSearch("?tab=unknown")).toBeNull();
  });

  it("prefers hash routes over query routes", () => {
    expect(appTabFromUrl("#doctor", "?tab=workspace")).toBe("doctor");
    expect(appTabFromUrl("", "?tab=workspace")).toBe("workspace");
  });

  it("ignores empty or unknown hashes", () => {
    expect(appTabFromHash("")).toBeNull();
    expect(appTabFromHash("#unknown")).toBeNull();
  });

  it("uses a clean URL for the dashboard", () => {
    expect(appTabHash("dashboard")).toBe("");
    expect(appTabHash("workspace")).toBe("#workspace");
  });
});
