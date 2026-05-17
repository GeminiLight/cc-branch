import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";

export function useApiInfo() {
  const api = useApiClient();

  return useQuery({
    queryKey: ["api", "info"],
    queryFn: ({ signal }) => api.getApiInfo(signal),
    staleTime: 300000,
  });
}
