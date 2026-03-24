"use client";

import { useDroppable } from "@dnd-kit/core";
import { KanbanCard } from "./kanban-card";
import { cn } from "@/lib/utils";

type TaskStatus = "todo" | "in_progress" | "review" | "done";

interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  priority: "low" | "medium" | "high" | "critical";
  due_date?: string;
  assignee?: {
    id: string;
    name: string;
    avatar_url?: string;
  };
}

interface KanbanColumnProps {
  status: TaskStatus;
  tasks: Task[];
  onCardClick?: (task: Task) => void;
}

const statusLabels: Record<TaskStatus, string> = {
  todo: "To Do",
  in_progress: "In Progress",
  review: "Review",
  done: "Done",
};

const columnColors: Record<TaskStatus, string> = {
  todo: "border-t-slate-400",
  in_progress: "border-t-blue-500",
  review: "border-t-yellow-500",
  done: "border-t-green-500",
};

export function KanbanColumn({ status, tasks, onCardClick }: KanbanColumnProps) {
  const { isOver, setNodeRef } = useDroppable({ id: status });

  return (
    <div className="flex min-w-[260px] flex-1 flex-col gap-3">
      {/* Column header */}
      <div className="flex items-center justify-between px-1">
        <span className="text-sm font-semibold text-foreground">
          {statusLabels[status]}
        </span>
        <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-muted px-1.5 text-xs font-medium text-muted-foreground">
          {tasks.length}
        </span>
      </div>

      {/* Droppable area */}
      <div
        ref={setNodeRef}
        className={cn(
          "flex flex-col gap-2 rounded-xl border-t-2 bg-muted/30 p-2 transition-colors min-h-[120px]",
          columnColors[status],
          isOver && "bg-muted/60 ring-1 ring-primary/20"
        )}
      >
        {tasks.map((task) => (
          <KanbanCard
            key={task.id}
            task={task}
            onClick={() => onCardClick?.(task)}
          />
        ))}

        {tasks.length === 0 && (
          <div className="flex flex-1 items-center justify-center py-8 text-xs text-muted-foreground">
            No tasks
          </div>
        )}
      </div>
    </div>
  );
}
