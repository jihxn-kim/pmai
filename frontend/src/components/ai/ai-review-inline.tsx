"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import api from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AlertTriangle,
  AlertCircle,
  Info,
  ExternalLink,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import type { AIReview, AIIssue } from "@/components/ai/ai-review-detail";

interface AIReviewInlineProps {
  review: AIReview;
  projectId: string;
}

const severityConfig = {
  critical: {
    icon: AlertTriangle,
    color: "text-red-600 dark:text-red-400",
    bg: "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800",
    badge: "destructive" as const,
    label: "Critical",
  },
  warning: {
    icon: AlertCircle,
    color: "text-yellow-600 dark:text-yellow-400",
    bg: "bg-yellow-50 dark:bg-yellow-950/30 border-yellow-200 dark:border-yellow-800",
    badge: "secondary" as const,
    label: "Warning",
  },
  info: {
    icon: Info,
    color: "text-blue-600 dark:text-blue-400",
    bg: "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800",
    badge: "outline" as const,
    label: "Info",
  },
};

function cleanMarkdown(text: string): string {
  return text
    .replace(/```json:issues\s*\n[\s\S]*?```/g, "")
    .replace(/```json:expertise\s*\n[\s\S]*?```/g, "")
    .trim();
}

export function AIReviewInline({ review, projectId }: AIReviewInlineProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [registering, setRegistering] = useState(false);
  const [registeredIds, setRegisteredIds] = useState<Set<string>>(new Set());

  const rawText = (review.detail as { text?: string })?.text || review.summary || "";
  const cleanedText = cleanMarkdown(rawText);
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
    <div className="flex flex-col lg:flex-row">
      {/* Left: Report */}
      <div className="flex-1 min-w-0 p-5 lg:border-r overflow-y-auto max-h-[70vh]">
        <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:text-base prose-headings:font-semibold prose-p:text-sm prose-p:leading-relaxed prose-li:text-sm prose-table:text-sm prose-code:text-xs prose-pre:text-xs prose-pre:bg-muted prose-pre:border">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {cleanedText}
          </ReactMarkdown>
        </div>
      </div>

      {/* Right: Issues panel */}
      {issues.length > 0 && (
        <div className="lg:w-[380px] shrink-0 border-t lg:border-t-0 overflow-y-auto max-h-[70vh]">
          <div className="sticky top-0 bg-card z-10 px-4 py-3 border-b">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-sm">
                이슈 ({issues.length})
              </h4>
              <div className="flex items-center gap-1.5 text-xs">
                {issues.filter((i) => i.severity === "critical").length > 0 && (
                  <span className="flex items-center gap-0.5 text-red-600 dark:text-red-400">
                    <AlertTriangle className="size-3" />
                    {issues.filter((i) => i.severity === "critical").length}
                  </span>
                )}
                {issues.filter((i) => i.severity === "warning").length > 0 && (
                  <span className="flex items-center gap-0.5 text-yellow-600 dark:text-yellow-400">
                    <AlertCircle className="size-3" />
                    {issues.filter((i) => i.severity === "warning").length}
                  </span>
                )}
                {issues.filter((i) => i.severity === "info").length > 0 && (
                  <span className="flex items-center gap-0.5 text-blue-600 dark:text-blue-400">
                    <Info className="size-3" />
                    {issues.filter((i) => i.severity === "info").length}
                  </span>
                )}
              </div>
            </div>

            {pendingIssues.length > 0 && (
              <div className="flex items-center justify-between mt-2 pt-2 border-t">
                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={toggleAll}>
                  {selectedIds.size === pendingIssues.length ? "전체 해제" : "전체 선택"}
                </Button>
                <Button
                  size="sm"
                  className="h-7 text-xs"
                  onClick={handleRegister}
                  disabled={selectedIds.size === 0 || registering}
                >
                  {registering ? (
                    <Loader2 className="mr-1 size-3 animate-spin" />
                  ) : (
                    <ExternalLink className="mr-1 size-3" />
                  )}
                  등록 ({selectedIds.size})
                </Button>
              </div>
            )}
          </div>

          <div className="p-3 space-y-2">
            {issues.map((issue) => {
              const config = severityConfig[issue.severity] || severityConfig.info;
              const Icon = config.icon;
              const isRegistered = issue.status === "registered" || registeredIds.has(issue.id);

              return (
                <div
                  key={issue.id}
                  className={`rounded-lg border p-3 ${config.bg} transition-colors`}
                >
                  <div className="flex items-start gap-2">
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
                      <div className="flex items-center gap-1.5 flex-wrap mb-1">
                        <Icon className={`size-3.5 shrink-0 ${config.color}`} />
                        <span className="font-medium text-xs">{issue.title}</span>
                      </div>
                      <div className="flex items-center gap-1 flex-wrap mb-1.5">
                        <Badge variant={config.badge} className="text-[10px] px-1.5 py-0">
                          {config.label}
                        </Badge>
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                          {issue.category}
                        </Badge>
                        {issue.recommended_assignee && (
                          <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-normal">
                            @{issue.recommended_assignee}
                          </Badge>
                        )}
                        {isRegistered && issue.github_issue_number && (
                          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                            #{issue.github_issue_number}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {issue.description}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
