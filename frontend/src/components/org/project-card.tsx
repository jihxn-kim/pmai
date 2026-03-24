"use client";

import { useRouter } from "next/navigation";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Users } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ProjectSummary {
  id: string;
  name: string;
  slug: string;
  status: "active" | "paused" | "done";
  member_count: number;
  task_counts: {
    total: number;
    done: number;
  };
  org_slug: string;
}

interface ProjectCardProps {
  project: ProjectSummary;
}

const statusConfig: Record<
  ProjectSummary["status"],
  { label: string; className: string }
> = {
  active: { label: "Active", className: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400" },
  paused: { label: "Paused", className: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400" },
  done: { label: "Done", className: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400" },
};

export function ProjectCard({ project }: ProjectCardProps) {
  const router = useRouter();
  const { total, done } = project.task_counts;
  const progress = total > 0 ? Math.round((done / total) * 100) : 0;
  const { label, className } = statusConfig[project.status] ?? statusConfig.active;

  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      onClick={() => router.push(`/org/${project.org_slug}/projects/${project.slug}`)}
    >
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="line-clamp-2">{project.name}</CardTitle>
          <span
            className={cn(
              "inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium",
              className
            )}
          >
            {label}
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Progress bar */}
        <div>
          <div className="mb-1 flex justify-between text-xs text-muted-foreground">
            <span>Progress</span>
            <span>{progress}%</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </CardContent>

      <CardFooter className="text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <Users className="size-3.5" />
          <span>{project.member_count} member{project.member_count !== 1 ? "s" : ""}</span>
        </div>
        <span className="ml-auto">
          {done}/{total} tasks
        </span>
      </CardFooter>
    </Card>
  );
}
