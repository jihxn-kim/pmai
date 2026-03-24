from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def test_org(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/orgs/",
        json={"name": "Briefing Test Org", "slug": "test-org-briefings"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest_asyncio.fixture
async def test_project(client: AsyncClient, auth_headers, test_org):
    resp = await client.post(
        f"/api/orgs/{test_org['id']}/projects",
        json={"name": "Briefing Test Project"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_list_briefings_empty(client: AsyncClient, auth_headers, test_org):
    resp = await client.get(
        f"/api/orgs/{test_org['id']}/briefings",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_latest_briefing_none(client: AsyncClient, auth_headers, test_org):
    resp = await client.get(
        f"/api/orgs/{test_org['id']}/briefings/latest",
        headers=auth_headers,
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
@patch("app.routers.briefings.process_ai_job", new_callable=AsyncMock)
async def test_generate_briefing(mock_process, client: AsyncClient, auth_headers, test_org):
    resp = await client.post(
        f"/api/orgs/{test_org['id']}/briefings/generate",
        headers=auth_headers,
    )
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert "message" in data
