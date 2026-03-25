"use client";

import { useState, useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  useRequestAnalysis,
  useRequestTestScenarios,
  useAIJobStatus,
} from "@/hooks/use-ai";
import { AIReviewList } from "@/components/ai/ai-review-list";
import { AIReviewDetail } from "@/components/ai/ai-review-detail";
import type { AIReview } from "@/components/ai/ai-review-detail";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Brain, FlaskConical, Loader2 } from "lucide-react";

interface AITabProps {
  projectId: string;
}

export function AITab({ projectId }: AITabProps) {
  const [selectedReview, setSelectedReview] = useState<AIReview | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [testDialogOpen, setTestDialogOpen] = useState(false);
  const [prNumber, setPrNumber] = useState("");
  const [filePaths, setFilePaths] = useState("");

  const analyze = useRequestAnalysis(projectId);
  const testScenarios = useRequestTestScenarios(projectId);

  // Track the latest job id returned from mutations
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const { data: jobStatus } = useAIJobStatus(activeJobId);

  const handleAnalyze = async () => {
    const result = await analyze.mutateAsync();
    if (result?.job_id) setActiveJobId(result.job_id);
  };

  const handleGenerateTests = async () => {
    const body: { pr_number?: number; file_paths?: string[] } = {};
    if (prNumber.trim()) body.pr_number = parseInt(prNumber.trim(), 10);
    if (filePaths.trim())
      body.file_paths = filePaths
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

    const result = await testScenarios.mutateAsync(body);
    if (result?.job_id) setActiveJobId(result.job_id);
    setTestDialogOpen(false);
    setPrNumber("");
    setFilePaths("");
  };

  const queryClient = useQueryClient();
  const prevStatus = useRef<string | null>(null);

  const isJobRunning =
    jobStatus?.status === "queued" || jobStatus?.status === "running";

  // Auto-refresh reviews when job completes
  useEffect(() => {
    if (prevStatus.current && !["completed", "failed"].includes(prevStatus.current)) {
      if (jobStatus?.status === "completed" || jobStatus?.status === "failed") {
        queryClient.invalidateQueries({ queryKey: ["ai-reviews", projectId] });
        // Clear active job after a brief delay so user sees the completion
        setTimeout(() => setActiveJobId(null), 2000);
      }
    }
    prevStatus.current = jobStatus?.status ?? null;
  }, [jobStatus?.status, projectId, queryClient]);

  return (
    <div className="flex flex-col gap-4">
      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          onClick={handleAnalyze}
          disabled={analyze.isPending}
        >
          {analyze.isPending ? (
            <Loader2 className="mr-1.5 size-4 animate-spin" />
          ) : (
            <Brain className="mr-1.5 size-4" />
          )}
          Analyze Project
        </Button>

        <Button
          size="sm"
          variant="outline"
          onClick={() => setTestDialogOpen(true)}
          disabled={testScenarios.isPending}
        >
          {testScenarios.isPending ? (
            <Loader2 className="mr-1.5 size-4 animate-spin" />
          ) : (
            <FlaskConical className="mr-1.5 size-4" />
          )}
          Generate Tests
        </Button>
      </div>

      {/* Job completed notification */}
      {activeJobId && jobStatus?.status === "completed" && (
        <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700 dark:border-green-800 dark:bg-green-950/30 dark:text-green-400">
          AI 분석이 완료되었습니다.
        </div>
      )}

      {activeJobId && jobStatus?.status === "failed" && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
          AI 분석이 실패했습니다: {jobStatus.error_message || "알 수 없는 오류"}
        </div>
      )}

      {/* Running job status with progress log */}
      {isJobRunning && activeJobId && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30 overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-blue-700 dark:text-blue-400 border-b border-blue-200 dark:border-blue-800">
            <Loader2 className="size-4 animate-spin" />
            <span>AI가 분석 중입니다...</span>
          </div>
          {jobStatus?.progress_log && jobStatus.progress_log.length > 0 && (
            <div className="max-h-48 overflow-y-auto px-3 py-2 space-y-1 font-mono text-xs text-blue-600 dark:text-blue-400">
              {(jobStatus.progress_log as Array<{timestamp: string; message: string}>).slice(-15).map((entry, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-blue-400 dark:text-blue-600 shrink-0">
                    {new Date(entry.timestamp).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                  </span>
                  <span className="truncate">{entry.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Review list */}
      <AIReviewList
        projectId={projectId}
        onSelect={(review) => {
          setSelectedReview(review);
          setDetailOpen(true);
        }}
      />

      {/* Review detail dialog */}
      <AIReviewDetail
        review={selectedReview}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />

      {/* Generate tests dialog */}
      <Dialog open={testDialogOpen} onOpenChange={setTestDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generate Test Scenarios</DialogTitle>
          </DialogHeader>

          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="pr-number">PR Number (optional)</Label>
              <Input
                id="pr-number"
                type="number"
                placeholder="e.g. 42"
                value={prNumber}
                onChange={(e) => setPrNumber(e.target.value)}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="file-paths">
                File Paths (optional, comma-separated)
              </Label>
              <Input
                id="file-paths"
                placeholder="src/foo.ts, src/bar.ts"
                value={filePaths}
                onChange={(e) => setFilePaths(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter showCloseButton>
            <Button
              size="sm"
              onClick={handleGenerateTests}
              disabled={testScenarios.isPending}
            >
              {testScenarios.isPending && (
                <Loader2 className="mr-1.5 size-4 animate-spin" />
              )}
              Generate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
