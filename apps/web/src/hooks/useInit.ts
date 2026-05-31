import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";
import type { WorkspaceScope } from "../types";

function scopeParts(scope?: WorkspaceScope | string) {
  return {
    projectPath: typeof scope === "string" ? scope : scope?.projectPath,
    configPath: typeof scope === "string" ? undefined : scope?.configPath,
  };
}

export function useInitWorkspace() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ profile, bootstrapSessions, projectPath, configPath }: { profile: string; bootstrapSessions: boolean; projectPath?: string; configPath?: string }) =>
      api.initWorkspace(profile, bootstrapSessions, { projectPath, configPath }),
    onSuccess: (_, { projectPath, configPath }) => {
      const scope = scopeParts({ projectPath, configPath });
      queryClient.invalidateQueries({ queryKey: ["workspace", "status", scope.projectPath, scope.configPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "config", scope.projectPath, scope.configPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "configs", scope.projectPath] });
    },
  });
}
