"""Tests for the Notion router endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notion import NotionDatabaseMapping


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_org(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/orgs/",
        json={"name": "Notion Test Org", "slug": "notion-test-org"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest_asyncio.fixture
async def test_project(client: AsyncClient, auth_headers, test_org):
    resp = await client.post(
        f"/api/orgs/{test_org['id']}/projects",
        json={"name": "Notion Test Project"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notion_status_not_connected(
    client: AsyncClient, auth_headers, test_org
):
    """GET /api/orgs/{org_id}/notion/status returns connected=false when no connection."""
    resp = await client.get(
        f"/api/orgs/{test_org['id']}/notion/status",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["connected"] is False
    assert data.get("notion_workspace_id") is None


@pytest.mark.asyncio
async def test_notion_set_database(
    client: AsyncClient, auth_headers, test_project
):
    """POST /api/projects/{project_id}/notion/database creates a DB mapping."""
    resp = await client.post(
        f"/api/projects/{test_project['id']}/notion/database",
        json={"notion_database_id": "test-db-id-12345"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["notion_database_id"] == "test-db-id-12345"
    assert data["project_id"] == test_project["id"]


@pytest.mark.asyncio
async def test_notion_sync_status_not_connected(
    client: AsyncClient, auth_headers, test_project
):
    """GET /api/projects/{project_id}/notion/sync-status returns connected=false when no mapping."""
    resp = await client.get(
        f"/api/projects/{test_project['id']}/notion/sync-status",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["connected"] is False
    assert data.get("notion_database_id") is None
