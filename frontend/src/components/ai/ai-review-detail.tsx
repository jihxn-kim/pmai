"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { formatDate } from "@/lib/utils";
import api from "@/lib/api";
import {
  AlertTriangle,
  AlertCircle,
  Info,
  ExternalLink,
  Loader2,
  CheckCircle2,
} from "lucide-react";

export interface AIIssue {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "warning" | "info";
  category: string;
  status: "pending" | "registered";
  github_issue_number?: number;
}

export interface AIReview {
  id: string;
  type?: string;
  review_type?: string;
  summary?: string;
  status: string;
  created_at: string;
  detail?: { text?: string } | Record<string, unknown>;
  suggestions?: AIIssue[];
}

interface AIReviewDetailProps {
  review: AIReview | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
}

const typeLabels: Record<string, string> = {
  code_review: "Code Review",
  analysis: "Analysis",
  test_scenario: "Test Scenarios",
};

const severityConfig = {
  critical: { icon: AlertTriangle, color: "text-red-500", bg: "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800", badge: "destructive" as const },
  warning: { icon: AlertCircle, color: "text-yellow-500", bg: "bg-yellow-50 dark:bg-yellow-950/30 border-yellow-200 dark:border-yellow-800", badge: "secondary" as const },
  info: { icon: Info, color: "text-blue-500", bg: "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800", badge: "outline" as const },
};

export function AIReviewDetail({ review, open, onOpenChange, projectId }: AIReviewDetailProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [registering, setRegistering] = useState(false);
  const [registeredIds, setRegisteredIds] = useState<Set<string>>(new Set());

  if (!review) return null;

  const reviewType = review.type || review.review_type || "analysis";
  const fullText = (review.detail as { text?: string })?.text || review.summary || "";
  const issues: AIIssue[] = review.suggestions || [];
  const pendingIssues = issues.filter((i) => i.status === "pending" && !registeredIds.has(i.id));

  const toggleIssue = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedIds.size === pendingIssues.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(pendingIssues.map((i) => i.id)));
    }
  };

  const handleRegister = async () => {
    if (selectedIds.size === 0) return;
    setRegistering(true);
    try {
      const { data } = await api.post(
        `/api/projects/${projectId}/ai/reviews/${review.id}/register-issues`,
        { issue_ids: Array.from(selectedIds) }
      );
      const newRegistered = new Set(registeredIds);
      for (const item of data.created) {
        newRegistered.add(item.id);
      }
      setRegisteredIds(newRegistered);
      setSelectedIds(new Set());
    } catch {
      // error handling
    } finally {
      setRegistering(false);
    }
  };

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

        {/* Issues section */}
        {issues.length > 0 && (
          <div className="mt-4 border-t pt-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm">
                발견된 이슈 ({issues.length}건)
              </h3>
              {pendingIssues.length > 0 && (
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" onClick={toggleAll}>
                    {selectedIds.size === pendingIssues.length ? "전체 해제" : "전체 선택"}
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleRegister}
                    disabled={selectedIds.size === 0 || registering}
                  >
                    {registering ? (
                      <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                    ) : (
                      <ExternalLink className="mr-1.5 size-3.5" />
                    )}
                    GitHub Issue 등록 ({selectedIds.size}건)
                  </Button>
                </div>
              )}
            </div>

            <div className="space-y-2">
              {issues.map((issue) => {
                const config = severityConfig[issue.severity] || severityConfig.info;
                const Icon = config.icon;
                const isRegistered = issue.status === "registered" || registeredIds.has(issue.id);

                return (
                  <div
                    key={issue.id}
                    className={`rounded-lg border p-3 ${config.bg}`}
                  >
                    <div className="flex items-start gap-3">
                      {!isRegistered && (
                        <Checkbox
                          checked={selectedIds.has(issue.id)}
                          onCheckedChange={() => toggleIssue(issue.id)}
                          className="mt-0.5"
                        />
                      )}
                      {isRegistered && (
                        <CheckCircle2 className="size-4 text-green-500 mt-0.5 shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <Icon className={`size-4 shrink-0 ${config.color}`} />
                          <span className="font-medium text-sm">{issue.title}</span>
                          <Badge variant={config.badge} className="text-xs">
                            {issue.severity}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {issue.category}
                          </Badge>
                          {isRegistered && issue.github_issue_number && (
                            <Badge variant="secondary" className="text-xs">
                              #{issue.github_issue_number}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">{issue.description}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
