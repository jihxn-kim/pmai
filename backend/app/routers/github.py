import base64
import json as _json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.activity_log import ActivityLog
from app.models.pull_request import PRState, PullRequest
from app.schemas.activity_log import ActivityResponse
from app.schemas.pull_request import PRResponse
from app.services import github_service

from app.config import settings
from app.dependencies import get_current_user
from app.models.organization import Organization, OrgMember
from app.models.user import User
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["github"])

EVENT_HANDLERS = {
    "pull_request": github_service.handle_pull_request,
    "issues": github_service.handle_issues,
    "push": github_service.handle_push,
    "pull_request_review": github_service.handle_pull_request_review,
}


def _encode_cursor(dt: datetime, row_id: uuid.UUID) -> str:
    """Encode a (datetime, id) pair as a base64 JSON cursor."""
    data = {"ts": dt.isoformat(), "id": str(row_id)}
    return base64.urlsafe_b64encode(_json.dumps(data).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode a cursor back into (datetime, id). Raises ValueError on failure."""
    try:
        data = _json.loads(base64.urlsafe_b64decode(cursor.encode()))
        cursor_dt = datetime.fromisoformat(data["ts"])
        cursor_id = uuid.UUID(data["id"])
        return cursor_dt, cursor_id
    except Exception as exc:
        raise ValueError("Invalid cursor") from exc


# --- GitHub App Installation ---

@router.get("/api/orgs/{org_id}/github/install")
async def github_app_install(org_id: uuid.UUID):
    """Redirect to GitHub App installation page."""
    if settings.github_app_slug:
        url = f"https://github.com/apps/{settings.github_app_slug}/installations/new?state={org_id}"
    else:
        url = f"https://github.com/settings/apps"
    return RedirectResponse(url=url)


@router.get("/api/github/setup/callback")
async def github_setup_callback(
    installation_id: int,
    setup_action: str = "install",
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """GitHub App post-installation callback. Saves installation_id to the org."""
    org_slug = None
    if state:
        try:
            org_id = uuid.UUID(state)
            org = await db.get(Organization, org_id)
            if org:
                org.github_installation_id = installation_id
                org_slug = org.slug
                await db.commit()
        except (ValueError, Exception):
            pass

    # Redirect back to frontend settings using slug, not UUID
    redirect_path = f"/org/{org_slug}/settings" if org_slug else "/"
    return RedirectResponse(url=f"{settings.frontend_url}{redirect_path}?github=installed")


@router.get("/api/orgs/{org_id}/github/status")
async def github_installation_status(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if GitHub App is installed for this org."""
    org = await db.get(Organization, org_id)
    if not org:
        return {"installed": False, "installation_id": None}
    return {
        "installed": org.github_installation_id is not None,
        "installation_id": org.github_installation_id,
    }


@router.post("/api/webhooks/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    import json

    body = await github_service.verify_webhook_signature(request)
    payload = json.loads(body)

    handler = EVENT_HANDLERS.get(x_github_event)
    if handler:
        await handler(db, payload)

    return {"status": "ok"}


@router.get(
    "/api/projects/{project_id}/pulls",
    response_model=list[PRResponse],
)
async def list_pull_requests(
    project_id: uuid.UUID,
    state: PRState | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(PullRequest).where(PullRequest.project_id == project_id)
    if state is not None:
        query = query.where(PullRequest.state == state)

    offset = (page - 1) * per_page
    query = query.order_by(PullRequest.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    prs = list(result.scalars().all())
    return prs


@router.get(
    "/api/projects/{project_id}/activity",
)
async def list_activity(
    project_id: uuid.UUID,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(ActivityLog).where(ActivityLog.project_id == project_id)

    if cursor is not None:
        try:
            cursor_dt, cursor_id = _decode_cursor(cursor)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid cursor format")
        # Items with older timestamps, or same timestamp but smaller UUID
        query = query.where(
            or_(
                ActivityLog.created_at < cursor_dt,
                and_(
                    ActivityLog.created_at == cursor_dt,
                    ActivityLog.id < cursor_id,
                ),
            )
        )

    query = query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(limit + 1)
    result = await db.execute(query)
    logs = list(result.scalars().all())

    has_more = len(logs) > limit
    if has_more:
        logs = logs[:limit]

    next_cursor = None
    if has_more and logs:
        last = logs[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)

    return {
        "data": [ActivityResponse.model_validate(log) for log in logs],
        "next_cursor": next_cursor,
    }
