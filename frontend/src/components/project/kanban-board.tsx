"use client";

import { useState } from "react";
import {
  DndContext,
  closestCenter,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { useTasks, useUpdateTask } from "@/hooks/use-tasks";
import { useQueryClient } from "@tanstack/react-query";
import { KanbanColumn } from "./kanban-column";
import { KanbanCard } from "./kanban-card";
import { TaskModal } from "@/components/task/task-modal";

type TaskStatus = "todo" | "in_progress" | "review" | "done";

const STATUSES: TaskStatus[] = ["todo", "in_progress", "review", "done"];

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

interface KanbanBoardProps {
  projectId: string;
}

export function KanbanBoard({ projectId }: KanbanBoardProps) {
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useTasks(projectId);
  const updateTask = useUpdateTask();

  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const tasks: Task[] = Array.isArray(data)
    ? data
    : Array.isArray((data as { data?: Task[] })?.data)
      ? (data as { data: Task[] }).data
      : [];

  const grouped = STATUSES.reduce<Record<TaskStatus, Task[]>>(
    (acc, status) => {
      acc[status] = tasks.filter((t) => t.status === status);
      return acc;
    },
    { todo: [], in_progress: [], review: [], done: [] }
  );

  function handleDragStart(event: DragStartEvent) {
    const task = tasks.find((t) => t.id === event.active.id);
    setActiveTask(task ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveTask(null);

    if (!over) return;

    const taskId = active.id as string;
    const newStatus = over.id as TaskStatus;

    const task = tasks.find((t) => t.id === taskId);
    if (!task || task.status === newStatus) return;

    // Optimistic update: mutate the cache immediately
    queryClient.setQueryData(
      ["tasks", projectId, undefined],
      (old: Task[] | { results: Task[] } | undefined) => {
        if (!old) return old;
        if (Array.isArray(old)) {
          return old.map((t) =>
            t.id === taskId ? { ...t, status: newStatus } : t
          );
        }
        return {
          ...old,
          results: old.results.map((t: Task) =>
            t.id === taskId ? { ...t, status: newStatus } : t
          ),
        };
      }
    );

    updateTask.mutate(
      { taskId, data: { status: newStatus } },
      {
        onError: () => {
          // Revert on error by invalidating
          queryClient.invalidateQueries({ queryKey: ["tasks", projectId] });
        },
      }
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
        Loading tasks...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-destructive">
        Failed to load tasks.
      </div>
    );
  }

  return (
    <>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex gap-4 overflow-x-auto pb-4">
          {STATUSES.map((status) => (
            <KanbanColumn
              key={status}
              status={status}
              tasks={grouped[status]}
              onCardClick={(task) => {
                setEditingTask(task);
                setIsModalOpen(true);
              }}
            />
          ))}
        </div>

        <DragOverlay>
          {activeTask ? <KanbanCard task={activeTask} /> : null}
        </DragOverlay>
      </DndContext>

      <TaskModal
        projectId={projectId}
        task={editingTask ?? undefined}
        open={isModalOpen}
        onOpenChange={(open) => {
          setIsModalOpen(open);
          if (!open) setEditingTask(null);
        }}
      />
    </>
  );
}
