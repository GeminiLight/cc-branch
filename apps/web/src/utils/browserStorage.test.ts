import { afterEach, describe, expect, it, vi } from "vitest";
import { getLocalStorageItem, setLocalStorageItem } from "./browserStorage";

describe("browserStorage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("reads and writes localStorage when available", () => {
    expect(setLocalStorageItem("cc-branch-test", "ok")).toBe(true);
    expect(getLocalStorageItem("cc-branch-test")).toBe("ok");
  });

  it("returns null when storage reads are blocked", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("storage blocked");
    });

    expect(getLocalStorageItem("cc-branch-test")).toBeNull();
  });

  it("returns false when storage writes are blocked", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("storage blocked");
    });

    expect(setLocalStorageItem("cc-branch-test", "ok")).toBe(false);
  });
});
