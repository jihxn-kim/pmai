import math
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMember
from app.models.pull_request import PRState, PullRequest, ReviewState
from app.models.task import Task, TaskStatus
from app.schemas.dashboard import (
    DashboardResponse,
    IssueItem,
    IssuesResponse,
    ProgressResponse,
    ProjectSummary,
    StatusDistribution,
)


async def get_task_distribution(db: AsyncSession, project_id: uuid.UUID) -> StatusDistribution:
    """GROUP BY task.status, count tasks, calculate progress."""
    result = await db.execute(
        select(Task.status, func.count(Task.id).label("cnt"))
        .where(Task.project_id == project_id)
        .group_by(Task.status)
    )
    rows = result.all()

    counts = {TaskStatus.todo: 0, TaskStatus.in_progress: 0, TaskStatus.review: 0, TaskStatus.done: 0}
    for row in rows:
        counts[row.status] = row.cnt

    total = sum(counts.values())
    done_count = counts[TaskStatus.done]
    progress = (done_count / total * 100) if total > 0 else 0.0

    return StatusDistribution(
        todo=counts[TaskStatus.todo],
        in_progress=counts[TaskStatus.in_progress],
        review=counts[TaskStatus.review],
        done=done_count,
        total=total,
        progress=round(progress, 2),
    )


async def get_org_dashboard(db: AsyncSession, org_id: uuid.UUID) -> DashboardResponse:
    """Get all projects for org, with task distribution and member count for each."""
    result = await db.execute(
        select(Project).where(Project.org_id == org_id)
    )
    projects = list(result.scalars().all())

    summaries = []
    for project in projects:
        distribution = await get_task_distribution(db, project.id)

        member_result = await db.execute(
            select(func.count(ProjectMember.user_id)).where(
                ProjectMember.project_id == project.id
            )
        )
        member_count = member_result.scalar_one()

        summaries.append(
            ProjectSummary(
                id=project.id,
                name=project.name,
                status=project.status,
                progress=distribution,
                member_count=member_count,
            )
        )

    return DashboardResponse(
        projects=summaries,
        total_projects=len(summaries),
    )


async def get_project_progress(db: AsyncSession, project_id: uuid.UUID) -> ProgressResponse:
    """Return ProgressResponse with distribution for a project."""
    distribution = await get_task_distribution(db, project_id)
    return ProgressResponse(
        project_id=project_id,
        distribution=distribution,
    )


async def get_my_tasks(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """Tasks where assignee_id=user_id AND status != done, ordered by due_date asc (nulls last), paginated."""
    query = (
        select(Task)
        .where(Task.assignee_id == user_id)
        .where(Task.status != TaskStatus.done)
        .order_by(Task.due_date.asc().nulls_last())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

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


async def get_project_issues(db: AsyncSession, project_id: uuid.UUID) -> IssuesResponse:
    """Detect issues: overdue tasks, stale PRs, pending reviews, unassigned tasks."""
    today = date.today()
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    three_days_ago = now - timedelta(days=3)

    items: list[IssueItem] = []

    # Overdue tasks: due_date < today AND status != done
    overdue_result = await db.execute(
        select(Task).where(
            Task.project_id == project_id,
            Task.due_date < today,
            Task.status != TaskStatus.done,
        )
    )
    overdue_tasks = overdue_result.scalars().all()
    for task in overdue_tasks:
        items.append(
            IssueItem(
                type="overdue_task",
                title=task.title,
                detail={
                    "task_id": str(task.id),
                    "due_date": str(task.due_date),
                    "status": task.status.value,
                },
            )
        )

    # Stale PRs: state == open AND created_at < 7 days ago
    stale_pr_result = await db.execute(
        select(PullRequest).where(
            PullRequest.project_id == project_id,
            PullRequest.state == PRState.open,
            PullRequest.created_at < seven_days_ago,
        )
    )
    stale_prs = stale_pr_result.scalars().all()
    for pr in stale_prs:
        items.append(
            IssueItem(
                type="stale_pr",
                title=pr.title,
                detail={
                    "pr_id": str(pr.id),
                    "number": pr.number,
                    "created_at": pr.created_at.isoformat(),
                },
            )
        )

    # Pending reviews: state == open AND created_at < 3 days ago AND review_state == pending
    pending_review_result = await db.execute(
        select(PullRequest).where(
            PullRequest.project_id == project_id,
            PullRequest.state == PRState.open,
            PullRequest.created_at < three_days_ago,
            PullRequest.review_state == ReviewState.pending,
        )
    )
    pending_reviews = pending_review_result.scalars().all()
    for pr in pending_reviews:
        items.append(
            IssueItem(
                type="pending_review",
                title=pr.title,
                detail={
                    "pr_id": str(pr.id),
                    "number": pr.number,
                    "created_at": pr.created_at.isoformat(),
                },
            )
        )

    # Unassigned tasks: assignee_id IS NULL AND status != done
    unassigned_result = await db.execute(
        select(Task).where(
            Task.project_id == project_id,
            Task.assignee_id.is_(None),
            Task.status != TaskStatus.done,
        )
    )
    unassigned_tasks = unassigned_result.scalars().all()
    for task in unassigned_tasks:
        items.append(
            IssueItem(
                type="unassigned_task",
                title=task.title,
                detail={
                    "task_id": str(task.id),
                    "status": task.status.value,
                },
            )
        )

    return IssuesResponse(items=items, total=len(items))
