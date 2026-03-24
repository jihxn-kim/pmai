import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.ai_job_queue import AIJobQueue, JobStatus, JobTrigger, JobType
from app.models.ai_review import AIReview
from app.models.project import Project
from app.models.pull_request import PullRequest
from app.models.user import User
from app.schemas.ai import (
    AIReviewResponse,
    JobCreatedResponse,
    JobStatusResponse,
    TestScenarioRequest,
)
from app.services.ai.worker import process_ai_job

router = APIRouter(tags=["ai"])


@router.post(
    "/api/projects/{project_id}/ai/analyze",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_analysis(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    job = AIJobQueue(
        project_id=project_id,
        org_id=project.org_id,
        job_type=JobType.analysis,
        trigger=JobTrigger.manual,
        status=JobStatus.queued,
        payload={"requested_by": str(current_user.id)},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    asyncio.create_task(process_ai_job(job.id))

    return JobCreatedResponse(
        job_id=job.id,
        status="queued",
        message="Analysis job queued",
    )


@router.post(
    "/api/projects/{project_id}/ai/review/{pr_number}",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_code_review(
    project_id: uuid.UUID,
    pr_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    pr_result = await db.execute(
        select(PullRequest).where(
            PullRequest.project_id == project_id,
            PullRequest.number == pr_number,
        )
    )
    pr = pr_result.scalar_one_or_none()
    if pr is None:
        raise HTTPException(status_code=404, detail="Pull request not found")

    job = AIJobQueue(
        project_id=project_id,
        org_id=project.org_id,
        job_type=JobType.code_review,
        trigger=JobTrigger.manual,
        status=JobStatus.queued,
        payload={
            "pr_number": pr_number,
            "base": pr.base_ref,
            "head": pr.head_ref,
            "requested_by": str(current_user.id),
        },
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    asyncio.create_task(process_ai_job(job.id))

    return JobCreatedResponse(
        job_id=job.id,
        status="queued",
        message="Code review job queued",
    )


@router.post(
    "/api/projects/{project_id}/ai/test-scenarios",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_test_scenarios(
    project_id: uuid.UUID,
    body: TestScenarioRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.pr_number is None and (body.file_paths is None or len(body.file_paths) == 0):
        raise HTTPException(
            status_code=400,
            detail="Either pr_number or file_paths must be provided",
        )

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    job = AIJobQueue(
        project_id=project_id,
        org_id=project.org_id,
        job_type=JobType.test_scenario,
        trigger=JobTrigger.manual,
        status=JobStatus.queued,
        payload={
            "pr_number": body.pr_number,
            "file_paths": body.file_paths,
            "requested_by": str(current_user.id),
        },
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    asyncio.create_task(process_ai_job(job.id))

    return JobCreatedResponse(
        job_id=job.id,
        status="queued",
        message="Test scenario job queued",
    )


@router.get(
    "/api/ai/jobs/{job_id}",
    response_model=JobStatusResponse,
)
async def get_job_status(
    job_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(AIJobQueue, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get(
    "/api/projects/{project_id}/ai/reviews",
    response_model=list[AIReviewResponse],
)
async def list_reviews(
    project_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIReview).where(AIReview.project_id == project_id)
    )
    reviews = result.scalars().all()
    return list(reviews)


@router.get(
    "/api/projects/{project_id}/ai/reviews/{review_id}",
    response_model=AIReviewResponse,
)
async def get_review(
    project_id: uuid.UUID,
    review_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIReview).where(
            AIReview.id == review_id,
            AIReview.project_id == project_id,
        )
    )
    review = result.scalar_one_or_none()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review
