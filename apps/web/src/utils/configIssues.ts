import type { ConfigIssue } from "../types";

const PUBLIC_SCHEMA_FIELDS = new Set(["openWith", "layoutBackend", "defaults", "tabs"]);

function isStaleCanonicalSchemaIssue(issue: ConfigIssue): boolean {
  return (
    issue.issue_type === "unknown_field" &&
    typeof issue.context?.field === "string" &&
    PUBLIC_SCHEMA_FIELDS.has(issue.context.field)
  );
}

export function visibleConfigIssues(issues: ConfigIssue[] | undefined | null): ConfigIssue[] {
  return (issues ?? []).filter((issue) => !isStaleCanonicalSchemaIssue(issue));
}
