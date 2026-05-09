import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";
import type { WorkspaceScope } from "../types";

export function useWorkspace(scope?: WorkspaceScope | string, isActive = true) {
  const api = useApiClient();
  const projectPath = typeof scope === "string" ? scope : scope?.projectPath;
  const configPath = typeof scope === "string" ? undefined : scope?.configPath;
  return useQuery({
    queryKey: ["workspace", "status", projectPath, configPath],
    queryFn: ({ signal }) => api.getStatus(scope, signal),
    refetchInterval: isActive ? 2000 : false,
    refetchIntervalInBackground: false,
    enabled: !!projectPath,
    staleTime: 1000,
  });
}
