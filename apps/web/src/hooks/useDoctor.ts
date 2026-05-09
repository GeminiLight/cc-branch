import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";
import type { WorkspaceScope } from "../types";

export function useDoctor(scope?: WorkspaceScope | string) {
  const api = useApiClient();
  const projectPath = typeof scope === "string" ? scope : scope?.projectPath;
  const configPath = typeof scope === "string" ? undefined : scope?.configPath;
  return useQuery({
    queryKey: ["workspace", "doctor", projectPath, configPath],
    queryFn: ({ signal }) => api.getDoctor(scope, signal),
    enabled: !!projectPath,
    staleTime: 30000,
  });
}
