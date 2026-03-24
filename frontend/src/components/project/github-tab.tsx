"use client";

import { usePulls } from "@/hooks/use-github";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ReviewBadge } from "@/components/ai/review-badge";
import { cn } from "@/lib/utils";
import { ExternalLink, GitPullRequest } from "lucide-react";

interface GitHubTabProps {
  projectId: string;
  repoUrl?: string;
}

interface PullRequest {
  id: number;
  number: number;
  title: string;
  state: "open" | "merged" | "closed";
  review_state?: "approved" | "changes_requested" | "pending" | null;
  html_url?: string;
}

const stateConfig: Record<
  PullRequest["state"],
  { label: string; className: string }
> = {
  open: {
    label: "Open",
    className: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  },
  merged: {
    label: "Merged",
    className: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
  },
  closed: {
    label: "Closed",
    className: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  },
};

const reviewConfig: Record<
  NonNullable<PullRequest["review_state"]>,
  { label: string; className: string }
> = {
  approved: {
    label: "Approved",
    className: "text-green-600 dark:text-green-400",
  },
  changes_requested: {
    label: "Changes Requested",
    className: "text-red-600 dark:text-red-400",
  },
  pending: {
    label: "Review Pending",
    className: "text-yellow-600 dark:text-yellow-400",
  },
};

export function GitHubTab({ projectId, repoUrl }: GitHubTabProps) {
  const { data, isLoading, isError } = usePulls(projectId);

  const pulls: PullRequest[] = Array.isArray(data) ? data : [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
        Loading pull requests...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-destructive">
        Failed to load pull requests.
      </div>
    );
  }

  if (pulls.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed py-20">
        <GitPullRequest className="size-10 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">No pull requests found.</p>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <GitPullRequest className="size-4" />
          Pull Requests
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <ul className="divide-y">
          {pulls.map((pr) => {
            const state = stateConfig[pr.state] ?? stateConfig.open;
            const review = pr.review_state ? reviewConfig[pr.review_state] : null;
            const prUrl =
              pr.html_url ??
              (repoUrl ? `${repoUrl}/pull/${pr.number}` : undefined);

            return (
              <li key={pr.id} className="flex items-start gap-3 px-4 py-3">
                {/* State badge */}
                <span
                  className={cn(
                    "mt-0.5 inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium",
                    state.className
                  )}
                >
                  {state.label}
                </span>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground">
                      #{pr.number}
                    </span>
                    <span className="truncate text-sm font-medium">
                      {pr.title}
                    </span>
                  </div>
                  {review && (
                    <p className={cn("mt-0.5 text-xs", review.className)}>
                      {review.label}
                    </p>
                  )}
                </div>

                <ReviewBadge
                  projectId={projectId}
                  prId={String(pr.number)}
                />

                {prUrl && (
                  <a
                    href={prUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-0.5 shrink-0 text-muted-foreground hover:text-foreground"
                  >
                    <ExternalLink className="size-3.5" />
                  </a>
                )}
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
