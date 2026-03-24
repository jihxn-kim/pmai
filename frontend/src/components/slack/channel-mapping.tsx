"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSetProjectChannel } from "@/hooks/use-slack";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import api from "@/lib/api";

interface ProjectSlackChannel {
  channel_id?: string;
}

interface ChannelMappingProps {
  projectId: string;
}

export function ChannelMapping({ projectId }: ChannelMappingProps) {
  const { data, isLoading, refetch } = useQuery<ProjectSlackChannel>({
    queryKey: ["project-slack-channel", projectId],
    queryFn: () =>
      api
        .get(`/api/projects/${projectId}/slack/channel`)
        .then((r) => r.data)
        .catch(() => ({ channel_id: undefined })),
    enabled: !!projectId,
  });

  const setChannel = useSetProjectChannel(projectId);
  const [channelInput, setChannelInput] = useState("");

  const handleConnect = (e: React.FormEvent) => {
    e.preventDefault();
    if (!channelInput.trim()) return;
    setChannel.mutate(channelInput.trim(), {
      onSuccess: () => {
        setChannelInput("");
        refetch();
      },
    });
  };

  const handleDisconnect = () => {
    setChannel.mutate("", {
      onSuccess: () => {
        refetch();
      },
    });
  };

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">로딩 중...</p>;
  }

  if (data?.channel_id) {
    return (
      <div className="flex flex-col gap-2">
        <Label>연결된 채널</Label>
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono bg-muted rounded px-2 py-1">
            {data.channel_id}
          </span>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleDisconnect}
            disabled={setChannel.isPending}
          >
            {setChannel.isPending ? "해제 중..." : "연결 해제"}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleConnect} className="flex flex-col gap-2">
      <Label htmlFor="project-channel-id">Slack 채널 ID</Label>
      <div className="flex gap-2">
        <Input
          id="project-channel-id"
          value={channelInput}
          onChange={(e) => setChannelInput(e.target.value)}
          placeholder="예: C0123456789"
          className="flex-1"
        />
        <Button
          type="submit"
          size="sm"
          disabled={setChannel.isPending || !channelInput.trim()}
        >
          {setChannel.isPending ? "연결 중..." : "연결"}
        </Button>
      </div>
      {setChannel.isError && (
        <p className="text-sm text-destructive">연결에 실패했습니다.</p>
      )}
    </form>
  );
}
