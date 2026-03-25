import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.ai_job_queue import AIJobQueue, JobStatus, JobTrigger, JobType
from app.models.ai_review import AIReview, AIReviewType, AIReviewStatus
from app.models.organization import Organization
from app.models.project import Project
from app.models.pull_request import PullRequest
from app.models.user import User
from app.schemas.ai import (
    AIReviewResponse,
    JobCreatedResponse,
    JobStatusResponse,
    TestScenarioRequest,
)
from app.services.ai.executor import (
    clone_or_update_repo, cleanup_repo,
    stream_project_analysis, stream_code_review,
)
from app.services.ai.worker import build_project_context

router = APIRouter(tags=["ai"])


async def _sse_analysis(project_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession):
    """SSE generator for project analysis."""
    project = await db.get(Project, project_id)
    if not project or not project.github_repo_url:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Project has no GitHub repo'})}\n\n"
        return

    org = await db.get(Organization, project.org_id)
    job_id = uuid.uuid4()

    # Create job record
    job = AIJobQueue(
        id=job_id, project_id=project_id, org_id=project.org_id,
        job_type=JobType.analysis, trigger=JobTrigger.manual,
        status=JobStatus.running, payload={"requested_by": str(user_id)},
    )
    db.add(job)
    await db.commit()

    yield f"data: {json.dumps({'type': 'progress', 'message': '📦 GitHub 레포를 클론하고 있습니다...'})}\n\n"

    repo_path = None
    try:
        repo_path = await clone_or_update_repo(
            project.id, job_id, project.github_repo_url, org.github_installation_id
        )
        yield f"data: {json.dumps({'type': 'progress', 'message': '📊 프로젝트 컨텍스트를 수집합니다...'})}\n\n"

        context = await build_project_context(db, project.id)

        yield f"data: {json.dumps({'type': 'progress', 'message': '🤖 AI가 분석을 시작합니다...'})}\n\n"

        result_data = None
        async for event in stream_project_analysis(repo_path, context):
            if event["type"] == "progress":
                yield f"data: {json.dumps(event)}\n\n"
            elif event["type"] == "result":
                result_data = event["data"]
            elif event["type"] == "error":
                yield f"data: {json.dumps(event)}\n\n"

        if result_data:
            # Save review to DB
            review = AIReview(
                project_id=project.id,
                type=AIReviewType.analysis,
                status=AIReviewStatus.completed,
                summary=result_data.get("progress_assessment", ""),
                detail=result_data,
                suggestions=result_data.get("recommendations", []),
                requested_by=user_id,
                completed_at=datetime.now(timezone.utc),
            )
            db.add(review)
            await db.flush()

            job.status = JobStatus.completed
            job.ai_review_id = review.id
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

            yield f"data: {json.dumps({'type': 'result', 'review_id': str(review.id)})}\n\n"
        else:
            job.status = JobStatus.failed
            job.error_message = "No result from agent"
            await db.commit()
            yield f"data: {json.dumps({'type': 'error', 'message': 'AI가 결과를 반환하지 않았습니다'})}\n\n"

    except Exception as exc:
        job.status = JobStatus.failed
        job.error_message = str(exc)[:500]
        await db.commit()
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)[:300]})}\n\n"
    finally:
        if repo_path:
            cleanup_repo(project.id, job_id)

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/api/projects/{project_id}/ai/analyze")
async def request_analysis(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream project analysis progress via SSE."""
    project = await db.execute(select(Project).where(Project.id == project_id))
    if project.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return StreamingResponse(
        _sse_analysis(project_id, current_user.id, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
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
    """Queue a code review job (still async — webhook-triggered reviews need this)."""
    from app.services.ai.worker import process_ai_job
    import asyncio

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    pr_result = await db.execute(
        select(PullRequest).where(PullRequest.project_id == project_id, PullRequest.number == pr_number)
    )
    pr = pr_result.scalar_one_or_none()
    if pr is None:
        raise HTTPException(status_code=404, detail="Pull request not found")

    job = AIJobQueue(
        project_id=project_id, org_id=project.org_id,
        job_type=JobType.code_review, trigger=JobTrigger.manual,
        status=JobStatus.queued,
        payload={"pr_number": pr_number, "base": pr.base_ref, "head": pr.head_ref, "requested_by": str(current_user.id)},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    asyncio.create_task(process_ai_job(job.id))
    return JobCreatedResponse(job_id=job.id, status="queued", message="Code review job queued")


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
    from app.services.ai.worker import process_ai_job
    import asyncio

    if body.pr_number is None and (body.file_paths is None or len(body.file_paths) == 0):
        raise HTTPException(status_code=400, detail="Either pr_number or file_paths must be provided")

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    job = AIJobQueue(
        project_id=project_id, org_id=project.org_id,
        job_type=JobType.test_scenario, trigger=JobTrigger.manual,
        status=JobStatus.queued,
        payload={"pr_number": body.pr_number, "file_paths": body.file_paths, "requested_by": str(current_user.id)},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    asyncio.create_task(process_ai_job(job.id))
    return JobCreatedResponse(job_id=job.id, status="queued", message="Test scenario job queued")


@router.get("/api/ai/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(AIJobQueue, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/api/projects/{project_id}/ai/reviews", response_model=list[AIReviewResponse])
async def list_reviews(
    project_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AIReview).where(AIReview.project_id == project_id))
    return list(result.scalars().all())


@router.get("/api/projects/{project_id}/ai/reviews/{review_id}", response_model=AIReviewResponse)
async def get_review(
    project_id: uuid.UUID,
    review_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIReview).where(AIReview.id == review_id, AIReview.project_id == project_id)
    )
    review = result.scalar_one_or_none()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review
