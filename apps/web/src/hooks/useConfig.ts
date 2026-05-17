import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";
import type { WorkspaceScope } from "../types";

function scopeParts(scope?: WorkspaceScope | string) {
  return {
    projectPath: typeof scope === "string" ? scope : scope?.projectPath,
    configPath: typeof scope === "string" ? undefined : scope?.configPath,
  };
}

export function useConfig(scope?: WorkspaceScope | string) {
  const api = useApiClient();
  const { projectPath, configPath } = scopeParts(scope);
  return useQuery({
    queryKey: ["workspace", "config", projectPath, configPath],
    queryFn: ({ signal }) => api.getConfig(scope, signal),
    enabled: !!projectPath,
    staleTime: 30000,
  });
}

export function useConfigOptions(scope?: WorkspaceScope | string) {
  const api = useApiClient();
  const { projectPath, configPath } = scopeParts(scope);
  return useQuery({
    queryKey: ["workspace", "configs", projectPath, configPath],
    queryFn: ({ signal }) => api.getConfigs(scope, signal),
    enabled: !!projectPath,
    staleTime: 5000,
  });
}

export function useSaveConfig() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      content,
      scope,
      baseMtime,
      baseContentHash,
    }: {
      content: string;
      scope?: WorkspaceScope | string;
      baseMtime?: number | null;
      baseContentHash?: string | null;
    }) => api.saveConfig(content, scope, baseMtime, baseContentHash),
    onSuccess: (_, { scope }) => {
      const { projectPath, configPath } = scopeParts(scope);
      queryClient.invalidateQueries({ queryKey: ["workspace", "config", projectPath, configPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "configs", projectPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "agents", projectPath, configPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "status", projectPath, configPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "doctor", projectPath, configPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "openers", projectPath, configPath] });
    },
  });
}
