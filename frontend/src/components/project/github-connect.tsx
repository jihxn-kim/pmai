"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { GitBranch, ExternalLink, CheckCircle2, Loader2, Lock } from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface GitHubConnectProps {
  projectId: string;
  orgId: string;
  githubRepoUrl?: string | null;
}

interface GitHubRepo {
  id: number;
  full_name: string;
  url: string;
  private: boolean;
}

function extractRepoName(url: string): string {
  try {
    const u = new URL(url);
    const parts = u.pathname.replace(/\.git$/, "").split("/").filter(Boolean);
    if (parts.length >= 2) return `${parts[0]}/${parts[1]}`;
    if (parts.length === 1) return parts[0];
  } catch {
    // fall through
  }
  return url;
}

export function GitHubConnect({ projectId, orgId, githubRepoUrl }: GitHubConnectProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [selectedUrl, setSelectedUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const { data: repos, isLoading: reposLoading } = useQuery<GitHubRepo[]>({
    queryKey: ["github-repos", orgId],
    queryFn: () => api.get(`/api/orgs/${orgId}/github/repos`).then((r) => r.data.repos),
    enabled: !!orgId && open,
  });

  async function handleConnect() {
    if (!selectedUrl) {
      setError("레포지토리를 선택해주세요.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await api.post(`/api/projects/${projectId}/github`, { repo_url: selectedUrl });
      setSuccess(true);
      await queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      setTimeout(() => {
        setOpen(false);
        setSuccess(false);
        setSelectedUrl("");
      }, 1000);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "연결에 실패했습니다.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  // Connected state
  if (githubRepoUrl) {
    const repoName = extractRepoName(githubRepoUrl);
    return (
      <div className="flex items-center gap-2">
        <GitBranch className="size-4 shrink-0 text-muted-foreground" />
        <a
          href={githubRepoUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground hover:underline"
        >
          {repoName}
          <ExternalLink className="size-3" />
        </a>
        <Badge variant="secondary" className="text-xs">
          Connected
        </Badge>
      </div>
    );
  }

  // Disconnected state
  return (
    <Dialog open={open} onOpenChange={(value) => {
      setOpen(value);
      if (!value) {
        setError(null);
        setSuccess(false);
        setSelectedUrl("");
      }
    }}>
      <DialogTrigger
        render={
          <Button variant="outline" size="sm" className="gap-1.5" />
        }
      >
        <GitBranch className="size-4" />
        GitHub 레포 연결
      </DialogTrigger>

      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitBranch className="size-4" />
            GitHub 레포지토리 연결
          </DialogTitle>
        </DialogHeader>

        {success ? (
          <div className="flex flex-col items-center gap-3 py-4">
            <CheckCircle2 className="size-8 text-green-500" />
            <p className="text-sm font-medium text-green-600 dark:text-green-400">
              레포지토리가 연결되었습니다!
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-3 py-2">
            <p className="text-sm text-muted-foreground">
              GitHub App에 접근 가능한 레포지토리 중 선택하세요.
            </p>

            {reposLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                <Loader2 className="size-4 animate-spin" />
                레포지토리 목록 로딩 중...
              </div>
            ) : repos && repos.length > 0 ? (
              <Select value={selectedUrl} onValueChange={(v) => setSelectedUrl(v ?? "")}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="레포지토리 선택..." />
                </SelectTrigger>
                <SelectContent className="w-[var(--radix-select-trigger-width)]">
                  {repos.map((repo) => (
                    <SelectItem key={repo.id} value={repo.url}>
                      <div className="flex items-center gap-1.5">
                        <GitBranch className="size-3.5 text-muted-foreground" />
                        {repo.full_name}
                        {repo.private && <Lock className="size-3 text-muted-foreground" />}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <div className="text-sm text-muted-foreground py-4 text-center">
                접근 가능한 레포지토리가 없습니다. GitHub App이 설치되어 있는지 확인하세요.
              </div>
            )}

            {error && (
              <p className="text-xs text-destructive">{error}</p>
            )}
          </div>
        )}

        {!success && repos && repos.length > 0 && (
          <DialogFooter>
            <Button
              onClick={handleConnect}
              disabled={loading || !selectedUrl}
              size="sm"
            >
              {loading ? "연결 중..." : "연결"}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
