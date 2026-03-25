"use client";

import { useState, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRequestTestScenarios } from "@/hooks/use-ai";
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
import { Brain, FlaskConical, Loader2, CheckCircle2, XCircle } from "lucide-react";

interface AITabProps {
  projectId: string;
}

interface ProgressEntry {
  message: string;
  timestamp: string;
}

export function AITab({ projectId }: AITabProps) {
  const queryClient = useQueryClient();
  const [selectedReview, setSelectedReview] = useState<AIReview | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [testDialogOpen, setTestDialogOpen] = useState(false);
  const [prNumber, setPrNumber] = useState("");
  const [filePaths, setFilePaths] = useState("");

  const testScenarios = useRequestTestScenarios(projectId);

  // SSE streaming state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progressLog, setProgressLog] = useState<ProgressEntry[]>([]);
  const [analyzeStatus, setAnalyzeStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const logEndRef = useRef<HTMLDivElement>(null);

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setAnalyzeStatus("running");
    setProgressLog([]);
    setErrorMessage("");

    try {
      const token = sessionStorage.getItem("access_token");
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/projects/${projectId}/ai/analyze`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No response body");

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            const now = new Date().toLocaleTimeString("ko-KR", {
              hour: "2-digit", minute: "2-digit", second: "2-digit",
            });

            if (event.type === "progress") {
              setProgressLog((prev) => [...prev, { message: event.message, timestamp: now }]);
              // Auto-scroll
              setTimeout(() => logEndRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
            } else if (event.type === "result") {
              setAnalyzeStatus("done");
              queryClient.invalidateQueries({ queryKey: ["ai-reviews", projectId] });
            } else if (event.type === "error") {
              setAnalyzeStatus("error");
              setErrorMessage(event.message);
            } else if (event.type === "done") {
              // Stream ended
            }
          } catch {
            // ignore parse errors
          }
        }
      }
    } catch (err) {
      setAnalyzeStatus("error");
      setErrorMessage(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsAnalyzing(false);
      // Reset status after delay
      setTimeout(() => {
        if (analyzeStatus !== "error") setAnalyzeStatus("idle");
      }, 5000);
    }
  };

  const handleGenerateTests = async () => {
    const body: { pr_number?: number; file_paths?: string[] } = {};
    if (prNumber.trim()) body.pr_number = parseInt(prNumber.trim(), 10);
    if (filePaths.trim())
      body.file_paths = filePaths.split(",").map((s) => s.trim()).filter(Boolean);

    await testScenarios.mutateAsync(body);
    setTestDialogOpen(false);
    setPrNumber("");
    setFilePaths("");
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={handleAnalyze} disabled={isAnalyzing}>
          {isAnalyzing ? (
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

      {/* Completion banner */}
      {analyzeStatus === "done" && (
        <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700 dark:border-green-800 dark:bg-green-950/30 dark:text-green-400">
          <CheckCircle2 className="size-4" />
          AI 분석이 완료되었습니다.
        </div>
      )}

      {analyzeStatus === "error" && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
          <XCircle className="size-4" />
          {errorMessage || "AI 분석에 실패했습니다."}
        </div>
      )}

      {/* Live progress log */}
      {isAnalyzing && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30 overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-blue-700 dark:text-blue-400 border-b border-blue-200 dark:border-blue-800">
            <Loader2 className="size-4 animate-spin" />
            <span>AI가 분석 중입니다...</span>
          </div>
          <div className="max-h-64 overflow-y-auto px-3 py-2 space-y-1 font-mono text-xs text-blue-600 dark:text-blue-400">
            {progressLog.length === 0 && (
              <div className="text-blue-400">대기 중...</div>
            )}
            {progressLog.map((entry, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-blue-400 dark:text-blue-600 shrink-0">{entry.timestamp}</span>
                <span>{entry.message}</span>
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
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
              <Label htmlFor="file-paths">File Paths (optional, comma-separated)</Label>
              <Input
                id="file-paths"
                placeholder="e.g. src/auth.py, src/api.py"
                value={filePaths}
                onChange={(e) => setFilePaths(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTestDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleGenerateTests} disabled={testScenarios.isPending}>
              {testScenarios.isPending ? "Generating..." : "Generate"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
