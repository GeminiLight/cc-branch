import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";
import type { WorkspaceScope } from "../types";

export function useStopSlot() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionName, projectPath, configPath }: { sessionName: string; projectPath?: string; configPath?: string }) =>
      api.runAction("stop", sessionName, { projectPath, configPath } satisfies WorkspaceScope),
    onSuccess: (_, { projectPath, configPath }) => {
      queryClient.invalidateQueries({ queryKey: ["workspace", "status", projectPath, configPath] });
    },
  });
}
