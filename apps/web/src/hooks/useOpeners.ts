import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";
import type { WorkspaceScope } from "../types";

export function useOpeners(scope?: WorkspaceScope | string, enabled = true) {
  const api = useApiClient();
  const projectPath = typeof scope === "string" ? scope : scope?.projectPath;
  const configPath = typeof scope === "string" ? undefined : scope?.configPath;
  return useQuery({
    queryKey: ["workspace", "openers", projectPath, configPath],
    queryFn: ({ signal }) => api.getOpeners(scope, signal),
    enabled: enabled && !!projectPath,
    staleTime: 30_000,
  });
}
