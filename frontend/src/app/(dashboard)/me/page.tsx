"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import api from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { CheckSquare, CalendarDays, AlertCircle } from "lucide-react";
import { cn, formatDate } from "@/lib/utils";

interface Task {
  id: string;
  title: string;
  status: string;
  priority: string;
  due_date?: string | null;
  project_id: string;
  project_name?: string;
}

interface MyTasksResponse {
  items: Task[];
  total: number;
}

const statusConfig: Record<string, { label: string; variant: "default" | "secondary" | "outline" }> = {
  todo: { label: "Todo", variant: "outline" },
  in_progress: { label: "In Progress", variant: "secondary" },
  in_review: { label: "In Review", variant: "secondary" },
  done: { label: "Done", variant: "default" },
};

const priorityConfig: Record<string, { label: string; className: string }> = {
  low: { label: "Low", className: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400" },
  medium: { label: "Medium", className: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" },
  high: { label: "High", className: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400" },
  urgent: { label: "Urgent", className: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" },
};

function isDueToday(dateStr?: string | null): boolean {
  if (!dateStr) return false;
  const today = new Date();
  const due = new Date(dateStr);
  return (
    due.getFullYear() === today.getFullYear() &&
    due.getMonth() === today.getMonth() &&
    due.getDate() === today.getDate()
  );
}

function isDueThisWeek(dateStr?: string | null): boolean {
  if (!dateStr) return false;
  const today = new Date();
  const due = new Date(dateStr);
  const weekFromNow = new Date(today);
  weekFromNow.setDate(today.getDate() + 7);
  return due >= today && due <= weekFromNow;
}

function TaskRow({ task }: { task: Task }) {
  const status = statusConfig[task.status] ?? { label: task.status, variant: "outline" as const };
  const priority = priorityConfig[task.priority] ?? { label: task.priority, className: "" };
  const today = isDueToday(task.due_date);
  const thisWeek = isDueThisWeek(task.due_date);

  return (
    <div
      className={cn(
        "flex items-center gap-3 py-3 px-4 rounded-lg text-sm transition-colors hover:bg-muted/50",
        today && "border-l-2 border-red-500 pl-3",
        !today && thisWeek && "border-l-2 border-amber-400 pl-3"
      )}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium truncate">{task.title}</span>
          {today && (
            <span className="inline-flex items-center gap-1 text-xs text-red-600 font-medium">
              <AlertCircle className="size-3" />
              Due today
            </span>
          )}
        </div>
        {task.project_name && (
          <p className="text-xs text-muted-foreground mt-0.5">{task.project_name}</p>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Badge variant={status.variant}>{status.label}</Badge>
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
            priority.className
          )}
        >
          {priority.label}
        </span>
        {task.due_date && (
          <span className={cn(
            "flex items-center gap-1 text-xs",
            today ? "text-red-600 font-medium" : "text-muted-foreground"
          )}>
            <CalendarDays className="size-3" />
            {formatDate(task.due_date)}
          </span>
        )}
      </div>
    </div>
  );
}

export default function MePage() {
  const { user } = useAuth();

  const { data, isLoading, isError } = useQuery<MyTasksResponse>({
    queryKey: ["my-tasks"],
    queryFn: () => api.get("/api/me/tasks").then((r) => r.data),
    enabled: !!user,
  });

  const tasks: Task[] = Array.isArray(data?.items) ? data.items : [];

  // Group by project
  const grouped = tasks.reduce<Record<string, Task[]>>((acc, task) => {
    const key = task.project_name ?? task.project_id ?? "Unknown Project";
    if (!acc[key]) acc[key] = [];
    acc[key].push(task);
    return acc;
  }, {});

  const projectNames = Object.keys(grouped).sort();

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">
          {user ? `${user.name}'s Tasks` : "My Tasks"}
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          All your tasks across every project
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
          Loading tasks...
        </div>
      )}

      {isError && (
        <div className="flex items-center justify-center py-16 text-sm text-destructive">
          Failed to load tasks.
        </div>
      )}

      {!isLoading && !isError && tasks.length === 0 && (
        <div className="flex flex-1 flex-col items-center justify-center gap-4 rounded-xl border border-dashed py-20">
          <CheckSquare className="size-12 text-muted-foreground/50" />
          <div className="text-center">
            <p className="font-medium">No tasks assigned to you</p>
            <p className="text-sm text-muted-foreground">
              When tasks are assigned to you, they will appear here.
            </p>
          </div>
        </div>
      )}

      {!isLoading && !isError && tasks.length > 0 && (
        <div className="flex flex-col gap-6">
          {projectNames.map((projectName, idx) => (
            <Card key={projectName}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <span>{projectName}</span>
                  <span className="ml-auto text-xs font-normal text-muted-foreground">
                    {grouped[projectName].length} task
                    {grouped[projectName].length !== 1 ? "s" : ""}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="flex flex-col">
                  {grouped[projectName].map((task, taskIdx) => (
                    <div key={task.id}>
                      <TaskRow task={task} />
                      {taskIdx < grouped[projectName].length - 1 && (
                        <Separator />
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
