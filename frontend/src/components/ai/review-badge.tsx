"use client";

import { useAIReviews, useRequestReview } from "@/hooks/use-ai";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

interface ReviewBadgeProps {
  projectId: string;
  prId: string;
}

interface AIReview {
  id: string;
  review_type: string;
  status: string;
  score?: number;
  pr_number?: number;
}

export function ReviewBadge({ projectId, prId }: ReviewBadgeProps) {
  const { data } = useAIReviews(projectId);
  const requestReview = useRequestReview(projectId);

  const reviews: AIReview[] = Array.isArray(data) ? data : [];

  // Find a code review for this PR
  const prNum = parseInt(prId, 10);
  const review = reviews.find(
    (r) => r.review_type === "code_review" && r.pr_number === prNum
  );

  if (review) {
    const isRunning =
      review.status === "pending" || review.status === "running";

    if (isRunning) {
      return (
        <span className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs text-blue-700 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-400">
          <Loader2 className="size-3 animate-spin" />
          AI
        </span>
      );
    }

    if (review.status === "completed" && review.score != null) {
      return (
        <span className="inline-flex items-center rounded-full border border-purple-200 bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-800 dark:border-purple-800 dark:bg-purple-950/30 dark:text-purple-400">
          AI {review.score}/10
        </span>
      );
    }

    // failed or completed without score
    return null;
  }

  // No review yet — show request button
  return (
    <Button
      size="sm"
      variant="outline"
      className="h-5 rounded-full px-2 py-0 text-xs"
      disabled={requestReview.isPending}
      onClick={(e) => {
        e.stopPropagation();
        requestReview.mutate(prNum);
      }}
    >
      {requestReview.isPending ? (
        <Loader2 className="size-3 animate-spin" />
      ) : (
        "AI Review"
      )}
    </Button>
  );
}
