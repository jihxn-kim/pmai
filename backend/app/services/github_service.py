import hashlib
import hmac
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.activity_log import ActivityLog
from app.models.project import Project
from app.models.pull_request import PRState, PullRequest, PullRequestReviewer, ReviewState
from app.models.task import Task, TaskStatus
from app.models.user import User


async def verify_webhook_signature(request: Request) -> bytes:
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    return body


async def resolve_github_user(db: AsyncSession, github_user: dict) -> uuid.UUID | None:
    if not github_user:
        return None
    result = await db.execute(select(User).where(User.github_id == github_user["id"]))
    user = result.scalar_one_or_none()
    return user.id if user else None


async def find_project_by_repo_id(db: AsyncSession, repo_id: int) -> Project | None:
    result = await db.execute(select(Project).where(Project.github_repo_id == repo_id))
    return result.scalar_one_or_none()


def _parse_pr_state(action: str, payload: dict) -> PRState:
    if payload.get("pull_request", {}).get("merged"):
        return PRState.merged
    state = payload.get("pull_request", {}).get("state", "open")
    if state == "closed":
        return PRState.closed
    return PRState.open


async def handle_pull_request(db: AsyncSession, payload: dict) -> None:
    repo = payload.get("repository", {})
    repo_id = repo.get("id")
    project = await find_project_by_repo_id(db, repo_id)
    if project is None:
        return

    pr_data = payload.get("pull_request", {})
    action = payload.get("action", "")

    github_pr_id = pr_data.get("id")
    number = pr_data.get("number")
    title = pr_data.get("title", "")
    author_id = await resolve_github_user(db, pr_data.get("user"))

    state = _parse_pr_state(action, payload)
    merged_at = None
    if pr_data.get("merged_at"):
        merged_at = datetime.fromisoformat(pr_data["merged_at"].replace("Z", "+00:00"))

    # Upsert PullRequest
    result = await db.execute(
        select(PullRequest).where(
            PullRequest.project_id == project.id,
            PullRequest.github_pr_id == github_pr_id,
        )
    )
    pr = result.scalar_one_or_none()

    if pr is None:
        pr = PullRequest(
            project_id=project.id,
            github_pr_id=github_pr_id,
            number=number,
            title=title,
            state=state,
            author_id=author_id,
            merged_at=merged_at,
        )
        db.add(pr)
        await db.flush()
    else:
        pr.title = title
        pr.state = state
        pr.author_id = author_id
        pr.merged_at = merged_at

    # Sync requested_reviewers
    requested_reviewers = pr_data.get("requested_reviewers", [])
    for reviewer_data in requested_reviewers:
        reviewer_user_id = await resolve_github_user(db, reviewer_data)
        if reviewer_user_id is None:
            continue
        result = await db.execute(
            select(PullRequestReviewer).where(
                PullRequestReviewer.pr_id == pr.id,
                PullRequestReviewer.user_id == reviewer_user_id,
            )
        )
        existing_reviewer = result.scalar_one_or_none()
        if existing_reviewer is None:
            reviewer_record = PullRequestReviewer(
                pr_id=pr.id,
                user_id=reviewer_user_id,
                state=ReviewState.pending,
            )
            db.add(reviewer_record)

    # Create ActivityLog
    log = ActivityLog(
        project_id=project.id,
        user_id=author_id,
        action=f"pull_request.{action}",
        detail={
            "pr_number": number,
            "title": title,
            "state": state.value,
            "github_pr_id": github_pr_id,
        },
    )
    db.add(log)
    await db.commit()


