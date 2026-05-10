import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";
import type { WorkspaceScope } from "../types";

export function useAgentSessions(scope?: WorkspaceScope | string, enabled = true) {
  const api = useApiClient();
  const projectPath = typeof scope === "string" ? scope : scope?.projectPath;
  const configPath = typeof scope === "string" ? undefined : scope?.configPath;
  return useQuery({
    queryKey: ["workspace", "agent-sessions", projectPath, configPath],
    queryFn: ({ signal }) => api.getAgentSessions(scope, undefined, signal),
    enabled: enabled && !!projectPath,
    staleTime: 30000,
  });
}
