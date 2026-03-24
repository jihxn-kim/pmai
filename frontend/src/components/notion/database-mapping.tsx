"use client";

import { useState, useEffect } from "react";
import {
  useNotionSyncStatus,
  useSetNotionDatabase,
  useTriggerNotionSync,
} from "@/hooks/use-notion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface DatabaseMappingProps {
  projectId: string;
}

export function DatabaseMapping({ projectId }: DatabaseMappingProps) {
  const { data: syncStatus, isLoading } = useNotionSyncStatus(projectId);
  const setDatabase = useSetNotionDatabase(projectId);
  const triggerSync = useTriggerNotionSync(projectId);

  const [dbId, setDbId] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (syncStatus?.notion_database_id) {
      setDbId(syncStatus.notion_database_id);
    }
  }, [syncStatus?.notion_database_id]);

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">Loading Notion database status...</p>
    );
  }

  const handleConnect = (e: React.FormEvent) => {
    e.preventDefault();
    if (!dbId.trim()) return;
    setDatabase.mutate(dbId.trim(), {
      onSuccess: () => {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      },
    });
  };

  const handleDisconnect = () => {
    if (!confirm("Notion 데이터베이스 연결을 해제하시겠습니까?")) return;
    setDatabase.mutate("", {
      onSuccess: () => {
        setDbId("");
      },
    });
  };

  const handleManualSync = () => {
    triggerSync.mutate();
  };

  const isMapped = !!syncStatus?.notion_database_id;

  return (
    <div className="flex flex-col gap-4">
      {isMapped ? (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="default">연결됨</Badge>
            <span className="text-sm text-muted-foreground">
              DB ID: <strong>{syncStatus.notion_database_id}</strong>
            </span>
          </div>

          {syncStatus?.last_synced_at && (
            <p className="text-xs text-muted-foreground">
              마지막 동기화:{" "}
              {new Date(syncStatus.last_synced_at).toLocaleString("ko-KR")}
            </p>
          )}

          <div className="flex gap-2 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              onClick={handleManualSync}
              disabled={triggerSync.isPending}
            >
              {triggerSync.isPending ? "동기화 중..." : "수동 동기화"}
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDisconnect}
              disabled={setDatabase.isPending}
            >
              {setDatabase.isPending ? "해제 중..." : "연결 해제"}
            </Button>
          </div>

          {triggerSync.isSuccess && (
            <p className="text-sm text-green-600">동기화가 시작되었습니다.</p>
          )}
          {triggerSync.isError && (
            <p className="text-sm text-destructive">동기화에 실패했습니다.</p>
          )}
        </div>
      ) : (
        <form onSubmit={handleConnect} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="notion-db-id">Notion Database ID</Label>
            <div className="flex gap-2">
              <Input
                id="notion-db-id"
                value={dbId}
                onChange={(e) => setDbId(e.target.value)}
                placeholder="예: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                className="flex-1"
              />
              <Button
                type="submit"
                size="sm"
                disabled={setDatabase.isPending || !dbId.trim()}
              >
                {setDatabase.isPending ? "연결 중..." : "연결"}
              </Button>
            </div>
          </div>
          {saved && (
            <p className="text-sm text-green-600">데이터베이스가 연결되었습니다.</p>
          )}
          {setDatabase.isError && (
            <p className="text-sm text-destructive">연결에 실패했습니다.</p>
          )}
        </form>
      )}
    </div>
  );
}
