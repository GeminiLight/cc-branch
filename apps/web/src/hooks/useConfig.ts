import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";

export function useConfig(projectPath?: string) {
  const api = useApiClient();
  return useQuery({
    queryKey: ["workspace", "config", projectPath],
    queryFn: ({ signal }) => api.getConfig(projectPath, signal),
    enabled: !!projectPath,
    staleTime: 30000,
  });
}

export function useSaveConfig() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      content,
      projectPath,
      baseMtime,
      baseContentHash,
    }: {
      content: string;
      projectPath?: string;
      baseMtime?: number | null;
      baseContentHash?: string | null;
    }) => api.saveConfig(content, projectPath, baseMtime, baseContentHash),
    onSuccess: (_, { projectPath }) => {
      queryClient.invalidateQueries({ queryKey: ["workspace", "config", projectPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "agents", projectPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "status", projectPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "doctor", projectPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "openers", projectPath] });
    },
  });
}
