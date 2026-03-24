"""Tests for the Slack router endpoints."""

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import OrgMember, OrgRole
from app.models.project import Project
from app.models.slack import SlackWorkspace


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_org(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/orgs/",
        json={"name": "Slack Test Org", "slug": "slack-test-org"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest_asyncio.fixture
async def test_project(client: AsyncClient, auth_headers, test_org):
    resp = await client.post(
        f"/api/orgs/{test_org['id']}/projects",
        json={"name": "Slack Test Project"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest_asyncio.fixture
async def connected_workspace(db_session: AsyncSession, test_org):
    workspace = SlackWorkspace(
        org_id=uuid.UUID(test_org["id"]),
        slack_team_id="T12345678",
        slack_bot_token="xoxb-test-token",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    return workspace


# ---------------------------------------------------------------------------
# Helper: build a valid-ish Slack signature header (bypass verification)
# ---------------------------------------------------------------------------

def _slack_headers(body: bytes, timestamp: str = "9999999999") -> dict:
    """Return headers that will pass or skip signature verification in tests.

    We patch `_verify_slack_signature` in the router to skip checks.
    """
    return {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": "v0=bypass",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_slack_status_not_connected(
    client: AsyncClient, auth_headers, test_org
):
    """GET /api/orgs/{org_id}/slack/status returns connected=false when no workspace."""
    resp = await client.get(
        f"/api/orgs/{test_org['id']}/slack/status",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["connected"] is False


@pytest.mark.asyncio
async def test_slack_status_connected(
    client: AsyncClient, auth_headers, test_org, connected_workspace
):
    """GET /api/orgs/{org_id}/slack/status returns connected=true when workspace exists."""
    resp = await client.get(
        f"/api/orgs/{test_org['id']}/slack/status",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["connected"] is True
    assert data["slack_team_id"] == "T12345678"


@pytest.mark.asyncio
@patch("app.routers.slack._verify_slack_signature", new_callable=AsyncMock)
async def test_slack_events_url_verification(
    mock_verify, client: AsyncClient
):
    """POST /api/slack/events with url_verification type returns the challenge."""
    challenge = "test_challenge_12345"
    mock_verify.return_value = json.dumps({
        "type": "url_verification",
        "challenge": challenge,
    }).encode()

    body = json.dumps({
        "type": "url_verification",
        "challenge": challenge,
    })

    resp = await client.post(
        "/api/slack/events",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Slack-Request-Timestamp": "9999999999",
            "X-Slack-Signature": "v0=bypass",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["challenge"] == challenge


@pytest.mark.asyncio
@patch("app.routers.slack._verify_slack_signature", new_callable=AsyncMock)
async def test_slack_events_app_mention(
    mock_verify, client: AsyncClient
):
    """POST /api/slack/events with app_mention returns ok (no workspace = no task created)."""
    event_payload = {
        "type": "event_callback",
        "team_id": "T_UNKNOWN",
        "event": {
            "type": "app_mention",
            "user": "U12345",
            "text": "<@UBOT> 프로젝트 상태 알려줘",
            "channel": "C12345",
        },
    }
    body_bytes = json.dumps(event_payload).encode()
    mock_verify.return_value = body_bytes

    resp = await client.post(
        "/api/slack/events",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Slack-Request-Timestamp": "9999999999",
            "X-Slack-Signature": "v0=bypass",
        },
    )

    assert resp.status_code == 200, resp.text
    assert resp.json().get("ok") is True


@pytest.mark.asyncio
async def test_set_project_channel(
    client: AsyncClient, auth_headers, test_project
):
    """POST /api/projects/{project_id}/slack/channel creates a channel mapping."""
    resp = await client.post(
        f"/api/projects/{test_project['id']}/slack/channel",
        json={"slack_channel_id": "C98765432"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["slack_channel_id"] == "C98765432"
    assert data["project_id"] == test_project["id"]


@pytest.mark.asyncio
async def test_set_project_channel_update(
    client: AsyncClient, auth_headers, test_project
):
    """POST /api/projects/{project_id}/slack/channel updates an existing mapping."""
    await client.post(
        f"/api/projects/{test_project['id']}/slack/channel",
        json={"slack_channel_id": "C111"},
        headers=auth_headers,
    )
    resp = await client.post(
        f"/api/projects/{test_project['id']}/slack/channel",
        json={"slack_channel_id": "C222"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["slack_channel_id"] == "C222"


@pytest.mark.asyncio
async def test_remove_project_channel(
    client: AsyncClient, auth_headers, test_project
):
    """DELETE /api/projects/{project_id}/slack/channel removes the mapping."""
    await client.post(
        f"/api/projects/{test_project['id']}/slack/channel",
        json={"slack_channel_id": "C_TO_DELETE"},
        headers=auth_headers,
    )
    resp = await client.delete(
        f"/api/projects/{test_project['id']}/slack/channel",
        headers=auth_headers,
    )
    assert resp.status_code == 204, resp.text


@pytest.mark.asyncio
async def test_list_user_mappings_empty(
    client: AsyncClient, auth_headers, test_org
):
    """GET /api/orgs/{org_id}/slack/user-mappings returns empty list initially."""
    resp = await client.get(
        f"/api/orgs/{test_org['id']}/slack/user-mappings",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


@pytest.mark.asyncio
async def test_add_user_mapping(
    client: AsyncClient, auth_headers, test_org, test_user
):
    """POST /api/orgs/{org_id}/slack/user-mappings creates a mapping."""
    resp = await client.post(
        f"/api/orgs/{test_org['id']}/slack/user-mappings",
        json={"user_id": str(test_user.id), "slack_user_id": "U_SLACK_123"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["slack_user_id"] == "U_SLACK_123"
    assert data["user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_slack_disconnect(
    client: AsyncClient, auth_headers, test_org, connected_workspace
):
    """DELETE /api/orgs/{org_id}/slack/disconnect removes the workspace."""
    resp = await client.delete(
        f"/api/orgs/{test_org['id']}/slack/disconnect",
        headers=auth_headers,
    )
    assert resp.status_code == 204, resp.text

    # Confirm it's gone
    status_resp = await client.get(
        f"/api/orgs/{test_org['id']}/slack/status",
        headers=auth_headers,
    )
    assert status_resp.json()["connected"] is False
