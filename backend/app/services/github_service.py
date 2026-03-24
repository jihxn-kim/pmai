import asyncio
import hashlib
import hmac
import time
import uuid
from datetime import datetime, timezone

import httpx
import jwt
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.activity_log import ActivityLog
from app.models.organization import Organization
from app.models.project import Project
from app.models.pull_request import PRState, PullRequest, PullRequestReviewer, ReviewState
from app.models.task import Task, TaskStatus
from app.models.user import User


async def get_installation_token(installation_id: int) -> str:
    """Create a JWT and exchange it for a GitHub App installation access token."""
    now = int(time.time())
    payload = {
        "iat": now - 60,  # issued 60s ago to allow clock drift
        "exp": now + 600,  # valid for 10 minutes
        "iss": settings.github_app_id,
    }
    # The private key may be stored with literal \n sequences; normalize them.
    private_key = settings.github_app_private_key.replace("\\n", "\n")
    app_jwt = jwt.encode(payload, private_key, algorithm="RS256")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
            },
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get installation token: {resp.text}",
            )
        return resp.json()["token"]


async def connect_github_repo(db: AsyncSession, project_id: uuid.UUID, repo_url: str) -> Project:
    """Connect a GitHub repository to a project and trigger initial sync."""
    # Parse owner/repo from URL
    # Expected format: https://github.com/owner/repo or https://github.com/owner/repo.git
    url = repo_url.rstrip("/").removesuffix(".git")
    parts = url.split("github.com/")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid GitHub repo URL")
    path_parts = parts[1].split("/")
    if len(path_parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid GitHub repo URL: missing owner/repo")
    owner, repo_name = path_parts[0], path_parts[1]

    # Get the project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get the org
    result = await db.execute(select(Organization).where(Organization.id == project.org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    if org.github_installation_id is None:
        raise HTTPException(
            status_code=400,
            detail="Organization has no GitHub App installation configured",
        )

    # Get installation access token
    token = await get_installation_token(org.github_installation_id)

    # Verify repo access via GitHub API
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo_name}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
        if resp.status_code == 404:
            raise HTTPException(
                status_code=400,
                detail="GitHub repository not found or not accessible",
            )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to access GitHub repository: {resp.text}",
            )
        repo_data = resp.json()

    # Save repo info on project
    project.github_repo_url = repo_url
    project.github_repo_id = repo_data["id"]
    await db.commit()
    await db.refresh(project)

    # Trigger initial sync as background task
    asyncio.create_task(initial_sync(project, owner, repo_name, token))

    return project


async def initial_sync(project: Project, owner: str, repo_name: str, token: str) -> None:
    """Background task: sync all PRs and issues from GitHub into the DB."""
    from app.database import async_session

    async with async_session() as db:
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            }
            async with httpx.AsyncClient() as client:
                # Fetch all PRs
                pr_resp = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo_name}/pulls",
                    params={"state": "all", "per_page": 100},
                    headers=headers,
                )
                if pr_resp.status_code == 200:
                    for pr_data in pr_resp.json():
                        github_pr_id = pr_data.get("id")
                        result = await db.execute(
                            select(PullRequest).where(
                                PullRequest.project_id == project.id,
                                PullRequest.github_pr_id == github_pr_id,
                            )
                        )
                        existing = result.scalar_one_or_none()
                        if existing is None:
                            state_str = pr_data.get("state", "open")
                            if pr_data.get("merged_at"):
                                pr_state = PRState.merged
                            elif state_str == "closed":
                                pr_state = PRState.closed
                            else:
                                pr_state = PRState.open

                            merged_at = None
                            if pr_data.get("merged_at"):
                                merged_at = datetime.fromisoformat(
                                    pr_data["merged_at"].replace("Z", "+00:00")
                                )

                            pr = PullRequest(
                                project_id=project.id,
                                github_pr_id=github_pr_id,
                                number=pr_data.get("number"),
                                title=pr_data.get("title", ""),
                                state=pr_state,
                                merged_at=merged_at,
                            )
                            db.add(pr)

                # Fetch all issues (skip PRs — they also appear in issues endpoint)
                issues_resp = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo_name}/issues",
                    params={"state": "all", "per_page": 100},
                    headers=headers,
                )
                if issues_resp.status_code == 200:
                    for issue_data in issues_resp.json():
                        # Skip entries that are actually PRs
                        if "pull_request" in issue_data:
                            continue
                        github_issue_id = issue_data.get("id")
                        result = await db.execute(
                            select(Task).where(
                                Task.project_id == project.id,
                                Task.github_issue_id == github_issue_id,
                            )
                        )
                        existing = result.scalar_one_or_none()
                        if existing is None:
                            task = Task(
                                project_id=project.id,
                                title=issue_data.get("title", ""),
                                description=issue_data.get("body", ""),
                                github_issue_id=github_issue_id,
                            )
                            db.add(task)

            await db.commit()
        except Exception:
            # Background task — swallow errors to avoid unhandled task exceptions
            await db.rollback()


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
