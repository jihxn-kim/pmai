import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_me_unauthorized(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_me_authorized(client: AsyncClient, test_user, auth_headers):
    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["github_id"] == 12345
    assert data["github_username"] == "testuser"
    assert data["name"] == "Test User"
    assert data["email"] == "testuser@example.com"


@pytest.mark.asyncio
async def test_refresh_no_cookie(client: AsyncClient):
    response = await client.post("/api/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, test_user, auth_headers):
    response = await client.post("/api/auth/logout")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
