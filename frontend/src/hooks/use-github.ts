import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export function usePulls(projectId: string) {
  return useQuery({
    queryKey: ["pulls", projectId],
    queryFn: () =>
      api.get(`/api/projects/${projectId}/pulls`).then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useActivity(projectId: string) {
  return useQuery({
    queryKey: ["activity", projectId],
    queryFn: () =>
      api.get(`/api/projects/${projectId}/activity`).then((r) => r.data),
    enabled: !!projectId,
  });
}
