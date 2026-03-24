"""Notion integration router — OAuth, DB mapping, and sync endpoints."""

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_org_role
from app.models.notion import NotionConnection, NotionDatabaseMapping
from app.models.organization import OrgMember, OrgRole
from app.models.project import Project
from app.models.user import User
from app.schemas.notion import (
    NotionDatabaseRequest,
    NotionStatusResponse,
    NotionSyncStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notion"])


# ---------------------------------------------------------------------------
# OAuth
# ---------------------------------------------------------------------------


@router.get("/api/orgs/{org_id}/notion/auth")
async def notion_oauth_start(
    org_id: uuid.UUID,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin)),
):
    """Redirect user to Notion OAuth consent screen."""
    if not settings.notion_client_id:
        raise HTTPException(status_code=501, detail="Notion OAuth is not configured")

    state = str(org_id)
    url = (
        f"https://api.notion.com/v1/oauth/authorize"
        f"?client_id={settings.notion_client_id}"
        f"&response_type=code"
        f"&owner=user"
        f"&redirect_uri={settings.notion_redirect_uri}"
        f"&state={state}"
    )
    return RedirectResponse(url=url)


@router.get("/api/notion/oauth/callback")
async def notion_oauth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Exchange OAuth code for Notion access token and save connection."""
    try:
        org_id = uuid.UUID(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    try:
        from app.services.notion.auth import exchange_notion_code

        token_data = await exchange_notion_code(code)

        if "error" in token_data:
            raise ValueError(f"Notion OAuth error: {token_data.get('error')}")

        access_token = token_data.get("access_token", "")
        workspace_id = token_data.get("workspace_id", "")

        # Upsert connection record
        existing_result = await db.execute(
            select(NotionConnection).where(NotionConnection.org_id == org_id)
        )
        conn = existing_result.scalar_one_or_none()
        if conn:
            conn.notion_access_token = access_token
            conn.notion_workspace_id = workspace_id
        else:
            conn = NotionConnection(
                org_id=org_id,
                notion_access_token=access_token,
                notion_workspace_id=workspace_id,
            )
            db.add(conn)

        await db.commit()
    except Exception as exc:
        logger.exception("Notion OAuth callback failed: %s", exc)
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings/notion?error=oauth_failed"
        )

    return RedirectResponse(
        url=f"{settings.frontend_url}/settings/notion?connected=true"
    )


# ---------------------------------------------------------------------------
# Status / Disconnect
# ---------------------------------------------------------------------------


@router.get(
    "/api/orgs/{org_id}/notion/status",
    response_model=NotionStatusResponse,
)
async def notion_status(
    org_id: uuid.UUID,
    _member: OrgMember = Depends(
        require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member)
    ),
    db: AsyncSession = Depends(get_db),
):
    """Return Notion connection status for the organisation."""
    result = await db.execute(
        select(NotionConnection).where(NotionConnection.org_id == org_id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        return NotionStatusResponse(connected=False)
    return NotionStatusResponse(
        connected=True,
        notion_workspace_id=conn.notion_workspace_id,
    )


@router.delete(
    "/api/orgs/{org_id}/notion/disconnect",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def notion_disconnect(
    org_id: uuid.UUID,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner)),
    db: AsyncSession = Depends(get_db),
):
    """Remove the Notion connection for the organisation."""
    result = await db.execute(
        select(NotionConnection).where(NotionConnection.org_id == org_id)
    )
    conn = result.scalar_one_or_none()
    if conn:
        await db.delete(conn)
        await db.commit()


# ---------------------------------------------------------------------------
# Project DB mapping
# ---------------------------------------------------------------------------


@router.post(
    "/api/projects/{project_id}/notion/database",
    status_code=status.HTTP_201_CREATED,
)
async def set_notion_database(
    project_id: uuid.UUID,
    body: NotionDatabaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Map a Notion database to a project."""
    project_result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing_result = await db.execute(
        select(NotionDatabaseMapping).where(
            NotionDatabaseMapping.project_id == project_id
        )
    )
    mapping = existing_result.scalar_one_or_none()
    if mapping:
        mapping.notion_database_id = body.notion_database_id
    else:
        mapping = NotionDatabaseMapping(
            project_id=project_id,
            notion_database_id=body.notion_database_id,
        )
        db.add(mapping)

    await db.commit()
    await db.refresh(mapping)

    return {
        "project_id": str(project_id),
        "notion_database_id": mapping.notion_database_id,
    }


@router.delete(
    "/api/projects/{project_id}/notion/database",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_notion_database(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove the Notion database mapping for a project."""
    result = await db.execute(
        select(NotionDatabaseMapping).where(
            NotionDatabaseMapping.project_id == project_id
        )
    )
    mapping = result.scalar_one_or_none()
    if mapping:
        await db.delete(mapping)
        await db.commit()


@router.get(
    "/api/projects/{project_id}/notion/sync-status",
    response_model=NotionSyncStatusResponse,
)
async def notion_sync_status(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return Notion sync status for a project."""
    result = await db.execute(
        select(NotionDatabaseMapping).where(
            NotionDatabaseMapping.project_id == project_id
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        return NotionSyncStatusResponse(connected=False)
    return NotionSyncStatusResponse(
        connected=True,
        notion_database_id=mapping.notion_database_id,
        last_synced_at=str(mapping.last_synced_at) if mapping.last_synced_at else None,
    )


@router.post(
    "/api/projects/{project_id}/notion/sync",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_notion_sync(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a Notion sync for a project (best-effort, non-blocking)."""
    result = await db.execute(
        select(NotionDatabaseMapping).where(
            NotionDatabaseMapping.project_id == project_id
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(
            status_code=404,
            detail="No Notion database mapped to this project",
        )

    try:
        from app.services.notion.sync import poll_notion_changes

        asyncio.create_task(poll_notion_changes())
    except Exception:
        pass

    return {"status": "sync_triggered"}
