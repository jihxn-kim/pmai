"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { ScrollArea } from "@/components/ui/scroll-area";
import { GitCommit, MessageSquare, UserPlus, CheckCircle2, Circle } from "lucide-react";
import { formatDate } from "@/lib/utils";

export interface ActivityItem {
  id: string;
  type: string;
  title: string;
  description?: string;
  created_at: string;
  actor?: {
    name: string;
    avatar_url?: string;
  };
}

interface ActivityFeedProps {
  projectId: string;
  className?: string;
}

const activityIcon: Record<string, React.ReactNode> = {
  commit: <GitCommit className="size-4 text-blue-500" />,
  comment: <MessageSquare className="size-4 text-purple-500" />,
  member_added: <UserPlus className="size-4 text-green-500" />,
  task_done: <CheckCircle2 className="size-4 text-green-500" />,
};

function ActivityRow({ item }: { item: ActivityItem }) {
  const icon = activityIcon[item.type] ?? <Circle className="size-4 text-muted-foreground" />;

  return (
    <div className="flex items-start gap-3 py-3">
      <div className="mt-0.5 shrink-0">{icon}</div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm">{item.title}</p>
        {item.description && (
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {item.description}
          </p>
        )}
      </div>
      <time className="shrink-0 text-xs text-muted-foreground">
        {formatDate(item.created_at)}
      </time>
    </div>
  );
}

export function ActivityFeed({ projectId, className }: ActivityFeedProps) {
  const { data, isLoading, isError } = useQuery<ActivityItem[]>({
    queryKey: ["activity", projectId],
    queryFn: () =>
      api.get(`/api/projects/${projectId}/activity`).then((r) => r.data),
    enabled: !!projectId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
        Loading activity...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-destructive">
        Failed to load activity.
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
        No recent activity.
      </div>
    );
  }

  return (
    <ScrollArea className={className}>
      <div className="divide-y">
        {data.map((item) => (
          <ActivityRow key={item.id} item={item} />
        ))}
      </div>
    </ScrollArea>
  );
}
