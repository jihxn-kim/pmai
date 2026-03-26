"use client";

import { useState, useEffect } from "react";
import { useSlackStatus, useSlackDisconnect, useSetOrgChannel, useSlackChannels } from "@/hooks/use-slack";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import api from "@/lib/api";
import { Hash, Loader2 } from "lucide-react";

interface SlackConnectProps {
  orgId: string;
}

export function SlackConnect({ orgId }: SlackConnectProps) {
  const { data: status, isLoading } = useSlackStatus(orgId);
  const disconnect = useSlackDisconnect(orgId);
  const setOrgChannel = useSetOrgChannel(orgId);
  const { data: channels, isLoading: channelsLoading } = useSlackChannels(orgId, !!status?.connected);

  const [selectedChannel, setSelectedChannel] = useState("");
  const [channelSaved, setChannelSaved] = useState(false);

  useEffect(() => {
    if (status?.org_channel_id) {
      setSelectedChannel(status.org_channel_id);
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
          onClick={async () => {
            try {
              const { data } = await api.get(`/api/orgs/${orgId}/slack/auth`);
              window.location.href = data.url;
            } catch {
              // auth error handled by interceptor
            }
          }}
        >
          Slack 연결
        </Button>
      </div>
    );
  }

  const handleSaveChannel = () => {
    if (!selectedChannel) return;
    setOrgChannel.mutate(selectedChannel, {
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

  const currentChannelName = channels?.find((c) => c.id === status.org_channel_id)?.name;

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

      <div className="flex flex-col gap-2">
        <Label>알림 채널</Label>
        {currentChannelName && !channelSaved && (
          <p className="text-xs text-muted-foreground">
            현재: <strong>#{currentChannelName}</strong>
          </p>
        )}
        <div className="flex gap-2">
          {channelsLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              채널 목록 로딩 중...
            </div>
          ) : (
            <>
              <Select value={selectedChannel} onValueChange={(v) => setSelectedChannel(v ?? "")}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="채널 선택..." />
                </SelectTrigger>
                <SelectContent>
                  {channels?.map((ch) => (
                    <SelectItem key={ch.id} value={ch.id}>
                      <div className="flex items-center gap-1.5">
                        <Hash className="size-3.5 text-muted-foreground" />
                        {ch.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                size="sm"
                onClick={handleSaveChannel}
                disabled={setOrgChannel.isPending || !selectedChannel}
              >
                {setOrgChannel.isPending ? "저장 중..." : "저장"}
              </Button>
            </>
          )}
        </div>
        {channelSaved && (
          <p className="text-sm text-green-600">채널이 저장되었습니다.</p>
        )}
        {setOrgChannel.isError && (
          <p className="text-sm text-destructive">저장에 실패했습니다.</p>
        )}
      </div>
    </div>
  );
}
