"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { GitBranch, ExternalLink, CheckCircle2 } from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";

interface GitHubConnectProps {
  projectId: string;
  githubRepoUrl?: string | null;
}

function extractRepoName(url: string): string {
  try {
    const u = new URL(url);
    // pathname is like /owner/repo or /owner/repo.git
    const parts = u.pathname.replace(/\.git$/, "").split("/").filter(Boolean);
    if (parts.length >= 2) return `${parts[0]}/${parts[1]}`;
    if (parts.length === 1) return parts[0];
  } catch {
    // fall through
  }
  return url;
}

export function GitHubConnect({ projectId, githubRepoUrl }: GitHubConnectProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleConnect() {
    if (!repoUrl.trim()) {
      setError("Please enter a repository URL.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await api.post(`/api/projects/${projectId}/github`, { repo_url: repoUrl.trim() });
      setSuccess(true);
      await queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      // close after a short delay so user sees success state
      setTimeout(() => {
        setOpen(false);
        setSuccess(false);
        setRepoUrl("");
      }, 1000);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to connect repository. Please check the URL and try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  // ── Connected state ────────────────────────────────────────────────────────
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

  // ── Disconnected state ─────────────────────────────────────────────────────
  return (
    <Dialog open={open} onOpenChange={(value) => {
      setOpen(value);
      if (!value) {
        setError(null);
        setSuccess(false);
        setRepoUrl("");
      }
    }}>
      <DialogTrigger
        render={
          <Button variant="outline" size="sm" className="gap-1.5" />
        }
      >
        <GitBranch className="size-4" />
        Connect GitHub Repository
      </DialogTrigger>

      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitBranch className="size-4" />
            Connect GitHub Repository
          </DialogTitle>
        </DialogHeader>

        {success ? (
          <div className="flex flex-col items-center gap-3 py-4">
            <CheckCircle2 className="size-8 text-green-500" />
            <p className="text-sm font-medium text-green-600 dark:text-green-400">
              Repository connected successfully!
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-3 py-2">
            <p className="text-sm text-muted-foreground">
              Enter the full GitHub repository URL to link it to this project.
            </p>
            <Input
              placeholder="https://github.com/owner/repo"
              value={repoUrl}
              onChange={(e) => {
                setRepoUrl(e.target.value);
                if (error) setError(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !loading) handleConnect();
              }}
              disabled={loading}
            />
            {error && (
              <p className="text-xs text-destructive">{error}</p>
            )}
          </div>
        )}

        {!success && (
          <DialogFooter>
            <Button
              onClick={handleConnect}
              disabled={loading || !repoUrl.trim()}
              size="sm"
            >
              {loading ? "Connecting..." : "Connect"}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
