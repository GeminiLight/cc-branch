import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { WorkspaceActionRequest } from "../types";
import { useApiClient } from "./useApiClient";

export function useWorkspaceAction() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      action,
      target,
      opener,
      intent,
      projectPath,
      configPath,
      stopRemoved,
    }: WorkspaceActionRequest) =>
      api.runWorkspaceAction({ action, target, opener, intent, projectPath, configPath, stopRemoved }),
    onSuccess: (_, { projectPath, configPath }) => {
      queryClient.invalidateQueries({ queryKey: ["workspace", "status", projectPath, configPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "doctor", projectPath, configPath] });
    },
  });
}
