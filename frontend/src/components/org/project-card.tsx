"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Users, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useDeleteProject } from "@/hooks/use-projects";

export interface ProjectSummary {
  id: string;
  name: string;
  status: "active" | "paused" | "done";
  member_count: number;
  progress: {
    todo: number;
    in_progress: number;
    review: number;
    done: number;
    total: number;
    progress: number;
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
  const deleteProject = useDeleteProject();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const prog = project.progress ?? { total: 0, done: 0, progress: 0 };
  const total = prog.total ?? 0;
  const done = prog.done ?? 0;
  const progressPct = prog.progress ?? (total > 0 ? Math.round((done / total) * 100) : 0);
  const { label, className } = statusConfig[project.status] ?? statusConfig.active;

  return (
    <>
      <Card
        className="cursor-pointer transition-shadow hover:shadow-md"
        onClick={() => router.push(`/org/${project.org_slug}/project/${project.id}`)}
      >
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="line-clamp-2">{project.name}</CardTitle>
            <div className="flex items-center gap-1.5">
              <span
                className={cn(
                  "inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium",
                  className
                )}
              >
                {label}
              </span>
              <Button
                variant="ghost"
                size="icon-sm"
                className="text-destructive hover:text-destructive"
                onClick={(e) => {
                  e.stopPropagation();
                  setConfirmDelete(true);
                }}
                aria-label="Delete project"
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Progress bar */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{done}/{total} tasks</span>
              <span>{progressPct}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        </CardContent>
        <CardFooter className="text-xs text-muted-foreground">
          <Users className="mr-1.5 size-3.5" />
          {project.member_count} member{project.member_count !== 1 ? "s" : ""}
        </CardFooter>
      </Card>

      {/* Confirm delete dialog */}
      <Dialog
        open={confirmDelete}
        onOpenChange={(open) => !open && setConfirmDelete(false)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Project</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete{" "}
              <strong>{project.name}</strong>? All tasks, reviews, and data
              associated with this project will be permanently removed. This
              action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmDelete(false)}
              disabled={deleteProject.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() =>
                deleteProject.mutate(project.id, {
                  onSuccess: () => setConfirmDelete(false),
                })
              }
              disabled={deleteProject.isPending}
            >
              {deleteProject.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
