"""Tests for the Google Calendar router endpoints."""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_calendar_status_not_connected(
    client: AsyncClient, auth_headers
):
    """GET /api/users/me/calendar/status returns connected=false when no connection."""
    resp = await client.get(
        "/api/users/me/calendar/status",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["connected"] is False
    assert data.get("google_email") is None
    assert data.get("calendar_id") is None


@pytest.mark.asyncio
async def test_calendar_disconnect_not_connected(
    client: AsyncClient, auth_headers
):
    """DELETE /api/users/me/calendar/disconnect returns 204 even if no connection exists."""
    resp = await client.delete(
        "/api/users/me/calendar/disconnect",
        headers=auth_headers,
    )
    assert resp.status_code == 204, resp.text
