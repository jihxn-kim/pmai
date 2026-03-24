import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def test_org(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/orgs/",
        json={"name": "Test Org", "slug": "test-org-proj"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest_asyncio.fixture
async def test_project(client: AsyncClient, auth_headers, test_org):
    resp = await client.post(
        f"/api/orgs/{test_org['id']}/projects",
        json={"name": "Test Project", "description": "A test project"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, auth_headers, test_org):
    resp = await client.post(
        f"/api/orgs/{test_org['id']}/projects",
        json={"name": "My Project", "description": "Desc"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Project"
    assert data["description"] == "Desc"
    assert data["status"] == "active"
    assert data["org_id"] == test_org["id"]


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, auth_headers, test_org, test_project):
    resp = await client.get(
        f"/api/orgs/{test_org['id']}/projects",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = [p["id"] for p in data]
    assert test_project["id"] in ids


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient, auth_headers, test_project):
    resp = await client.get(
        f"/api/projects/{test_project['id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == test_project["id"]
    assert data["name"] == test_project["name"]


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, auth_headers, test_project):
    resp = await client.patch(
        f"/api/projects/{test_project['id']}",
        json={"name": "Updated Project", "status": "paused"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Project"
    assert data["status"] == "paused"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, auth_headers, test_org, test_project):
    resp = await client.delete(
        f"/api/projects/{test_project['id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get(
        f"/api/projects/{test_project['id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_remove_project_member(
    client: AsyncClient, auth_headers, db_session, test_project
):
    from app.models.user import User

    # Create a second user to add as member
    second_user = User(
        github_id=99999,
        github_username="seconduser",
        name="Second User",
        email="second@example.com",
        avatar_url=None,
    )
    db_session.add(second_user)
    await db_session.commit()
    await db_session.refresh(second_user)

    # Add member
    resp = await client.post(
        f"/api/projects/{test_project['id']}/members",
        json={"github_username": "seconduser", "role": "developer"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["github_username"] == "seconduser"
    assert data["role"] == "developer"

    # List members — should have 2 (lead + new developer)
    resp = await client.get(
        f"/api/projects/{test_project['id']}/members",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    members = resp.json()
    usernames = [m["github_username"] for m in members]
    assert "seconduser" in usernames

    # Update member role
    second_user_id = str(second_user.id)
    resp = await client.patch(
        f"/api/projects/{test_project['id']}/members/{second_user_id}",
        json={"role": "reviewer"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "reviewer"

    # Remove member
    resp = await client.delete(
        f"/api/projects/{test_project['id']}/members/{second_user_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 204

    # Verify removed
    resp = await client.get(
        f"/api/projects/{test_project['id']}/members",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    members = resp.json()
    usernames = [m["github_username"] for m in members]
    assert "seconduser" not in usernames
