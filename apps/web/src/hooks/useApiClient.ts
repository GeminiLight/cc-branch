import { createClient } from "../api/client";

let singleton: ReturnType<typeof createClient> | null = null;

export function useApiClient() {
  if (!singleton) {
    singleton = createClient();
  }
  return singleton;
}
