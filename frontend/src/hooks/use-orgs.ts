import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export function useOrgs() {
  return useQuery({
    queryKey: ["orgs"],
    queryFn: () => api.get("/api/orgs").then(r => r.data),
  });
}

export function useOrgDashboard(orgId: string) {
  return useQuery({
    queryKey: ["org-dashboard", orgId],
    queryFn: () => api.get(`/api/orgs/${orgId}/dashboard`).then(r => r.data),
    enabled: !!orgId,
  });
}

export function useOrgMembers(orgId: string) {
  return useQuery({
    queryKey: ["org-members", orgId],
    queryFn: () => api.get(`/api/orgs/${orgId}/members`).then(r => r.data),
    enabled: !!orgId,
  });
}
