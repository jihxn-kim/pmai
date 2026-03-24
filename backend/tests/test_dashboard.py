import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pull_request import PRState, PullRequest, ReviewState
from app.models.task import Task, TaskStatus


@pytest_asyncio.fixture
async def test_org(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/orgs/",
        json={"name": "Dashboard Org", "slug": "dashboard-org"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest_asyncio.fixture
async def test_project(client: AsyncClient, auth_headers, test_org):
    resp = await client.post(
        f"/api/orgs/{test_org['id']}/projects",
        json={"name": "Dashboard Project"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_progress_no_tasks(client: AsyncClient, auth_headers, test_project):
    """Project with no tasks should have progress=0."""
    resp = await client.get(
        f"/api/projects/{test_project['id']}/progress",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["project_id"] == test_project["id"]
    dist = data["distribution"]
    assert dist["total"] == 0
    assert dist["progress"] == 0.0
    assert dist["todo"] == 0
    assert dist["in_progress"] == 0
    assert dist["review"] == 0
    assert dist["done"] == 0


@pytest.mark.asyncio
async def test_progress_with_tasks(
    client: AsyncClient, auth_headers, test_project, db_session: AsyncSession
):
    """Project with tasks should show correct distribution."""
    import uuid as _uuid
    project_id = _uuid.UUID(test_project["id"])

    # Create tasks directly in DB with specific statuses
    tasks_data = [
        TaskStatus.todo,
        TaskStatus.todo,
        TaskStatus.in_progress,
        TaskStatus.review,
        TaskStatus.done,
        TaskStatus.done,
    ]
    for status in tasks_data:
        task = Task(
            project_id=project_id,
            title=f"Task {status.value}",
            status=status,
        )
        db_session.add(task)
    await db_session.commit()

    resp = await client.get(
        f"/api/projects/{test_project['id']}/progress",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    dist = data["distribution"]
    assert dist["total"] == 6
    assert dist["todo"] == 2
    assert dist["in_progress"] == 1
    assert dist["review"] == 1
    assert dist["done"] == 2
    # 2/6 * 100 = 33.33...
    assert abs(dist["progress"] - 33.33) < 0.1


@pytest.mark.asyncio
async def test_org_dashboard(
    client: AsyncClient, auth_headers, test_org, test_project, db_session: AsyncSession
):
    """Org dashboard should list projects with summaries."""
    import uuid as _uuid
    project_id = _uuid.UUID(test_project["id"])

    # Add a done task
    task = Task(
        project_id=project_id,
        title="Done task",
        status=TaskStatus.done,
    )
    db_session.add(task)
    await db_session.commit()

    resp = await client.get(
        f"/api/orgs/{test_org['id']}/dashboard",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_projects"] >= 1
    project_ids = [p["id"] for p in data["projects"]]
    assert test_project["id"] in project_ids

    # Find our project summary
    summary = next(p for p in data["projects"] if p["id"] == test_project["id"])
    assert "progress" in summary
    assert "member_count" in summary
    assert summary["member_count"] >= 1
    assert summary["progress"]["done"] == 1


@pytest.mark.asyncio
async def test_my_tasks(
    client: AsyncClient, auth_headers, test_user, test_project, db_session: AsyncSession
):
    """GET /api/me/tasks returns only tasks assigned to the current user, excluding done."""
    import uuid as _uuid
    project_id = _uuid.UUID(test_project["id"])
    user_id = test_user.id

    # Assigned, not done
    assigned_todo = Task(
        project_id=project_id,
        title="My todo task",
        assignee_id=user_id,
        status=TaskStatus.todo,
    )
    # Assigned but done (should NOT appear)
    assigned_done = Task(
        project_id=project_id,
        title="My done task",
        assignee_id=user_id,
        status=TaskStatus.done,
    )
    # Not assigned (should NOT appear)
    unassigned = Task(
        project_id=project_id,
        title="Unassigned task",
        assignee_id=None,
        status=TaskStatus.todo,
    )
    db_session.add_all([assigned_todo, assigned_done, unassigned])
    await db_session.commit()

    resp = await client.get(
        "/api/me/tasks",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    titles = [t["title"] for t in body["data"]]
    assert "My todo task" in titles
    assert "My done task" not in titles
    assert "Unassigned task" not in titles


@pytest.mark.asyncio
async def test_project_issues_overdue(
    client: AsyncClient, auth_headers, test_project, db_session: AsyncSession
):
    """Issues endpoint should detect overdue tasks."""
    import uuid as _uuid
    project_id = _uuid.UUID(test_project["id"])

    # Overdue task: due_date in the past, not done
    overdue_task = Task(
        project_id=project_id,
        title="Overdue Task",
        status=TaskStatus.in_progress,
        due_date=date.today() - timedelta(days=3),
    )
    # Not overdue (future due date)
    future_task = Task(
        project_id=project_id,
        title="Future Task",
        status=TaskStatus.todo,
        due_date=date.today() + timedelta(days=7),
    )
    db_session.add_all([overdue_task, future_task])
    await db_session.commit()

    resp = await client.get(
        f"/api/projects/{test_project['id']}/issues",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "items" in data
    assert "total" in data

    overdue_items = [i for i in data["items"] if i["type"] == "overdue_task"]
    titles = [i["title"] for i in overdue_items]
    assert "Overdue Task" in titles
    assert "Future Task" not in titles


@pytest.mark.asyncio
async def test_project_issues_unassigned(
    client: AsyncClient, auth_headers, test_project, db_session: AsyncSession
):
    """Issues endpoint should detect unassigned tasks."""
    import uuid as _uuid
    project_id = _uuid.UUID(test_project["id"])

    unassigned = Task(
        project_id=project_id,
        title="Unassigned Issue Task",
        assignee_id=None,
        status=TaskStatus.todo,
    )
    db_session.add(unassigned)
    await db_session.commit()

    resp = await client.get(
        f"/api/projects/{test_project['id']}/issues",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    unassigned_items = [i for i in data["items"] if i["type"] == "unassigned_task"]
    titles = [i["title"] for i in unassigned_items]
    assert "Unassigned Issue Task" in titles


@pytest.mark.asyncio
async def test_project_issues_stale_pr(
    client: AsyncClient, auth_headers, test_project, db_session: AsyncSession
):
    """Issues endpoint should detect stale PRs (open and older than 7 days)."""
    import uuid as _uuid
    project_id = _uuid.UUID(test_project["id"])

    stale_pr = PullRequest(
        project_id=project_id,
        github_pr_id=9001,
        number=1,
        title="Stale PR",
        state=PRState.open,
        created_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    recent_pr = PullRequest(
        project_id=project_id,
        github_pr_id=9002,
        number=2,
        title="Recent PR",
        state=PRState.open,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add_all([stale_pr, recent_pr])
    await db_session.commit()

    resp = await client.get(
        f"/api/projects/{test_project['id']}/issues",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    stale_items = [i for i in data["items"] if i["type"] == "stale_pr"]
    titles = [i["title"] for i in stale_items]
    assert "Stale PR" in titles
    assert "Recent PR" not in titles
