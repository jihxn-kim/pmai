import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.calendar import GoogleCalendarConnection

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False


def get_oauth_flow() -> "Flow":
    return Flow.from_client_config(
        {"web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }},
        scopes=["https://www.googleapis.com/auth/calendar.events"],
        redirect_uri=settings.google_redirect_uri,
    )


async def get_google_credentials(db: AsyncSession, user_id: uuid.UUID) -> "Credentials | None":
    result = await db.execute(
        select(GoogleCalendarConnection).where(GoogleCalendarConnection.user_id == user_id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        return None

    creds = Credentials(
        token=conn.access_token,
        refresh_token=conn.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    )

    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        conn.access_token = creds.token
        conn.token_expires_at = datetime.now(timezone.utc)
        await db.commit()

    return creds


async def save_google_tokens(db: AsyncSession, user_id: uuid.UUID, credentials, email: str) -> None:
    result = await db.execute(
        select(GoogleCalendarConnection).where(GoogleCalendarConnection.user_id == user_id)
    )
    conn = result.scalar_one_or_none()
    if conn:
        conn.access_token = credentials.token
        conn.refresh_token = credentials.refresh_token or conn.refresh_token
        conn.google_email = email
        conn.token_expires_at = datetime.now(timezone.utc)
    else:
        conn = GoogleCalendarConnection(
            user_id=user_id, google_email=email,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_expires_at=datetime.now(timezone.utc),
        )
        db.add(conn)
    await db.commit()
