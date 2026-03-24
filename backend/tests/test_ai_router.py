import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_job_queue import AIJobQueue, JobStatus, JobTrigger, JobType


@pytest_asyncio.fixture
async def test_org(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/orgs/",
        json={"name": "AI Test Org", "slug": "test-org-ai"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest_asyncio.fixture
async def test_project(client: AsyncClient, auth_headers, test_org):
    resp = await client.post(
        f"/api/orgs/{test_org['id']}/projects",
        json={"name": "AI Test Project"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
@patch("app.routers.ai.process_ai_job", new_callable=AsyncMock)
async def test_request_analysis(mock_process, client: AsyncClient, auth_headers, test_project):
    resp = await client.post(
        f"/api/projects/{test_project['id']}/ai/analyze",
        headers=auth_headers,
    )
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert "message" in data


@pytest.mark.asyncio
async def test_get_job_status(
    client: AsyncClient, auth_headers, test_project, db_session: AsyncSession
):
    project_id = uuid.UUID(test_project["id"])
    job = AIJobQueue(
        project_id=project_id,
        job_type=JobType.analysis,
        trigger=JobTrigger.manual,
        status=JobStatus.queued,
        payload={},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await client.get(
        f"/api/ai/jobs/{job.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == str(job.id)
    assert data["job_type"] == "analysis"
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_list_reviews_empty(client: AsyncClient, auth_headers, test_project):
    resp = await client.get(
        f"/api/projects/{test_project['id']}/ai/reviews",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
@patch("app.routers.ai.process_ai_job", new_callable=AsyncMock)
async def test_request_test_scenarios_no_params(
    mock_process, client: AsyncClient, auth_headers, test_project
):
    resp = await client.post(
        f"/api/projects/{test_project['id']}/ai/test-scenarios",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 400, resp.text
