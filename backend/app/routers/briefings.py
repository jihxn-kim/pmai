import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_org_role
from app.models.ai_job_queue import AIJobQueue, JobStatus, JobTrigger, JobType
from app.models.organization import OrgMember, OrgRole
from app.models.weekly_briefing import WeeklyBriefing
from app.schemas.ai import BriefingResponse, JobCreatedResponse
from app.services.ai.worker import process_ai_job

router = APIRouter(tags=["briefings"])


@router.get(
    "/api/orgs/{org_id}/briefings",
    response_model=list[BriefingResponse],
)
async def list_briefings(
    org_id: uuid.UUID,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WeeklyBriefing)
        .where(WeeklyBriefing.org_id == org_id)
        .order_by(WeeklyBriefing.created_at.desc())
    )
    briefings = result.scalars().all()
    return list(briefings)


@router.get(
    "/api/orgs/{org_id}/briefings/latest",
    response_model=BriefingResponse,
)
async def get_latest_briefing(
    org_id: uuid.UUID,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WeeklyBriefing)
        .where(WeeklyBriefing.org_id == org_id)
        .order_by(WeeklyBriefing.created_at.desc())
        .limit(1)
    )
    briefing = result.scalar_one_or_none()
    if briefing is None:
        raise HTTPException(status_code=404, detail="No briefings found")
    return briefing


@router.get(
    "/api/orgs/{org_id}/briefings/{briefing_id}",
    response_model=BriefingResponse,
)
async def get_briefing(
    org_id: uuid.UUID,
    briefing_id: uuid.UUID,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WeeklyBriefing).where(
            WeeklyBriefing.id == briefing_id,
            WeeklyBriefing.org_id == org_id,
        )
    )
    briefing = result.scalar_one_or_none()
    if briefing is None:
        raise HTTPException(status_code=404, detail="Briefing not found")
    return briefing


@router.post(
    "/api/orgs/{org_id}/briefings/generate",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_briefing(
    org_id: uuid.UUID,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    job = AIJobQueue(
        org_id=org_id,
        job_type=JobType.briefing,
        trigger=JobTrigger.manual,
        status=JobStatus.queued,
        payload={},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    asyncio.create_task(process_ai_job(job.id))

    return JobCreatedResponse(
        job_id=job.id,
        status="queued",
        message="Briefing generation job queued",
    )
