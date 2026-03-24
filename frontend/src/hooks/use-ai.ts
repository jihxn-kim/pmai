"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export function useAIReviews(projectId: string) {
  return useQuery({
    queryKey: ["ai-reviews", projectId],
    queryFn: () => api.get(`/api/projects/${projectId}/ai/reviews`).then(r => r.data),
    enabled: !!projectId,
  });
}

export function useAIReview(projectId: string, reviewId: string) {
  return useQuery({
    queryKey: ["ai-review", projectId, reviewId],
    queryFn: () => api.get(`/api/projects/${projectId}/ai/reviews/${reviewId}`).then(r => r.data),
    enabled: !!projectId && !!reviewId,
  });
}

export function useAIJobStatus(jobId: string | null) {
  return useQuery({
    queryKey: ["ai-job", jobId],
    queryFn: () => api.get(`/api/ai/jobs/${jobId}`).then(r => r.data),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 3000;
    },
  });
}

export function useRequestAnalysis(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post(`/api/projects/${projectId}/ai/analyze`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-reviews", projectId] }),
  });
}

export function useRequestReview(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (prNumber: number) => api.post(`/api/projects/${projectId}/ai/review/${prNumber}`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-reviews", projectId] }),
  });
}

export function useRequestTestScenarios(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { pr_number?: number; file_paths?: string[] }) =>
      api.post(`/api/projects/${projectId}/ai/test-scenarios`, body).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-reviews", projectId] }),
  });
}

export function useBriefings(orgId: string) {
  return useQuery({
    queryKey: ["briefings", orgId],
    queryFn: () => api.get(`/api/orgs/${orgId}/briefings`).then(r => r.data),
    enabled: !!orgId,
  });
}

export function useLatestBriefing(orgId: string) {
  return useQuery({
    queryKey: ["briefing-latest", orgId],
    queryFn: () => api.get(`/api/orgs/${orgId}/briefings/latest`).then(r => r.data),
    enabled: !!orgId,
    retry: false,
  });
}

export function useGenerateBriefing(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post(`/api/orgs/${orgId}/briefings/generate`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["briefings", orgId] }),
  });
}
