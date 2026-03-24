"""Google Calendar integration router — OAuth, webhook, and status endpoints."""

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.calendar import GoogleCalendarConnection
from app.models.user import User
from app.schemas.calendar import CalendarStatusResponse

try:
    from google_auth_oauthlib.flow import Flow
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

logger = logging.getLogger(__name__)

router = APIRouter(tags=["calendar"])


# ---------------------------------------------------------------------------
# OAuth
# ---------------------------------------------------------------------------

@router.get("/api/calendar/auth")
async def calendar_oauth_start(
    current_user: User = Depends(get_current_user),
):
    """Redirect user to Google OAuth consent screen."""
    if not HAS_GOOGLE:
        raise HTTPException(status_code=501, detail="Google Calendar library not installed")
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=501, detail="Google Calendar OAuth is not configured")

    from app.services.calendar.auth import get_oauth_flow
    flow = get_oauth_flow()
    # Encode user_id as state for callback
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=str(current_user.id),
    )
    return RedirectResponse(url=auth_url)


@router.get("/api/calendar/oauth/callback")
async def calendar_oauth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Exchange OAuth code for tokens and save them."""
    if not HAS_GOOGLE:
        raise HTTPException(status_code=501, detail="Google Calendar library not installed")

    try:
        user_id = uuid.UUID(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    try:
        from app.services.calendar.auth import get_oauth_flow, save_google_tokens
        flow = get_oauth_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Get user email from Google
        import httpx
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {credentials.token}"},
            )
        email = resp.json().get("email", "")

        await save_google_tokens(db, user_id, credentials, email)
    except Exception as exc:
        logger.exception("Google Calendar OAuth callback failed: %s", exc)
        return RedirectResponse(url=f"{settings.frontend_url}/settings/calendar?error=oauth_failed")

    return RedirectResponse(url=f"{settings.frontend_url}/settings/calendar?connected=true")


# ---------------------------------------------------------------------------
# Status / Disconnect
# ---------------------------------------------------------------------------

@router.get(
    "/api/users/me/calendar/status",
    response_model=CalendarStatusResponse,
)
async def calendar_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return Google Calendar connection status for the current user."""
    result = await db.execute(
        select(GoogleCalendarConnection).where(
            GoogleCalendarConnection.user_id == current_user.id
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        return CalendarStatusResponse(connected=False)
    return CalendarStatusResponse(
        connected=True,
        google_email=conn.google_email,
        calendar_id=conn.calendar_id,
    )


@router.delete(
    "/api/users/me/calendar/disconnect",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def calendar_disconnect(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove the Google Calendar connection for the current user."""
    result = await db.execute(
        select(GoogleCalendarConnection).where(
            GoogleCalendarConnection.user_id == current_user.id
        )
    )
    conn = result.scalar_one_or_none()
    if conn:
        await db.delete(conn)
        await db.commit()


# ---------------------------------------------------------------------------
# Webhook (Google Push Notifications)
# ---------------------------------------------------------------------------

@router.post("/api/calendar/webhook")
async def calendar_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive Google Calendar push notifications and sync changed events."""
    # Google uses channel tokens — no signing verification needed
    channel_id = request.headers.get("X-Goog-Channel-ID", "")
    resource_state = request.headers.get("X-Goog-Resource-State", "")

    # Sync messages only (not "sync" init messages)
    if resource_state == "sync":
        return {"ok": True}

    # Extract user_id from channel_id (format: "{user_id}-{suffix}")
    user_id: uuid.UUID | None = None
    if channel_id:
        try:
            user_id = uuid.UUID(channel_id.split("-")[0])
        except (ValueError, IndexError):
            pass

    if not user_id or not HAS_GOOGLE:
        return {"ok": True}

    try:
        from app.services.calendar.auth import get_google_credentials
        from app.services.calendar.sync import sync_calendar_to_tasks

        creds = await get_google_credentials(db, user_id)
        if not creds:
            return {"ok": True}

        result = await db.execute(
            select(GoogleCalendarConnection).where(
                GoogleCalendarConnection.user_id == user_id
            )
        )
        conn = result.scalar_one_or_none()
        if not conn:
            return {"ok": True}

        from googleapiclient.discovery import build
        service = build("calendar", "v3", credentials=creds)

        # Fetch recent changes using events.list with updatedMin
        from datetime import datetime, timezone, timedelta
        updated_min = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        events_result = service.events().list(
            calendarId=conn.calendar_id,
            updatedMin=updated_min,
            showDeleted=True,
            singleEvents=True,
        ).execute()

        changed_events = events_result.get("items", [])
        await sync_calendar_to_tasks(db, user_id, changed_events)
    except Exception:
        logger.exception("Calendar webhook processing failed")

    return {"ok": True}
