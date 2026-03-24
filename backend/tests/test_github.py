import hashlib
import hmac
import json
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.organization import Organization, OrgMember
from app.models.project import Project
from app.models.pull_request import PullRequest, PRState
from app.models.activity_log import ActivityLog
from app.models.task import Task


def make_signature(body: bytes, secret: str = None) -> str:
    secret = secret or settings.github_webhook_secret or "test-secret"
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def webhook_headers(body: bytes, event: str, secret: str = None) -> dict:
    return {
        "X-Hub-Signature-256": make_signature(body, secret),
        "X-GitHub-Event": event,
        "Content-Type": "application/json",
    }


@pytest_asyncio.fixture
async def test_org_with_project(db_session: AsyncSession, test_user):
    """Create an org + project with github_repo_id set."""
    org = Organization(
        name="Webhook Org",
        slug="webhook-org",
        owner_id=test_user.id,
    )
    db_session.add(org)
    await db_session.flush()

    member = OrgMember(
        org_id=org.id,
        user_id=test_user.id,
        role="owner",
    )
    db_session.add(member)

    project = Project(
        org_id=org.id,
        name="Webhook Project",
        github_repo_id=99999,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return org, project


@pytest.mark.asyncio
async def test_webhook_invalid_signature(client: AsyncClient):
    payload = json.dumps({"action": "opened"}).encode()
    headers = {
        "X-Hub-Signature-256": "sha256=invalidsignature",
        "X-GitHub-Event": "pull_request",
        "Content-Type": "application/json",
    }
    resp = await client.post("/api/webhooks/github", content=payload, headers=headers)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_pull_request_opened(
    client: AsyncClient, db_session: AsyncSession, test_org_with_project
):
    org, project = test_org_with_project

    payload = {
        "action": "opened",
        "number": 1,
        "pull_request": {
            "id": 111111,
            "number": 1,
            "title": "Add new feature",
            "state": "open",
            "merged": False,
            "merged_at": None,
            "user": {"id": 99999, "login": "unknown-gh-user"},
            "requested_reviewers": [],
        },
        "repository": {
            "id": 99999,
            "name": "webhook-project",
        },
        "sender": {"id": 99999, "login": "unknown-gh-user"},
    }

    body = json.dumps(payload).encode()
    secret = settings.github_webhook_secret or "test-secret"
    # Temporarily override if empty
    if not settings.github_webhook_secret:
        # Patch to use our test secret
        original_secret = settings.github_webhook_secret
        settings.github_webhook_secret = "test-secret"

    headers = webhook_headers(body, "pull_request", settings.github_webhook_secret or "test-secret")
    resp = await client.post("/api/webhooks/github", content=body, headers=headers)
    assert resp.status_code == 200, resp.text

    result = await db_session.execute(
        select(PullRequest).where(PullRequest.project_id == project.id)
    )
    prs = result.scalars().all()
    assert len(prs) == 1
    assert prs[0].github_pr_id == 111111
    assert prs[0].title == "Add new feature"
    assert prs[0].state == PRState.open


@pytest.mark.asyncio
async def test_webhook_issue_opened(
    client: AsyncClient, db_session: AsyncSession, test_org_with_project
):
    org, project = test_org_with_project

    payload = {
        "action": "opened",
        "issue": {
            "id": 222222,
            "number": 5,
            "title": "Bug: something is broken",
            "body": "Description of the bug",
        },
        "repository": {
            "id": 99999,
            "name": "webhook-project",
        },
        "sender": {"id": 99999, "login": "unknown-gh-user"},
    }

    body = json.dumps(payload).encode()
    headers = webhook_headers(body, "issues", settings.github_webhook_secret or "test-secret")
    resp = await client.post("/api/webhooks/github", content=body, headers=headers)
    assert resp.status_code == 200, resp.text

    result = await db_session.execute(
        select(Task).where(Task.project_id == project.id)
    )
    tasks = result.scalars().all()
    assert len(tasks) == 1
    assert tasks[0].title == "Bug: something is broken"
    assert tasks[0].github_issue_id == 222222


@pytest.mark.asyncio
async def test_webhook_push(
    client: AsyncClient, db_session: AsyncSession, test_org_with_project
):
    org, project = test_org_with_project

    payload = {
        "ref": "refs/heads/main",
        "pusher": {"name": "testpusher"},
        "commits": [
            {"id": "abc1234def5678", "message": "Fix bug"},
            {"id": "bcd2345efg6789", "message": "Add feature"},
        ],
        "repository": {
            "id": 99999,
            "name": "webhook-project",
        },
        "sender": {"id": 99999, "login": "unknown-gh-user"},
    }

    body = json.dumps(payload).encode()
    headers = webhook_headers(body, "push", settings.github_webhook_secret or "test-secret")
    resp = await client.post("/api/webhooks/github", content=body, headers=headers)
    assert resp.status_code == 200, resp.text

    result = await db_session.execute(
        select(ActivityLog).where(
            ActivityLog.project_id == project.id,
            ActivityLog.action == "push",
        )
    )
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].detail["ref"] == "refs/heads/main"
    assert logs[0].detail["pusher"] == "testpusher"
    assert len(logs[0].detail["commits"]) == 2
    assert logs[0].detail["commits"][0]["sha"] == "abc1234"


@pytest.mark.asyncio
async def test_list_pulls(
    client: AsyncClient, db_session: AsyncSession, test_org_with_project
):
    org, project = test_org_with_project

    # Create a PR directly in DB
    pr = PullRequest(
        project_id=project.id,
        github_pr_id=333333,
        number=10,
        title="Test PR",
        state=PRState.open,
    )
    db_session.add(pr)
    await db_session.commit()

    resp = await client.get(f"/api/projects/{project.id}/pulls")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["github_pr_id"] == 333333
    assert data[0]["title"] == "Test PR"


@pytest.mark.asyncio
async def test_list_activity(
    client: AsyncClient, db_session: AsyncSession, test_org_with_project
):
    org, project = test_org_with_project

    # Create some activity logs
    for i in range(3):
        log = ActivityLog(
            project_id=project.id,
            user_id=None,
            action=f"test.action.{i}",
            detail={"index": i},
        )
        db_session.add(log)
    await db_session.commit()

    resp = await client.get(f"/api/projects/{project.id}/activity?limit=2")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "data" in body
    assert "next_cursor" in body
    assert len(body["data"]) == 2
    assert body["next_cursor"] is not None

    # Use the cursor to get next page
    cursor = body["next_cursor"]
    resp2 = await client.get(
        f"/api/projects/{project.id}/activity?limit=2&cursor={cursor}"
    )
    assert resp2.status_code == 200, resp2.text
    body2 = resp2.json()
    assert "data" in body2
    assert len(body2["data"]) == 1
    assert body2["next_cursor"] is None
