import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";

export function useOpeners(projectPath?: string, enabled = true) {
  const api = useApiClient();
  return useQuery({
    queryKey: ["workspace", "openers", projectPath],
    queryFn: ({ signal }) => api.getOpeners(projectPath, signal),
    enabled,
    staleTime: 30_000,
  });
}
