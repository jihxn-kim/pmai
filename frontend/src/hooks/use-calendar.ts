"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export function useCalendarStatus() {
  return useQuery({
    queryKey: ["calendar-status"],
    queryFn: () => api.get("/api/users/me/calendar/status").then(r => r.data),
  });
}

export function useCalendarDisconnect() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.delete("/api/users/me/calendar/disconnect"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calendar-status"] }),
  });
}
