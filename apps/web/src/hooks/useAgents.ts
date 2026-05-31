import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";
import type { WorkspaceScope } from "../types";

export function useAgents(scope?: WorkspaceScope | string, enabled = true) {
  const api = useApiClient();
  const projectPath = typeof scope === "string" ? scope : scope?.projectPath;
  const configPath = typeof scope === "string" ? undefined : scope?.configPath;
  return useQuery({
    queryKey: ["workspace", "agents", projectPath, configPath],
    queryFn: ({ signal }) => api.getAgents(scope, signal),
    enabled: enabled && !!projectPath,
    staleTime: 30000,
  });
}
