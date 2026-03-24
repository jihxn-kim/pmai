import uuid

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.task import TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.common import PaginationMeta
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services import task_service

router = APIRouter(tags=["tasks"])


class PaginatedTaskResponse(BaseModel):
    data: list[TaskResponse]
    meta: PaginationMeta


@router.post(
    "/api/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    project_id: uuid.UUID,
    body: TaskCreate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.create_task(
        db,
        project_id=project_id,
        title=body.title,
        description=body.description,
        assignee_id=body.assignee_id,
        priority=body.priority,
        due_date=body.due_date,
    )
    return task


@router.get(
    "/api/projects/{project_id}/tasks",
    response_model=PaginatedTaskResponse,
)
async def list_tasks(
    project_id: uuid.UUID,
    status: TaskStatus | None = Query(default=None),
    assignee_id: uuid.UUID | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await task_service.list_tasks(
        db,
        project_id=project_id,
        status=status,
        assignee_id=assignee_id,
        priority=priority,
        page=page,
        per_page=per_page,
    )
    return result


@router.get(
    "/api/tasks/{task_id}",
    response_model=TaskResponse,
)
async def get_task(
    task_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.get_task(db, task_id)
    return task


@router.patch(
    "/api/tasks/{task_id}",
    response_model=TaskResponse,
)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.update_task(
        db,
        task_id,
        title=body.title,
        description=body.description,
        assignee_id=body.assignee_id,
        status=body.status,
        priority=body.priority,
        due_date=body.due_date,
    )
    return task


@router.delete(
    "/api/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    task_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await task_service.delete_task(db, task_id)