async def handle_issues(db: AsyncSession, payload: dict) -> None:
    repo = payload.get("repository", {})
    repo_id = repo.get("id")
    project = await find_project_by_repo_id(db, repo_id)
    if project is None:
        return

    action = payload.get("action", "")
    issue_data = payload.get("issue", {})
    issue_id = issue_data.get("id")
    issue_number = issue_data.get("number")
    issue_title = issue_data.get("title", "")
    issue_body = issue_data.get("body", "")
    sender = payload.get("sender", {})
    user_id = await resolve_github_user(db, sender)

    if action == "opened":
        task = Task(
            project_id=project.id,
            title=issue_title,
            description=issue_body,
            github_issue_id=issue_id,
        )
        db.add(task)
        await db.flush()

    elif action == "closed":
        result = await db.execute(
            select(Task).where(
                Task.project_id == project.id,
                Task.github_issue_id == issue_id,
            )
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = TaskStatus.done

    elif action == "edited":
        result = await db.execute(
            select(Task).where(
                Task.project_id == project.id,
                Task.github_issue_id == issue_id,
            )
        )
        task = result.scalar_one_or_none()
        if task:
            task.title = issue_title
            task.description = issue_body

    log = ActivityLog(
        project_id=project.id,
        user_id=user_id,
        action=f"issue.{action}",
        detail={
            "issue_number": issue_number,
            "title": issue_title,
            "github_issue_id": issue_id,
        },
    )
    db.add(log)
    await db.commit()


async def handle_push(db: AsyncSession, payload: dict) -> None:
    repo = payload.get("repository", {})
    repo_id = repo.get("id")
    project = await find_project_by_repo_id(db, repo_id)
    if project is None:
        return

    ref = payload.get("ref", "")
    pusher = payload.get("pusher", {})
    pusher_name = pusher.get("name", "")
    commits = payload.get("commits", [])[:10]
    commit_summaries = [
        {"sha": c.get("id", "")[:7], "message": c.get("message", "")}
        for c in commits
    ]

    sender = payload.get("sender", {})
    user_id = await resolve_github_user(db, sender)

    log = ActivityLog(
        project_id=project.id,
        user_id=user_id,
        action="push",
        detail={
            "ref": ref,
            "pusher": pusher_name,
            "commits": commit_summaries,
        },
    )
    db.add(log)
    await db.commit()


async def handle_pull_request_review(db: AsyncSession, payload: dict) -> None:
    repo = payload.get("repository", {})
    repo_id = repo.get("id")
    project = await find_project_by_repo_id(db, repo_id)
    if project is None:
        return

    review_data = payload.get("review", {})
    pr_data = payload.get("pull_request", {})
    github_pr_id = pr_data.get("id")
    reviewer_github_user = review_data.get("user", {})
    reviewer_user_id = await resolve_github_user(db, reviewer_github_user)

    github_review_state = review_data.get("state", "").lower()
    if github_review_state == "approved":
        review_state = ReviewState.approved
    elif github_review_state == "changes_requested":
        review_state = ReviewState.changes_requested
    else:
        review_state = ReviewState.pending

    submitted_at = None
    if review_data.get("submitted_at"):
        submitted_at = datetime.fromisoformat(
            review_data["submitted_at"].replace("Z", "+00:00")
        )

    # Find the PR
    result = await db.execute(
        select(PullRequest).where(
            PullRequest.project_id == project.id,
            PullRequest.github_pr_id == github_pr_id,
        )
    )
    pr = result.scalar_one_or_none()
    if pr is None:
        return

    # Upsert PullRequestReviewer
    if reviewer_user_id is not None:
        result = await db.execute(
            select(PullRequestReviewer).where(
                PullRequestReviewer.pr_id == pr.id,
                PullRequestReviewer.user_id == reviewer_user_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            reviewer_record = PullRequestReviewer(
                pr_id=pr.id,
                user_id=reviewer_user_id,
                state=review_state,
                submitted_at=submitted_at,
            )
            db.add(reviewer_record)
        else:
            existing.state = review_state
            existing.submitted_at = submitted_at

    # Update PR review_state
    pr.review_state = review_state

    # Create ActivityLog
    sender = payload.get("sender", {})
    user_id = await resolve_github_user(db, sender)

    log = ActivityLog(
        project_id=project.id,
        user_id=user_id,
        action="pull_request_review.submitted",
        detail={
            "pr_number": pr_data.get("number"),
            "review_state": review_state.value,
            "github_pr_id": github_pr_id,
        },
    )
    db.add(log)
    await db.commit()
