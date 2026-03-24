import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def test_org(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/orgs/",
        json={"name": "Test Org", "slug": "test-org-tasks"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest_asyncio.fixture
async def test_project(client: AsyncClient, auth_headers, test_org):
    resp = await client.post(
        f"/api/orgs/{test_org['id']}/projects",
        json={"name": "Test Project"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_task(client: AsyncClient, auth_headers, test_project):
    resp = await client.post(
        f"/api/projects/{test_project['id']}/tasks",
        json={"title": "My First Task", "description": "Task description", "priority": "high"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["title"] == "My First Task"
    assert data["description"] == "Task description"
    assert data["priority"] == "high"
    assert data["status"] == "todo"
    assert data["project_id"] == test_project["id"]


@pytest.mark.asyncio
async def test_list_tasks_with_pagination(client: AsyncClient, auth_headers, test_project):
    # Create 3 tasks
    for i in range(3):
        resp = await client.post(
            f"/api/projects/{test_project['id']}/tasks",
            json={"title": f"Task {i}"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text

    resp = await client.get(
        f"/api/projects/{test_project['id']}/tasks",
        params={"page": 1, "per_page": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    meta = body["meta"]
    assert meta["total"] == 3
    assert meta["page"] == 1
    assert meta["per_page"] == 2
    assert meta["total_pages"] == 2
    assert len(body["data"]) == 2


@pytest.mark.asyncio
async def test_update_task_status(client: AsyncClient, auth_headers, test_project):
    # Create a task
    resp = await client.post(
        f"/api/projects/{test_project['id']}/tasks",
        json={"title": "Status Task"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    task_id = resp.json()["id"]

    # Update status
    resp = await client.patch(
        f"/api/tasks/{task_id}",
        json={"status": "in_progress"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "in_progress"
    assert data["id"] == task_id


@pytest.mark.asyncio
async def test_delete_task(client: AsyncClient, auth_headers, test_project):
    # Create a task
    resp = await client.post(
        f"/api/projects/{test_project['id']}/tasks",
        json={"title": "Task to Delete"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    task_id = resp.json()["id"]

    # Delete it
    resp = await client.delete(
        f"/api/tasks/{task_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 204, resp.text

    # Verify it's gone
    resp = await client.get(
        f"/api/tasks/{task_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_filter_tasks_by_status(client: AsyncClient, auth_headers, test_project):
    project_id = test_project["id"]

    # Create tasks with different statuses
    resp = await client.post(
        f"/api/projects/{project_id}/tasks",
        json={"title": "Todo Task"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    todo_task_id = resp.json()["id"]

    resp = await client.post(
        f"/api/projects/{project_id}/tasks",
        json={"title": "Another Todo Task"},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    resp = await client.post(
        f"/api/projects/{project_id}/tasks",
        json={"title": "In Progress Task"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    in_progress_task_id = resp.json()["id"]

    # Move one task to in_progress
    resp = await client.patch(
        f"/api/tasks/{in_progress_task_id}",
        json={"status": "in_progress"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Filter by todo
    resp = await client.get(
        f"/api/projects/{project_id}/tasks",
        params={"status": "todo"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meta"]["total"] == 2
    statuses = [t["status"] for t in body["data"]]
    assert all(s == "todo" for s in statuses)

    # Filter by in_progress
    resp = await client.get(
        f"/api/projects/{project_id}/tasks",
        params={"status": "in_progress"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["id"] == in_progress_task_id
