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
      stopRemoved,
    }: WorkspaceActionRequest) =>
      api.runWorkspaceAction({ action, target, opener, intent, projectPath, stopRemoved }),
    onSuccess: (_, { projectPath }) => {
      queryClient.invalidateQueries({ queryKey: ["workspace", "status", projectPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "doctor", projectPath] });
    },
  });
}
