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
    mutationFn: ({ content, projectPath }: { content: string; projectPath?: string }) =>
      api.saveConfig(content, projectPath),
    onSuccess: (_, { projectPath }) => {
      queryClient.invalidateQueries({ queryKey: ["workspace", "config", projectPath] });
    },
  });
}
