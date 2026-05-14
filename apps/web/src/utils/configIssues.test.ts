import { describe, expect, it } from "vitest";
import type { ConfigIssue } from "../types";
import { visibleConfigIssues } from "./configIssues";

function issue(field: string, target = "config"): ConfigIssue {
  return {
    issue_type: "unknown_field",
    severity: "warning",
    message: `Unknown field '${field}'`,
    target,
    context: { field },
    fixable: false,
  };
}

describe("visibleConfigIssues", () => {
  it("hides stale unknown-field warnings only where the canonical v2 fields are valid", () => {
    expect(visibleConfigIssues([
      issue("openWith", "config"),
      issue("defaults", "config"),
      issue("tabs", "config"),
      issue("layoutBackend", "config"),
      issue("layoutBackend", "tab:dev"),
      issue("layoutBackend", "pane:dev:api"),
      issue("stillWrong", "config"),
    ])).toEqual([issue("stillWrong", "config")]);
  });

  it("keeps same-name unknown fields when they appear in invalid sections", () => {
    expect(visibleConfigIssues([
      issue("openWith", "agent:codex"),
      issue("layoutBackend", "agent:codex"),
      issue("tabs", "pane:dev:api"),
      issue("defaults", "window:dev:api"),
    ])).toEqual([
      issue("openWith", "agent:codex"),
      issue("layoutBackend", "agent:codex"),
      issue("tabs", "pane:dev:api"),
      issue("defaults", "window:dev:api"),
    ]);
  });
});
