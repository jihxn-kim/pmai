"""Tests for POST /api/projects/{project_id}/github endpoint."""
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import respx
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrgMember
from app.models.project import Project


@pytest_asyncio.fixture
async def test_org_with_installation(db_session: AsyncSession, test_user):
    """Create an org with github_installation_id set + a project."""
    org = Organization(
        name="GitHub Org",
        slug="github-org",
        owner_id=test_user.id,
        github_installation_id=98765,
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
        name="GitHub Project",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(org)
    return org, project


@pytest_asyncio.fixture
async def test_org_no_installation(db_session: AsyncSession, test_user):
    """Create an org WITHOUT github_installation_id + a project."""
    org = Organization(
        name="No Install Org",
        slug="no-install-org",
        owner_id=test_user.id,
        github_installation_id=None,
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
        name="No Install Project",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return org, project


async def _noop_initial_sync(*args, **kwargs):
    """No-op replacement for initial_sync used in tests."""
    pass


@pytest.mark.asyncio
async def test_connect_github_repo_success(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers,
    test_org_with_installation,
):
    """Connecting a valid repo should set github_repo_id on the project."""
    org, project = test_org_with_installation

    fake_token = "ghs_fake_installation_token"
    fake_repo_data = {
        "id": 123456789,
        "name": "my-repo",
        "full_name": "testowner/my-repo",
    }

    # Patch get_installation_token so we don't need a real GitHub App key.
    # Patch initial_sync with a no-op so asyncio.create_task gets a fast coroutine.
    with patch(
        "app.services.github_service.get_installation_token",
        new=AsyncMock(return_value=fake_token),
    ), patch(
        "app.services.github_service.initial_sync",
        new=_noop_initial_sync,
    ), respx.mock(
        base_url="https://api.github.com"
    ) as mock_github:
        mock_github.get("/repos/testowner/my-repo").mock(
            return_value=Response(200, json=fake_repo_data)
        )

        resp = await client.post(
            f"/api/projects/{project.id}/github",
            json={"repo_url": "https://github.com/testowner/my-repo"},
            headers=auth_headers,
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["github_repo_id"] == 123456789
    assert data["github_repo_url"] == "https://github.com/testowner/my-repo"

    # Verify the project was updated in DB
    await db_session.refresh(project)
    assert project.github_repo_id == 123456789


@pytest.mark.asyncio
async def test_connect_github_repo_no_installation(
    client: AsyncClient,
    auth_headers,
    test_org_no_installation,
):
    """Should return 400 when org has no github_installation_id."""
    org, project = test_org_no_installation

    resp = await client.post(
        f"/api/projects/{project.id}/github",
        json={"repo_url": "https://github.com/testowner/my-repo"},
        headers=auth_headers,
    )

    assert resp.status_code == 400
    assert "installation" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_connect_github_repo_not_found(
    client: AsyncClient,
    auth_headers,
    test_org_with_installation,
):
    """Should return 400 when GitHub returns 404 for the repository."""
    org, project = test_org_with_installation

    fake_token = "ghs_fake_installation_token"

    with patch(
        "app.services.github_service.get_installation_token",
        new=AsyncMock(return_value=fake_token),
    ), patch(
        "app.services.github_service.initial_sync",
        new=_noop_initial_sync,
    ), respx.mock(base_url="https://api.github.com") as mock_github:
        mock_github.get("/repos/testowner/nonexistent-repo").mock(
            return_value=Response(404, json={"message": "Not Found"})
        )

        resp = await client.post(
            f"/api/projects/{project.id}/github",
            json={"repo_url": "https://github.com/testowner/nonexistent-repo"},
            headers=auth_headers,
        )

    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"].lower()
