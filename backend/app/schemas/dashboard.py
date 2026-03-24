import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.project import ProjectStatus


class StatusDistribution(BaseModel):
    todo: int = 0
    in_progress: int = 0
    review: int = 0
    done: int = 0
    total: int = 0
    progress: float = 0.0


class ProjectSummary(BaseModel):
    id: uuid.UUID
    name: str
    status: ProjectStatus
    progress: StatusDistribution
    member_count: int


class DashboardResponse(BaseModel):
    projects: list[ProjectSummary]
    total_projects: int


class ProgressResponse(BaseModel):
    project_id: uuid.UUID
    distribution: StatusDistribution


class IssueItem(BaseModel):
    type: str  # overdue_task, stale_pr, pending_review, unassigned_task
    title: str
    detail: dict


class IssuesResponse(BaseModel):
    items: list[IssueItem]
    total: int
