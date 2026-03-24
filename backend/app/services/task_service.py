import math
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskPriority, TaskStatus


async def create_task(
    db: AsyncSession,
    project_id: uuid.UUID,
    title: str,
    description: str | None = None,
    assignee_id: uuid.UUID | None = None,
    priority: TaskPriority = TaskPriority.medium,
    due_date=None,
) -> Task:
    task = Task(
        project_id=project_id,
        title=title,
        description=description,
        assignee_id=assignee_id,
        priority=priority,
        due_date=due_date,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def list_tasks(
    db: AsyncSession,
    project_id: uuid.UUID,
    status: TaskStatus | None = None,
    assignee_id: uuid.UUID | None = None,
    priority: TaskPriority | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    query = select(Task).where(Task.project_id == project_id)

    if status is not None:
        query = query.where(Task.status == status)
    if assignee_id is not None:
        query = query.where(Task.assignee_id == assignee_id)
    if priority is not None:
        query = query.where(Task.priority == priority)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginate
    offset = (page - 1) * per_page
    paginated_query = query.offset(offset).limit(per_page)
    result = await db.execute(paginated_query)
    tasks = list(result.scalars().all())

    total_pages = math.ceil(total / per_page) if total > 0 else 1

    return {
        "data": tasks,
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        },
    }


async def get_task(db: AsyncSession, task_id: uuid.UUID) -> Task:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


async def update_task(
    db: AsyncSession,
    task_id: uuid.UUID,
    **kwargs,
) -> Task:
    task = await get_task(db, task_id)
    for key, value in kwargs.items():
        if value is not None:
            setattr(task, key, value)
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task_id: uuid.UUID) -> None:
    task = await get_task(db, task_id)
    await db.delete(task)
    await db.commit()
