import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.config import settings
from app.models.notion import NotionConnection


async def exchange_notion_code(code: str) -> dict:
    """Exchange OAuth code for Notion access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.notion.com/v1/oauth/token",
            auth=(settings.notion_client_id, settings.notion_client_secret),
            json={"grant_type": "authorization_code", "code": code, "redirect_uri": settings.notion_redirect_uri},
        )
        return resp.json()


async def get_notion_token(db: AsyncSession, org_id: uuid.UUID) -> str | None:
    result = await db.execute(select(NotionConnection).where(NotionConnection.org_id == org_id))
    conn = result.scalar_one_or_none()
    return conn.notion_access_token if conn else None
