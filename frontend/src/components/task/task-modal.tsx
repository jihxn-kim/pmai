"use client";

import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useCreateTask, useUpdateTask } from "@/hooks/use-tasks";
import { useProjectMembers } from "@/hooks/use-projects";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Member {
  id: string;
  name: string;
  avatar_url?: string;
}

interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  due_date?: string;
  assignee?: {
    id: string;
    name: string;
    avatar_url?: string;
  };
}

interface TaskModalProps {
  projectId: string;
  task?: Task;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TaskModal({
  projectId,
  task,
  open,
  onOpenChange,
}: TaskModalProps) {
  const queryClient = useQueryClient();
  const createTask = useCreateTask(projectId);
  const updateTask = useUpdateTask();
  const { data: membersData } = useProjectMembers(projectId);

  const members: Member[] = Array.isArray(membersData)
    ? membersData
    : (membersData as { results?: Member[] })?.results ?? [];

  const isEdit = !!task;

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("medium");
  const [assigneeId, setAssigneeId] = useState("");
  const [dueDate, setDueDate] = useState("");

  // Populate form when editing
  useEffect(() => {
    if (task) {
      setTitle(task.title ?? "");
      setDescription(task.description ?? "");
      setPriority(task.priority ?? "medium");
      setAssigneeId(task.assignee?.id ?? "");
      setDueDate(task.due_date ? task.due_date.split("T")[0] : "");
    } else {
      setTitle("");
      setDescription("");
      setPriority("medium");
      setAssigneeId("");
      setDueDate("");
    }
  }, [task, open]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const payload: Record<string, unknown> = {
      title,
      description: description || undefined,
      priority,
      assignee_id: assigneeId && assigneeId !== "unassigned" ? assigneeId : undefined,
      due_date: dueDate || undefined,
    };

    if (isEdit && task) {
      updateTask.mutate(
        { taskId: task.id, data: payload },
        {
          onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tasks", projectId] });
            onOpenChange(false);
          },
        }
      );
    } else {
      createTask.mutate(payload, {
        onSuccess: () => {
          onOpenChange(false);
        },
      });
    }
  }

  const isPending = createTask.isPending || updateTask.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Task" : "New Task"}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Title */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="task-title">Title</Label>
            <Input
              id="task-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Task title"
              required
            />
          </div>

          {/* Description */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="task-description">Description</Label>
            <Textarea
              id="task-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
              rows={3}
            />
          </div>

          {/* Priority */}
          <div className="flex flex-col gap-1.5">
            <Label>Priority</Label>
            <Select value={priority} onValueChange={(v) => { if (v) setPriority(v); }}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Assignee */}
          <div className="flex flex-col gap-1.5">
            <Label>Assignee</Label>
            <Select
              value={assigneeId || "unassigned"}
              onValueChange={(v) => {
                if (v !== null) setAssigneeId(v === "unassigned" ? "" : v);
              }}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Unassigned" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="unassigned">Unassigned</SelectItem>
                {members.map((member) => (
                  <SelectItem key={member.id} value={member.id}>
                    {member.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Due date */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="task-due-date">Due Date</Label>
            <Input
              id="task-due-date"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isPending || !title.trim()}>
              {isPending ? "Saving…" : isEdit ? "Save Changes" : "Create Task"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
