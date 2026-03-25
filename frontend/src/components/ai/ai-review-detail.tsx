"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

export interface AIReview {
  id: string;
  type?: string;
  review_type?: string;
  summary?: string;
  status: string;
  created_at: string;
  detail?: { text?: string } | Record<string, unknown>;
}

interface AIReviewDetailProps {
  review: AIReview | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const typeLabels: Record<string, string> = {
  code_review: "Code Review",
  analysis: "Analysis",
  test_scenario: "Test Scenarios",
};

export function AIReviewDetail({ review, open, onOpenChange }: AIReviewDetailProps) {
  if (!review) return null;

  const reviewType = review.type || review.review_type || "analysis";
  const fullText = (review.detail as { text?: string })?.text || review.summary || "";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl overflow-y-auto max-h-[85vh]">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <DialogTitle>AI Review Detail</DialogTitle>
            <Badge variant="secondary">{typeLabels[reviewType] || reviewType}</Badge>
            <span className="text-xs text-muted-foreground ml-auto">
              {formatDate(review.created_at)}
            </span>
          </div>
        </DialogHeader>

        <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap text-sm leading-relaxed">
          {fullText}
        </div>
      </DialogContent>
    </Dialog>
  );
}
