import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "./useApiClient";

export function useProfiles() {
  const api = useApiClient();
  return useQuery({
    queryKey: ["profiles"],
    queryFn: ({ signal }) => api.getProfiles(signal),
    staleTime: 60000,
  });
}
