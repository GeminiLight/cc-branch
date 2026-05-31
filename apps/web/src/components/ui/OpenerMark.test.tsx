import { describe, expect, it } from "vitest";
import warpIconUrl from "../../assets/opener-icons/warp.png";

describe("OpenerMark assets", () => {
  it("uses the official Warp app icon image rather than the old custom SVG", () => {
    expect(warpIconUrl).toContain("warp.png");
  });
});
