import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { WindowEnabledRequest } from "../types";
import { useApiClient } from "./useApiClient";

export function useWindowEnabled() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: WindowEnabledRequest) => api.setWindowEnabled(request),
    onSuccess: (_, { projectPath, configPath }) => {
      queryClient.invalidateQueries({ queryKey: ["workspace", "status", projectPath, configPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "config", projectPath, configPath] });
      queryClient.invalidateQueries({ queryKey: ["workspace", "doctor", projectPath, configPath] });
    },
  });
}
