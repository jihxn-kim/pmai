import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.task import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    assignee_id: uuid.UUID | None = None
    priority: TaskPriority = TaskPriority.medium
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee_id: uuid.UUID | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    assignee_id: uuid.UUID | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    github_issue_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
