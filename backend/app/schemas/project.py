import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.project import ProjectRole, ProjectStatus


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None
    start_date: date | None = None
    end_date: date | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str | None
    status: ProjectStatus
    github_repo_url: str | None
    github_repo_id: int | None
    start_date: date | None
    end_date: date | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectMemberAdd(BaseModel):
    github_username: str
    role: ProjectRole = ProjectRole.developer


class ProjectMemberUpdate(BaseModel):
    role: ProjectRole


class ProjectMemberResponse(BaseModel):
    user_id: uuid.UUID
    github_username: str
    name: str
    avatar_url: str | None
    role: ProjectRole
    created_at: datetime
