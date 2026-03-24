import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import PaginationMeta
from app.schemas.dashboard import DashboardResponse, IssuesResponse, ProgressResponse
from app.schemas.task import TaskResponse
from app.services import dashboard_service

router = APIRouter(tags=["dashboard"])


class PaginatedTaskResponse(BaseModel):
    data: list[TaskResponse]
    meta: PaginationMeta


@router.get(
    "/api/orgs/{org_id}/dashboard",
    response_model=DashboardResponse,
)
async def get_org_dashboard(
    org_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_service.get_org_dashboard(db, org_id)


@router.get(
    "/api/me/tasks",
    response_model=PaginatedTaskResponse,
)
async def get_my_tasks(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_service.get_my_tasks(
        db,
        user_id=current_user.id,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/api/projects/{project_id}/progress",
    response_model=ProgressResponse,
)
async def get_project_progress(
    project_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_service.get_project_progress(db, project_id)


@router.get(
    "/api/projects/{project_id}/issues",
    response_model=IssuesResponse,
)
async def get_project_issues(
    project_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_service.get_project_issues(db, project_id)
