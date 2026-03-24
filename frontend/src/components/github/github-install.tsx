"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { GitBranch, ExternalLink, CheckCircle2 } from "lucide-react";

interface GitHubInstallProps {
  orgId: string;
}

export function GitHubInstall({ orgId }: GitHubInstallProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["github-status", orgId],
    queryFn: () => api.get(`/api/orgs/${orgId}/github/status`).then((r) => r.data),
    enabled: !!orgId,
  });

  if (isLoading) {
    return <Card><CardContent className="py-6 text-sm text-muted-foreground">Loading...</CardContent></Card>;
  }

  const installed = data?.installed ?? false;

  return (
    <Card>
      <CardContent className="flex items-center justify-between py-6">
        <div className="flex items-center gap-3">
          <GitBranch className="size-5 text-muted-foreground" />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium">GitHub App</span>
              {installed ? (
                <Badge variant="default" className="gap-1">
                  <CheckCircle2 className="size-3" /> 설치됨
                </Badge>
              ) : (
                <Badge variant="secondary">미설치</Badge>
              )}
            </div>
            {installed && (
              <p className="text-xs text-muted-foreground mt-0.5">
                Installation ID: {data.installation_id}
              </p>
            )}
          </div>
        </div>
        {!installed && (
          <Button
            onClick={() => {
              window.location.href = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/orgs/${orgId}/github/install`;
            }}
          >
            <ExternalLink className="size-4 mr-2" /> GitHub App 설치
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
