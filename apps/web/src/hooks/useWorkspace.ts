import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";

export function useWorkspace(projectPath?: string, isActive = true) {
  const api = useApiClient();
  return useQuery({
    queryKey: ["workspace", "status", projectPath],
    queryFn: ({ signal }) => api.getStatus(projectPath, signal),
    refetchInterval: isActive ? 2000 : false,
    refetchIntervalInBackground: false,
    enabled: !!projectPath,
    staleTime: 1000,
  });
}
