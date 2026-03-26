"""Slack integration router — OAuth, events, and settings endpoints."""

import asyncio
import hashlib
import hmac
import logging
import time
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_org_role
from app.models.organization import OrgMember, OrgRole
from app.models.project import Project
from app.models.slack import SlackChannelMapping, SlackUserMapping, SlackWorkspace
from app.models.user import User
from app.schemas.slack import (
    ChannelMappingRequest,
    OrgChannelRequest,
    SlackStatusResponse,
    UserMappingRequest,
    UserMappingResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["slack"])

# ---------------------------------------------------------------------------
# Signing secret verification
# ---------------------------------------------------------------------------

async def _verify_slack_signature(request: Request) -> bytes:
    """Verify the X-Slack-Signature header.

    Raises HTTP 403 on failure. Returns the raw request body bytes.
    """
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Reject stale requests (older than 5 minutes)
    try:
        if abs(time.time() - int(timestamp)) > 300:
            raise HTTPException(status_code=403, detail="Request timestamp is too old")
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid timestamp")

    if not settings.slack_signing_secret:
        # No signing secret configured — skip verification (dev mode)
        return body

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected = (
        "v0="
        + hmac.new(
            settings.slack_signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
    )

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")

    return body


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@router.post("/api/slack/events")
async def slack_events(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive Slack event callbacks."""
    body_bytes = await _verify_slack_signature(request)

    import json  # noqa: PLC0415

    try:
        payload = json.loads(body_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    event = payload.get("event", {})
    event_type = event.get("type", "")

    if event_type == "app_mention":
        # Resolve bot token from workspace for this team
        team_id = payload.get("team_id") or payload.get("team", {}).get("id")
        bot_token: str | None = None
        if team_id:
            ws_result = await db.execute(
                select(SlackWorkspace).where(SlackWorkspace.slack_team_id == team_id)
            )
            workspace = ws_result.scalar_one_or_none()
            if workspace:
                bot_token = workspace.slack_bot_token

        if bot_token:
            from app.services.slack.bot import handle_mention  # noqa: PLC0415

            asyncio.create_task(handle_mention(db, event, bot_token))

    return {"ok": True}


@router.post("/api/slack/interactions")
async def slack_interactions(request: Request):
    """Placeholder for Slack interactive component callbacks."""
    return {"ok": True}


# ---------------------------------------------------------------------------
# OAuth
# ---------------------------------------------------------------------------

@router.get("/api/orgs/{org_id}/slack/auth")
async def slack_oauth_start(
    org_id: uuid.UUID,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin)),
):
    """Return the Slack OAuth authorisation URL."""
    if not settings.slack_client_id:
        raise HTTPException(status_code=501, detail="Slack OAuth is not configured")

    scopes = "channels:read,channels:join,chat:write,app_mentions:read,users:read"
    redirect_uri = settings.slack_redirect_uri
    state = str(org_id)
    url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={settings.slack_client_id}"
        f"&scope={scopes}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )
    return {"url": url}


@router.get("/api/slack/oauth/callback")
async def slack_oauth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Exchange an OAuth code for a bot token and save the workspace."""
    if not settings.slack_client_id or not settings.slack_client_secret:
        raise HTTPException(status_code=501, detail="Slack OAuth is not configured")

    try:
        org_id = uuid.UUID(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    redirect_uri = settings.slack_redirect_uri

    async with httpx.AsyncClient() as http_client:
        resp = await http_client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "code": code,
                "client_id": settings.slack_client_id,
                "client_secret": settings.slack_client_secret,
                "redirect_uri": redirect_uri,
            },
        )

    data = resp.json()
    if not data.get("ok"):
        raise HTTPException(
            status_code=400,
            detail=f"Slack OAuth failed: {data.get('error', 'unknown')}",
        )

    team_id: str = data["team"]["id"]
    bot_token: str = data["access_token"]

    # Upsert workspace record
    existing_result = await db.execute(
        select(SlackWorkspace).where(SlackWorkspace.org_id == org_id)
    )
    workspace = existing_result.scalar_one_or_none()
    if workspace:
        workspace.slack_team_id = team_id
        workspace.slack_bot_token = bot_token
    else:
        workspace = SlackWorkspace(
            org_id=org_id,
            slack_team_id=team_id,
            slack_bot_token=bot_token,
        )
        db.add(workspace)

    await db.commit()
    await db.refresh(workspace)

    from app.models.organization import Organization
    org = await db.get(Organization, org_id)
    org_slug = org.slug if org else ""
    return RedirectResponse(url=f"{settings.frontend_url}/org/{org_slug}/settings?slack=connected")


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@router.get(
    "/api/orgs/{org_id}/slack/status",
    response_model=SlackStatusResponse,
)
async def slack_status(
    org_id: uuid.UUID,
    _member: OrgMember = Depends(
        require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member)
    ),
    db: AsyncSession = Depends(get_db),
):
    """Return Slack connection status for the organisation."""
    result = await db.execute(
        select(SlackWorkspace).where(SlackWorkspace.org_id == org_id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        return SlackStatusResponse(connected=False)
    return SlackStatusResponse(
        connected=True,
        slack_team_id=workspace.slack_team_id,
        org_channel_id=workspace.slack_org_channel_id,
    )


@router.get("/api/orgs/{org_id}/slack/users")
async def list_slack_users(
    org_id: uuid.UUID,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Fetch users from the connected Slack workspace."""
    result = await db.execute(
        select(SlackWorkspace).where(SlackWorkspace.org_id == org_id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Slack not connected")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://slack.com/api/users.list",
            headers={"Authorization": f"Bearer {workspace.slack_bot_token}"},
        )
    data = resp.json()
    if not data.get("ok"):
        raise HTTPException(status_code=502, detail=f"Slack API error: {data.get('error')}")

    users = [
        {
            "id": u["id"],
            "name": u.get("real_name") or u.get("name", ""),
            "display_name": u.get("profile", {}).get("display_name", ""),
            "avatar": u.get("profile", {}).get("image_48", ""),
        }
        for u in data.get("members", [])
        if not u.get("is_bot") and not u.get("deleted") and u.get("id") != "USLACKBOT"
    ]
    users.sort(key=lambda u: u["name"])
    return {"users": users}


@router.get("/api/orgs/{org_id}/slack/channels")
async def list_slack_channels(
    org_id: uuid.UUID,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Fetch public channels from the connected Slack workspace."""
    result = await db.execute(
        select(SlackWorkspace).where(SlackWorkspace.org_id == org_id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Slack not connected")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://slack.com/api/conversations.list",
            headers={"Authorization": f"Bearer {workspace.slack_bot_token}"},
            params={"types": "public_channel", "limit": 200, "exclude_archived": "true"},
        )
    data = resp.json()
    if not data.get("ok"):
        raise HTTPException(status_code=502, detail=f"Slack API error: {data.get('error')}")

    channels = [
        {"id": ch["id"], "name": ch["name"]}
        for ch in data.get("channels", [])
    ]
    channels.sort(key=lambda c: c["name"])
    return {"channels": channels}


@router.delete(
    "/api/orgs/{org_id}/slack/disconnect",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def slack_disconnect(
    org_id: uuid.UUID,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner)),
    db: AsyncSession = Depends(get_db),
):
    """Remove the Slack workspace integration for the organisation."""
    result = await db.execute(
        select(SlackWorkspace).where(SlackWorkspace.org_id == org_id)
    )
    workspace = result.scalar_one_or_none()
    if workspace:
        await db.delete(workspace)
        await db.commit()


@router.patch(
    "/api/orgs/{org_id}/slack/org-channel",
    response_model=SlackStatusResponse,
)
async def set_org_channel(
    org_id: uuid.UUID,
    body: OrgChannelRequest,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Set (or update) the organisation-wide Slack notification channel."""
    result = await db.execute(
        select(SlackWorkspace).where(SlackWorkspace.org_id == org_id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Slack workspace not connected",
        )

    old_channel_id = workspace.slack_org_channel_id
    workspace.slack_org_channel_id = body.slack_channel_id
    await db.commit()
    await db.refresh(workspace)

    try:
        from slack_sdk.web.async_client import AsyncWebClient
        client = AsyncWebClient(token=workspace.slack_bot_token)
        # Leave old channel
        if old_channel_id and old_channel_id != body.slack_channel_id:
            try:
                await client.conversations_leave(channel=old_channel_id)
            except Exception as e:
                logger.warning(f"Failed to leave old channel: {e}")
        # Join new channel
        resp = await client.conversations_join(channel=body.slack_channel_id)
        logger.info(f"Bot joined channel {body.slack_channel_id}: {resp.get('ok')}")
    except Exception as e:
        logger.warning(f"Failed to join channel: {e}")

    return SlackStatusResponse(
        connected=True,
        slack_team_id=workspace.slack_team_id,
        org_channel_id=workspace.slack_org_channel_id,
    )


@router.post(
    "/api/projects/{project_id}/slack/channel",
    status_code=status.HTTP_201_CREATED,
)
async def set_project_channel(
    project_id: uuid.UUID,
    body: ChannelMappingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Map a Slack channel to a project."""
    project_result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing_result = await db.execute(
        select(SlackChannelMapping).where(
            SlackChannelMapping.project_id == project_id
        )
    )
    mapping = existing_result.scalar_one_or_none()
    if mapping:
        mapping.slack_channel_id = body.slack_channel_id
    else:
        mapping = SlackChannelMapping(
            project_id=project_id,
            slack_channel_id=body.slack_channel_id,
        )
        db.add(mapping)

    await db.commit()
    await db.refresh(mapping)

    return {
        "project_id": str(project_id),
        "slack_channel_id": mapping.slack_channel_id,
    }


@router.delete(
    "/api/projects/{project_id}/slack/channel",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_project_channel(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove the Slack channel mapping for a project."""
    result = await db.execute(
        select(SlackChannelMapping).where(
            SlackChannelMapping.project_id == project_id
        )
    )
    mapping = result.scalar_one_or_none()
    if mapping:
        await db.delete(mapping)
        await db.commit()


@router.get(
    "/api/orgs/{org_id}/slack/user-mappings",
    response_model=list[UserMappingResponse],
)
async def list_user_mappings(
    org_id: uuid.UUID,
    _member: OrgMember = Depends(
        require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member)
    ),
    db: AsyncSession = Depends(get_db),
):
    """List all Slack user mappings for members of the organisation."""
    from app.models.organization import OrgMember as OrgMemberModel  # noqa: PLC0415

    # Get all user IDs in the org
    member_result = await db.execute(
        select(OrgMemberModel.user_id).where(OrgMemberModel.org_id == org_id)
    )
    user_ids = [row[0] for row in member_result.all()]

    if not user_ids:
        return []

    mapping_result = await db.execute(
        select(SlackUserMapping).where(SlackUserMapping.user_id.in_(user_ids))
    )
    return list(mapping_result.scalars().all())


@router.post(
    "/api/orgs/{org_id}/slack/user-mappings",
    response_model=UserMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_user_mapping(
    org_id: uuid.UUID,
    body: UserMappingRequest,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a mapping between an internal user and a Slack user ID."""
    existing_result = await db.execute(
        select(SlackUserMapping).where(SlackUserMapping.user_id == body.user_id)
    )
    mapping = existing_result.scalar_one_or_none()
    if mapping:
        mapping.slack_user_id = body.slack_user_id
    else:
        mapping = SlackUserMapping(
            user_id=body.user_id,
            slack_user_id=body.slack_user_id,
        )
        db.add(mapping)

    await db.commit()
    await db.refresh(mapping)
    return mapping
