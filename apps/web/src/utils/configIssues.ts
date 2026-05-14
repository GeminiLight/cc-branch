import type { ConfigIssue } from "../types";

function isCanonicalPublicField(field: string, target: string): boolean {
  if (field === "openWith" || field === "defaults" || field === "tabs") {
    return target === "config";
  }
  if (field === "layoutBackend") {
    return target === "config" || target.startsWith("tab:") || target.startsWith("pane:");
  }
  return false;
}

function isStaleCanonicalSchemaIssue(issue: ConfigIssue): boolean {
  return (
    issue.issue_type === "unknown_field" &&
    typeof issue.context?.field === "string" &&
    isCanonicalPublicField(issue.context.field, issue.target)
  );
}

export function visibleConfigIssues(issues: ConfigIssue[] | undefined | null): ConfigIssue[] {
  return (issues ?? []).filter((issue) => !isStaleCanonicalSchemaIssue(issue));
}
