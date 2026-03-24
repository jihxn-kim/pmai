"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { useProject } from "@/hooks/use-projects";
import { OverviewTab } from "@/components/project/overview-tab";
import { GitHubTab } from "@/components/project/github-tab";
import { GitHubConnect } from "@/components/project/github-connect";
import { TeamTab } from "@/components/project/team-tab";
import { IssuesTab } from "@/components/project/issues-tab";
import { AITab } from "@/components/project/ai-tab";
import { KanbanBoard } from "@/components/project/kanban-board";
import { TaskModal } from "@/components/task/task-modal";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProjectDetailPageProps {
  params: Promise<{ slug: string; projectId: string }>;
}

const statusConfig: Record<
  string,
  { label: string; className: string }
> = {
  active: {
    label: "Active",
    className:
      "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  },
  paused: {
    label: "Paused",
    className:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  },
  done: {
    label: "Done",
    className: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  },
};

export default function ProjectDetailPage({ params }: ProjectDetailPageProps) {
  const { slug, projectId } = use(params);
  const router = useRouter();
  const [newTaskOpen, setNewTaskOpen] = useState(false);

  const { data: project, isLoading, isError } = useProject(projectId);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Loading project...
      </div>
    );
  }

  if (isError || !project) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <p className="text-sm text-destructive">Project not found.</p>
        <Button variant="outline" onClick={() => router.push(`/org/${slug}`)}>
          <ArrowLeft className="mr-1.5 size-4" />
          Back to Dashboard
        </Button>
      </div>
    );
  }

  const status = statusConfig[project.status as string] ?? statusConfig.active;

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div className="flex items-start gap-4">
        <Button
          variant="ghost"
          size="sm"
          className="-ml-1 mt-0.5"
          onClick={() => router.push(`/org/${slug}`)}
        >
          <ArrowLeft className="size-4" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">{project.name}</h1>
            <span
              className={cn(
                "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                status.className
              )}
            >
              {status.label}
            </span>
          </div>
          <div className="mt-1.5">
            <GitHubConnect
              projectId={projectId}
              githubRepoUrl={project.github_repo_url}
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="tasks">Tasks</TabsTrigger>
          <TabsTrigger value="github">GitHub</TabsTrigger>
          <TabsTrigger value="team">Team</TabsTrigger>
          <TabsTrigger value="issues">Issues</TabsTrigger>
          <TabsTrigger value="ai">AI</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="pt-4">
            <OverviewTab
              projectId={projectId}
              description={project.description}
              startDate={project.start_date}
              endDate={project.end_date}
            />
          </div>
        </TabsContent>

        <TabsContent value="tasks">
          <div className="pt-4 flex flex-col gap-4">
            <div className="flex justify-end">
              <Button size="sm" onClick={() => setNewTaskOpen(true)}>
                <Plus className="mr-1.5 size-4" />
                New Task
              </Button>
            </div>
            <KanbanBoard projectId={projectId} />
            <TaskModal
              projectId={projectId}
              open={newTaskOpen}
              onOpenChange={setNewTaskOpen}
            />
          </div>
        </TabsContent>

        <TabsContent value="github">
          <div className="pt-4">
            <GitHubTab projectId={projectId} repoUrl={project.repo_url} />
          </div>
        </TabsContent>

        <TabsContent value="team">
          <div className="pt-4">
            <TeamTab projectId={projectId} />
          </div>
        </TabsContent>

        <TabsContent value="issues">
          <div className="pt-4">
            <IssuesTab projectId={projectId} />
          </div>
        </TabsContent>

        <TabsContent value="ai">
          <div className="pt-4">
            <AITab projectId={projectId} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
