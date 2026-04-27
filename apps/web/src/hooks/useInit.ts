import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";

export function useInitWorkspace() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ profile, bootstrapSessions, projectPath }: { profile: string; bootstrapSessions: boolean; projectPath?: string }) =>
      api.initWorkspace(profile, bootstrapSessions, projectPath),
    onSuccess: (_, { projectPath }) => {
      queryClient.invalidateQueries({ queryKey: ["workspace", "status", projectPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "config", projectPath] });
    },
  });
}
