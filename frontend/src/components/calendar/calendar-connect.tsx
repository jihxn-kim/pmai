"use client";

import { useCalendarStatus, useCalendarDisconnect } from "@/hooks/use-calendar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function CalendarConnect() {
  const { data: status, isLoading } = useCalendarStatus();
  const disconnect = useCalendarDisconnect();

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">Loading Google Calendar status...</p>
    );
  }

  if (!status?.connected) {
    return (
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Badge variant="outline">연결 안됨</Badge>
        </div>
        <Button
          variant="default"
          onClick={() => {
            window.location.href = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/calendar/auth`;
          }}
        >
          Connect Google Calendar
        </Button>
      </div>
    );
  }

  const handleDisconnect = () => {
    if (!confirm("Google Calendar 연동을 해제하시겠습니까?")) return;
    disconnect.mutate();
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2 flex-wrap">
        <Badge variant="default">연결됨</Badge>
        {status.email && (
          <span className="text-sm text-muted-foreground">
            계정: <strong>{status.email}</strong>
          </span>
        )}
        <Button
          variant="destructive"
          size="sm"
          onClick={handleDisconnect}
          disabled={disconnect.isPending}
        >
          {disconnect.isPending ? "해제 중..." : "연결 해제"}
        </Button>
      </div>
    </div>
  );
}
