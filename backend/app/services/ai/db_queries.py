"""DB query functions for AI custom tools."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, TaskPriority
from app.models.project import Project, ProjectMember
from app.models.pull_request import PullRequest, PRState, ReviewState
from app.models.user import User


async def execute_db_query(db: AsyncSession, query_name: str, params: dict) -> dict:
    """Execute a named DB query and return serializable results."""
    project_id = uuid.UUID(params["project_id"])

    if query_name == "tasks":
        result = await db.execute(
            select(Task).where(Task.project_id == project_id).order_by(Task.created_at.desc())
        )
        tasks = result.scalars().all()
        return {
            "total": len(tasks),
            "tasks": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "assignee_id": str(t.assignee_id) if t.assignee_id else None,
                    "due_date": str(t.due_date) if t.due_date else None,
                    "github_issue_id": t.github_issue_id,
                }
                for t in tasks
            ],
        }

    elif query_name == "members":
        result = await db.execute(
            select(ProjectMember, User)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
        )
        members = result.all()
        return {
            "total": len(members),
            "members": [
                {
                    "user_id": str(pm.user_id),
                    "name": u.name,
                    "github_username": u.github_username,
                    "role": pm.role.value,
                    "expertise": u.expertise,
                }
                for pm, u in members
            ],
        }

    elif query_name == "issues":
        today = date.today()
        issues = []

        # Overdue tasks
        overdue = await db.execute(
            select(Task).where(
                Task.project_id == project_id,
                Task.due_date < today,
                Task.status != TaskStatus.done,
            )
        )
        for t in overdue.scalars():
            days = (today - t.due_date).days
            issues.append({
                "type": "overdue_task",
                "title": t.title,
                "days_overdue": days,
                "assignee_id": str(t.assignee_id) if t.assignee_id else None,
            })

        # Stale PRs (open > 7 days)
        stale_cutoff = today - timedelta(days=7)
        stale_prs = await db.execute(
            select(PullRequest).where(
                PullRequest.project_id == project_id,
                PullRequest.state == PRState.open,
            )
        )
        for pr in stale_prs.scalars():
            if pr.created_at and pr.created_at.date() < stale_cutoff:
                issues.append({
                    "type": "stale_pr",
                    "title": pr.title,
                    "pr_number": pr.number,
                })

        # Unassigned tasks
        unassigned = await db.execute(
            select(Task).where(
                Task.project_id == project_id,
                Task.assignee_id.is_(None),
                Task.status != TaskStatus.done,
            )
        )
        for t in unassigned.scalars():
            issues.append({"type": "unassigned_task", "title": t.title})

        return {"total": len(issues), "issues": issues}

    elif query_name == "progress":
        result = await db.execute(
            select(Task.status, func.count(Task.id))
            .where(Task.project_id == project_id)
            .group_by(Task.status)
        )
        counts = {row[0].value: row[1] for row in result.all()}
        total = sum(counts.values())
        done = counts.get("done", 0)
        return {
            "todo": counts.get("todo", 0),
            "in_progress": counts.get("in_progress", 0),
            "review": counts.get("review", 0),
            "done": done,
            "total": total,
            "progress_percent": round((done / total * 100), 1) if total > 0 else 0,
        }

    elif query_name == "pull_requests":
        result = await db.execute(
            select(PullRequest).where(PullRequest.project_id == project_id)
            .order_by(PullRequest.created_at.desc())
        )
        prs = result.scalars().all()
        return {
            "total": len(prs),
            "pull_requests": [
                {
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state.value,
                    "review_state": pr.review_state.value if pr.review_state else None,
                    "author_id": str(pr.author_id) if pr.author_id else None,
                }
                for pr in prs
            ],
        }

    elif query_name == "ai_reviews":
        from app.models.ai_review import AIReview
        result = await db.execute(
            select(AIReview).where(AIReview.project_id == project_id)
            .order_by(AIReview.created_at.desc())
            .limit(5)
        )
        reviews = result.scalars().all()
        return {
            "total": len(reviews),
            "reviews": [
                {
                    "id": str(r.id),
                    "type": r.type.value,
                    "status": r.status.value,
                    "summary": r.summary,
                    "created_at": str(r.created_at),
                    "completed_at": str(r.completed_at) if r.completed_at else None,
                }
                for r in reviews
            ],
        }

    elif query_name == "activity":
        from app.models.activity_log import ActivityLog
        result = await db.execute(
            select(ActivityLog).where(ActivityLog.project_id == project_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(20)
        )
        logs = result.scalars().all()
        return {
            "total": len(logs),
            "activities": [
                {
                    "event_type": log.event_type,
                    "title": log.title,
                    "description": log.description,
                    "actor": log.actor,
                    "created_at": str(log.created_at),
                }
                for log in logs
            ],
        }

    elif query_name == "org_projects":
        org_id = uuid.UUID(params["org_id"])
        result = await db.execute(
            select(Project).where(Project.org_id == org_id).order_by(Project.created_at.desc())
        )
        projects = result.scalars().all()
        return {
            "total": len(projects),
            "projects": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "description": p.description,
                    "status": p.status if hasattr(p, "status") else None,
                    "github_repo_url": p.github_repo_url,
                    "created_at": str(p.created_at),
                }
                for p in projects
            ],
        }

    return {"error": f"Unknown query: {query_name}"}
