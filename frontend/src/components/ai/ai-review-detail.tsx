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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatDate } from "@/lib/utils";
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
  FileText,
  ListChecks,
} from "lucide-react";

export interface AIIssue {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "warning" | "info";
  category: string;
  recommended_assignee?: string | null;
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
  // Remove the json:issues and json:expertise blocks from display
  return text
    .replace(/```json:issues\s*\n[\s\S]*?```/g, "")
    .replace(/```json:expertise\s*\n[\s\S]*?```/g, "")
    .trim();
}

export function AIReviewDetail({ review, open, onOpenChange, projectId }: AIReviewDetailProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [registering, setRegistering] = useState(false);
  const [registeredIds, setRegisteredIds] = useState<Set<string>>(new Set());

  if (!review) return null;

  const reviewType = review.type || review.review_type || "analysis";
  const rawText = (review.detail as { text?: string })?.text || review.summary || "";
  const cleanedText = cleanMarkdown(rawText);
  const issues: AIIssue[] = review.suggestions || [];
  const pendingIssues = issues.filter((i) => i.status === "pending" && !registeredIds.has(i.id));

  const criticalCount = issues.filter((i) => i.severity === "critical").length;
  const warningCount = issues.filter((i) => i.severity === "warning").length;
  const infoCount = issues.filter((i) => i.severity === "info").length;

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
      <DialogContent className="max-w-4xl overflow-y-auto max-h-[90vh]">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <DialogTitle className="text-lg">AI 분석 결과</DialogTitle>
            <Badge variant="secondary">{typeLabels[reviewType] || reviewType}</Badge>
            <span className="text-xs text-muted-foreground ml-auto">
              {formatDate(review.created_at)}
            </span>
          </div>

          {/* Issue summary bar */}
          {issues.length > 0 && (
            <div className="flex items-center gap-3 mt-2 text-xs">
              {criticalCount > 0 && (
                <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
                  <AlertTriangle className="size-3.5" />
                  Critical {criticalCount}
                </span>
              )}
              {warningCount > 0 && (
                <span className="flex items-center gap-1 text-yellow-600 dark:text-yellow-400">
                  <AlertCircle className="size-3.5" />
                  Warning {warningCount}
                </span>
              )}
              {infoCount > 0 && (
                <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400">
                  <Info className="size-3.5" />
                  Info {infoCount}
                </span>
              )}
            </div>
          )}
        </DialogHeader>

        <Tabs defaultValue="report" className="mt-2">
          <TabsList className="w-full">
            <TabsTrigger value="report" className="flex-1 gap-1.5">
              <FileText className="size-3.5" />
              분석 보고서
            </TabsTrigger>
            <TabsTrigger value="issues" className="flex-1 gap-1.5">
              <ListChecks className="size-3.5" />
              발견된 이슈 ({issues.length})
            </TabsTrigger>
          </TabsList>

          {/* Report tab */}
          <TabsContent value="report" className="mt-4">
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {cleanedText}
              </ReactMarkdown>
            </div>
          </TabsContent>

          {/* Issues tab */}
          <TabsContent value="issues" className="mt-4">
            {issues.length === 0 ? (
              <div className="text-center py-8 text-sm text-muted-foreground">
                발견된 이슈가 없습니다.
              </div>
            ) : (
              <>
                {/* Action bar */}
                {pendingIssues.length > 0 && (
                  <div className="flex items-center justify-between mb-4 pb-3 border-b">
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

                <div className="space-y-3">
                  {issues.map((issue) => {
                    const config = severityConfig[issue.severity] || severityConfig.info;
                    const Icon = config.icon;
                    const isRegistered = issue.status === "registered" || registeredIds.has(issue.id);

                    return (
                      <div
                        key={issue.id}
                        className={`rounded-lg border p-4 ${config.bg} transition-colors`}
                      >
                        <div className="flex items-start gap-3">
                          {!isRegistered && (
                            <Checkbox
                              checked={selectedIds.has(issue.id)}
                              onCheckedChange={() => toggleIssue(issue.id)}
                              className="mt-1"
                            />
                          )}
                          {isRegistered && (
                            <CheckCircle2 className="size-5 text-green-500 mt-0.5 shrink-0" />
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap mb-2">
                              <Icon className={`size-4 shrink-0 ${config.color}`} />
                              <span className="font-semibold text-sm">{issue.title}</span>
                            </div>
                            <div className="flex items-center gap-1.5 flex-wrap mb-2">
                              <Badge variant={config.badge} className="text-xs">
                                {config.label}
                              </Badge>
                              <Badge variant="outline" className="text-xs">
                                {issue.category}
                              </Badge>
                              {issue.recommended_assignee && (
                                <Badge variant="outline" className="text-xs font-normal">
                                  @{issue.recommended_assignee}
                                </Badge>
                              )}
                              {isRegistered && issue.github_issue_number && (
                                <Badge variant="secondary" className="text-xs">
                                  #{issue.github_issue_number}
                                </Badge>
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground leading-relaxed">
                              {issue.description}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
