import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_create_org(client: AsyncClient, test_user: User, auth_headers: dict):
    response = await client.post(
        "/api/orgs/",
        json={"name": "Test Org", "slug": "test-org"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Org"
    assert data["slug"] == "test-org"
    assert data["owner_id"] == str(test_user.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_orgs(client: AsyncClient, test_user: User, auth_headers: dict):
    # Create an org first
    await client.post(
        "/api/orgs/",
        json={"name": "List Test Org", "slug": "list-test-org"},
        headers=auth_headers,
    )

    response = await client.get("/api/orgs/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    slugs = [org["slug"] for org in data]
    assert "list-test-org" in slugs


@pytest.mark.asyncio
async def test_duplicate_slug(client: AsyncClient, test_user: User, auth_headers: dict):
    # Create first org
    resp = await client.post(
        "/api/orgs/",
        json={"name": "Dupe Org", "slug": "dupe-slug"},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    # Attempt to create second org with same slug
    resp2 = await client.post(
        "/api/orgs/",
        json={"name": "Another Org", "slug": "dupe-slug"},
        headers=auth_headers,
    )
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_get_org_members(client: AsyncClient, test_user: User, auth_headers: dict):
    # Create org
    create_resp = await client.post(
        "/api/orgs/",
        json={"name": "Members Org", "slug": "members-org"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    org_id = create_resp.json()["id"]

    # List members
    members_resp = await client.get(
        f"/api/orgs/{org_id}/members",
        headers=auth_headers,
    )
    assert members_resp.status_code == 200
    members = members_resp.json()
    assert isinstance(members, list)
    assert len(members) >= 1

    # Creator should be included as owner
    creator = next(
        (m for m in members if m["github_username"] == test_user.github_username), None
    )
    assert creator is not None
    assert creator["role"] == "owner"


@pytest.mark.asyncio
async def test_get_org_unauthorized(client: AsyncClient, test_user: User, auth_headers: dict):
    # Create org
    create_resp = await client.post(
        "/api/orgs/",
        json={"name": "Private Org", "slug": "private-org"},
        headers=auth_headers,
    )
    org_id = create_resp.json()["id"]

    # Access without auth
    resp = await client.get(f"/api/orgs/{org_id}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_org(client: AsyncClient, test_user: User, auth_headers: dict):
    create_resp = await client.post(
        "/api/orgs/",
        json={"name": "Update Org", "slug": "update-org"},
        headers=auth_headers,
    )
    org_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/orgs/{org_id}",
        json={"name": "Updated Name"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"
    assert resp.json()["slug"] == "update-org"
