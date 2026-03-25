"use client";

import { useAIReviews } from "@/hooks/use-ai";
import { cn } from "@/lib/utils";
import { Brain } from "lucide-react";

interface AIReview {
  id: string;
  type?: "code_review" | "analysis" | "test_scenario";
  review_type?: "code_review" | "analysis" | "test_scenario";
  summary?: string;
  status: string;
  created_at: string;
  detail?: { text?: string };
}

interface AIReviewListProps {
  projectId: string;
  onSelect?: (review: AIReview) => void;
}

const typeConfig: Record<
  AIReview["review_type"],
  { label: string; className: string }
> = {
  code_review: {
    label: "Code Review",
    className:
      "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
  },
  analysis: {
    label: "Analysis",
    className:
      "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  },
  test_scenario: {
    label: "Test Scenarios",
    className:
      "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  },
};

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function AIReviewList({ projectId, onSelect }: AIReviewListProps) {
  const { data, isLoading, isError } = useAIReviews(projectId);

  const reviews: AIReview[] = Array.isArray(data) ? data : [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
        Loading AI reviews...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-destructive">
        Failed to load AI reviews.
      </div>
    );
  }

  if (reviews.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed py-16">
        <Brain className="size-10 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">No AI reviews yet.</p>
      </div>
    );
  }

  return (
    <ul className="divide-y rounded-xl border">
      {reviews.map((review) => {
        const reviewType = review.type || review.review_type || "analysis";
        const type = typeConfig[reviewType] ?? typeConfig.analysis;
        const isPending =
          review.status === "pending" || review.status === "running";

        return (
          <li
            key={review.id}
            className={cn(
              "flex items-start gap-3 px-4 py-3",
              onSelect && "cursor-pointer hover:bg-muted/50 transition-colors"
            )}
            onClick={() => onSelect?.(review)}
          >
            <span
              className={cn(
                "mt-0.5 inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium",
                type.className
              )}
            >
              {type.label}
            </span>

            <div className="min-w-0 flex-1">
              <p className="truncate text-sm">
                {review.summary ?? "(Processing...)"}
              </p>
              {isPending && (
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Running...
                </p>
              )}
            </div>

            <div className="flex shrink-0 flex-col items-end gap-1">
              {review.score != null && (
                <span className="text-xs font-semibold text-foreground">
                  {review.score}/10
                </span>
              )}
              <span className="text-xs text-muted-foreground">
                {formatRelativeTime(review.created_at)}
              </span>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export type { AIReview };
