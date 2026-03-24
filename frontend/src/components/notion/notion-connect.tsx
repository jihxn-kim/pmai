"use client";

import { useNotionStatus, useNotionDisconnect } from "@/hooks/use-notion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface NotionConnectProps {
  orgId: string;
}

export function NotionConnect({ orgId }: NotionConnectProps) {
  const { data: status, isLoading } = useNotionStatus(orgId);
  const disconnect = useNotionDisconnect(orgId);

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">Loading Notion status...</p>
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
            window.location.href = `/api/orgs/${orgId}/notion/auth`;
          }}
        >
          Connect Notion
        </Button>
      </div>
    );
  }

  const handleDisconnect = () => {
    if (!confirm("Notion 연동을 해제하시겠습니까?")) return;
    disconnect.mutate();
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2 flex-wrap">
        <Badge variant="default">연결됨</Badge>
        {status.workspace_id && (
          <span className="text-sm text-muted-foreground">
            워크스페이스 ID: <strong>{status.workspace_id}</strong>
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
