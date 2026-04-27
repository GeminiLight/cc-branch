import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";

export function useDoctor(projectPath?: string) {
  const api = useApiClient();
  return useQuery({
    queryKey: ["workspace", "doctor", projectPath],
    queryFn: ({ signal }) => api.getDoctor(projectPath, signal),
    enabled: !!projectPath,
    staleTime: 30000,
  });
}
