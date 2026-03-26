import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface SlackStatus {
  connected: boolean;
  team_id?: string;
  org_channel_id?: string;
}

export interface SlackUserMapping {
  id: string;
  user_id: string;
  slack_user_id: string;
}

// ── Queries ────────────────────────────────────────────────────────────────

export function useSlackStatus(orgId: string) {
  return useQuery<SlackStatus>({
    queryKey: ["slack-status", orgId],
    queryFn: () =>
      api.get(`/api/orgs/${orgId}/slack/status`).then((r) => r.data),
    enabled: !!orgId,
  });
}

export function useSlackUserMappings(orgId: string) {
  return useQuery<SlackUserMapping[]>({
    queryKey: ["slack-user-mappings", orgId],
    queryFn: () =>
      api.get(`/api/orgs/${orgId}/slack/user-mappings`).then((r) => r.data),
    enabled: !!orgId,
  });
}

// ── Mutations ──────────────────────────────────────────────────────────────

export function useSlackDisconnect(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api.delete(`/api/orgs/${orgId}/slack`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["slack-status", orgId] });
    },
  });
}

export function useSetOrgChannel(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (channelId: string) =>
      api
        .patch(`/api/orgs/${orgId}/slack/channel`, { channel_id: channelId })
        .then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["slack-status", orgId] });
    },
  });
}

export function useSetProjectChannel(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (channelId: string) =>
      api
        .post(`/api/projects/${projectId}/slack/channel`, {
          channel_id: channelId,
        })
        .then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["project-slack-channel", projectId],
      });
    },
  });
}

export function useAddUserMapping(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { user_id: string; slack_user_id: string }) =>
      api
        .post(`/api/orgs/${orgId}/slack/user-mappings`, data)
        .then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["slack-user-mappings", orgId],
      });
    },
  });
}
