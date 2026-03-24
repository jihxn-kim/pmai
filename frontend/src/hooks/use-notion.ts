"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export function useNotionStatus(orgId: string) {
  return useQuery({
    queryKey: ["notion-status", orgId],
    queryFn: () => api.get(`/api/orgs/${orgId}/notion/status`).then(r => r.data),
    enabled: !!orgId,
  });
}

export function useNotionDisconnect(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.delete(`/api/orgs/${orgId}/notion/disconnect`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notion-status", orgId] }),
  });
}

export function useSetNotionDatabase(projectId: string) {
  return useMutation({
    mutationFn: (dbId: string) =>
      api.post(`/api/projects/${projectId}/notion/database`, { notion_database_id: dbId }),
  });
}

export function useNotionSyncStatus(projectId: string) {
  return useQuery({
    queryKey: ["notion-sync-status", projectId],
    queryFn: () =>
      api.get(`/api/projects/${projectId}/notion/sync-status`).then(r => r.data),
    enabled: !!projectId,
  });
}

export function useTriggerNotionSync(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post(`/api/projects/${projectId}/notion/sync`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["notion-sync-status", projectId] }),
  });
}
