import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";

export function useStopSlot() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionName, projectPath }: { sessionName: string; projectPath?: string }) =>
      api.runAction("stop", sessionName, projectPath),
    onSuccess: (_, { projectPath }) => {
      queryClient.invalidateQueries({ queryKey: ["workspace", "status", projectPath] });
    },
  });
}
