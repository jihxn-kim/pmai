"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

interface FileComment {
  file_path: string;
  line?: number;
  comment: string;
}

interface Suggestion {
  priority: "critical" | "warning" | "info";
  text: string;
}

interface AIReview {
  id: string;
  review_type: "code_review" | "analysis" | "test_scenario";
  summary?: string;
  status: string;
  created_at: string;
  score?: number;
  suggestions?: Suggestion[];
  file_comments?: FileComment[];
  content?: string;
}

interface AIReviewDetailProps {
  review: AIReview | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const priorityConfig: Record<
  Suggestion["priority"],
  { label: string; className: string }
> = {
  critical: {
    label: "Critical",
    className:
      "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  },
  warning: {
    label: "Warning",
    className:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  },
  info: {
    label: "Info",
    className:
      "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  },
};

export function AIReviewDetail({
  review,
  open,
  onOpenChange,
}: AIReviewDetailProps) {
  if (!review) return null;

  const suggestions: Suggestion[] = Array.isArray(review.suggestions)
    ? review.suggestions
    : [];
  const fileComments: FileComment[] = Array.isArray(review.file_comments)
    ? review.file_comments
    : [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl overflow-y-auto max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>AI Review Detail</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          {/* Summary */}
          {review.summary && (
            <section>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Summary
              </h3>
              <p className="text-sm">{review.summary}</p>
            </section>
          )}

          {/* Score */}
          {review.score != null && (
            <section>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Score
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold">{review.score}</span>
                <span className="text-sm text-muted-foreground">/ 10</span>
              </div>
            </section>
          )}

          {/* Content (for analysis / test scenarios) */}
          {review.content && (
            <section>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Details
              </h3>
              <pre className="whitespace-pre-wrap rounded-lg bg-muted px-3 py-2 text-xs">
                {review.content}
              </pre>
            </section>
          )}

          {/* Suggestions */}
          {suggestions.length > 0 && (
            <section>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Suggestions
              </h3>
              <ul className="space-y-2">
                {suggestions.map((s, i) => {
                  const cfg =
                    priorityConfig[s.priority] ?? priorityConfig.info;
                  return (
                    <li
                      key={i}
                      className="flex items-start gap-2 rounded-lg border p-2"
                    >
                      <span
                        className={cn(
                          "mt-0.5 inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium",
                          cfg.className
                        )}
                      >
                        {cfg.label}
                      </span>
                      <span className="text-sm">{s.text}</span>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {/* File comments */}
          {fileComments.length > 0 && (
            <section>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                File Comments
              </h3>
              <ul className="space-y-2">
                {fileComments.map((fc, i) => (
                  <li key={i} className="rounded-lg border p-3">
                    <div className="flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
                      <span>{fc.file_path}</span>
                      {fc.line != null && (
                        <span className="text-foreground">:{fc.line}</span>
                      )}
                    </div>
                    <p className="mt-1 text-sm">{fc.comment}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export type { AIReview };
