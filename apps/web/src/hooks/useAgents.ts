import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";

export function useAgents(projectPath?: string, enabled = true) {
  const api = useApiClient();
  return useQuery({
    queryKey: ["workspace", "agents", projectPath],
    queryFn: ({ signal }) => api.getAgents(projectPath, signal),
    enabled: enabled && !!projectPath,
    staleTime: 30000,
  });
}
