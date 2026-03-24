"use client";

import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface Task {
  id: string;
  title: string;
  priority: "low" | "medium" | "high" | "critical";
  due_date?: string;
  assignee?: {
    id: string;
    name: string;
    avatar_url?: string;
  };
}

interface KanbanCardProps {
  task: Task;
  onClick?: () => void;
}

const priorityConfig: Record<
  string,
  { label: string; className: string }
> = {
  low: {
    label: "Low",
    className:
      "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
  },
  medium: {
    label: "Medium",
    className:
      "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  },
  high: {
    label: "High",
    className:
      "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300",
  },
  critical: {
    label: "Critical",
    className:
      "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  },
};

function isOverdue(dueDate: string): boolean {
  return new Date(dueDate) < new Date();
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export function KanbanCard({ task, onClick }: KanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({ id: task.id });

  const style = {
    transform: CSS.Translate.toString(transform),
  };

  const priority = priorityConfig[task.priority] ?? priorityConfig.medium;
  const overdue = task.due_date ? isOverdue(task.due_date) : false;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={cn(
        "rounded-lg border bg-card p-3 text-sm shadow-sm ring-1 ring-foreground/5 cursor-grab active:cursor-grabbing select-none",
        "hover:ring-foreground/15 transition-all",
        isDragging && "opacity-50 ring-primary/40"
      )}
      onClick={onClick}
    >
      <p className="font-medium leading-snug text-card-foreground mb-2 line-clamp-2">
        {task.title}
      </p>

      <div className="flex items-center justify-between gap-2">
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
            priority.className
          )}
        >
          {priority.label}
        </span>

        <div className="flex items-center gap-2">
          {task.due_date && (
            <span
              className={cn(
                "text-xs",
                overdue ? "text-red-500 font-medium" : "text-muted-foreground"
              )}
            >
              {new Date(task.due_date).toLocaleDateString()}
            </span>
          )}

          {task.assignee && (
            <Avatar size="sm">
              {task.assignee.avatar_url && (
                <AvatarImage
                  src={task.assignee.avatar_url}
                  alt={task.assignee.name}
                />
              )}
              <AvatarFallback>{getInitials(task.assignee.name)}</AvatarFallback>
            </Avatar>
          )}
        </div>
      </div>
    </div>
  );
}
