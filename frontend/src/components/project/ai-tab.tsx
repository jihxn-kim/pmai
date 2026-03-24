"use client";

import { useState } from "react";
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

  const isJobRunning =
    jobStatus?.status === "pending" || jobStatus?.status === "running";

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

      {/* Running job status */}
      {isJobRunning && activeJobId && (
        <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-400">
          <Loader2 className="size-4 animate-spin" />
          <span>AI job running... ({jobStatus.status})</span>
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
