"use client";

import { useState, useEffect } from "react";
import { useSlackStatus, useSlackDisconnect, useSetOrgChannel } from "@/hooks/use-slack";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface SlackConnectProps {
  orgId: string;
}

export function SlackConnect({ orgId }: SlackConnectProps) {
  const { data: status, isLoading } = useSlackStatus(orgId);
  const disconnect = useSlackDisconnect(orgId);
  const setOrgChannel = useSetOrgChannel(orgId);

  const [channelId, setChannelId] = useState("");
  const [channelSaved, setChannelSaved] = useState(false);

  useEffect(() => {
    if (status?.org_channel_id) {
      setChannelId(status.org_channel_id);
    }
  }, [status?.org_channel_id]);

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">Loading Slack status...</p>
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
            window.location.href = `/api/orgs/${orgId}/slack/auth`;
          }}
        >
          Connect Slack
        </Button>
      </div>
    );
  }

  const handleSaveChannel = (e: React.FormEvent) => {
    e.preventDefault();
    if (!channelId.trim()) return;
    setOrgChannel.mutate(channelId.trim(), {
      onSuccess: () => {
        setChannelSaved(true);
        setTimeout(() => setChannelSaved(false), 3000);
      },
    });
  };

  const handleDisconnect = () => {
    if (!confirm("Slack 연동을 해제하시겠습니까?")) return;
    disconnect.mutate();
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2 flex-wrap">
        <Badge variant="default">연결됨</Badge>
        {status.team_id && (
          <span className="text-sm text-muted-foreground">
            워크스페이스: <strong>{status.team_id}</strong>
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

      <form onSubmit={handleSaveChannel} className="flex flex-col gap-2">
        <Label htmlFor="org-channel-id">조직 기본 채널 ID</Label>
        <div className="flex gap-2">
          <Input
            id="org-channel-id"
            value={channelId}
            onChange={(e) => setChannelId(e.target.value)}
            placeholder="예: C0123456789"
            className="flex-1"
          />
          <Button
            type="submit"
            size="sm"
            disabled={setOrgChannel.isPending || !channelId.trim()}
          >
            {setOrgChannel.isPending ? "저장 중..." : "저장"}
          </Button>
        </div>
        {channelSaved && (
          <p className="text-sm text-green-600">채널이 저장되었습니다.</p>
        )}
        {setOrgChannel.isError && (
          <p className="text-sm text-destructive">저장에 실패했습니다.</p>
        )}
      </form>
    </div>
  );
}
