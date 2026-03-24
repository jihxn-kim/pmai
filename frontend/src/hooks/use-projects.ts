import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export function useProject(projectId: string) {
  return useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.get(`/api/projects/${projectId}`).then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useProjectMembers(projectId: string) {
  return useQuery({
    queryKey: ["project-members", projectId],
    queryFn: () =>
      api.get(`/api/projects/${projectId}/members`).then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useProjectProgress(projectId: string) {
  return useQuery({
    queryKey: ["project-progress", projectId],
    queryFn: () =>
      api.get(`/api/projects/${projectId}/progress`).then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useProjectIssues(projectId: string) {
  return useQuery({
    queryKey: ["project-issues", projectId],
    queryFn: () =>
      api.get(`/api/projects/${projectId}/issues`).then((r) => r.data),
    enabled: !!projectId,
  });
}
