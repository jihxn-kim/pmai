"""Background worker: processes AI jobs from the queue."""

import asyncio
import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.ai_job_queue import AIJobQueue, JobStatus, JobType
from app.models.ai_review import AIReview, AIReviewStatus, AIReviewType
from app.models.organization import Organization
from app.models.project import Project
from app.models.pull_request import PullRequest
from app.models.task import Task, TaskStatus
from app.models.weekly_briefing import BriefingStatus, WeeklyBriefing
from app.services.ai.executor import (
    cleanup_repo,
    clone_or_update_repo,
    run_code_review,
    run_project_analysis,
    run_test_generation,
    run_weekly_briefing,
)

logger = logging.getLogger(__name__)


async def build_project_context(db: AsyncSession, project_id: uuid.UUID) -> str:
    """Build a text context of project state for the analyst/briefing agent."""
    project = await db.get(Project, project_id)
    if not project:
        return ""

    # Task stats
    tasks_result = await db.execute(select(Task).where(Task.project_id == project_id))
    tasks = list(tasks_result.scalars().all())

    total = len(tasks)
    done = len([t for t in tasks if t.status == TaskStatus.done])
    today = date.today()
    overdue = [
        t
        for t in tasks
        if t.due_date and t.due_date < today and t.status != TaskStatus.done
    ]

    # PR stats
    prs_result = await db.execute(
        select(PullRequest).where(PullRequest.project_id == project_id)
    )
    prs = list(prs_result.scalars().all())
    open_prs = [p for p in prs if p.state.value == "open"]

    context_parts = [
        f"Project: {project.name}",
        f"Status: {project.status.value}",
        f"Tasks: {done}/{total} done",
        f"Overdue tasks: {len(overdue)}",
        f"Open PRs: {len(open_prs)}",
    ]

    if overdue:
        context_parts.append("Overdue items:")
        for t in overdue[:10]:
            days = (today - t.due_date).days
            context_parts.append(f"  - {t.title} ({days} days overdue)")

    return "\n".join(context_parts)


async def _update_job_progress(job_id: uuid.UUID, message: str) -> None:
    """Append a progress entry to the job's progress_log in the DB."""
    try:
        async with async_session() as db:
            job = await db.get(AIJobQueue, job_id)
            if job:
                entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": message[:300],
                }
                log = list(job.progress_log or [])
                log.append(entry)
                # Keep only last 50 entries
                if len(log) > 50:
                    log = log[-50:]
                job.progress_log = log
                await db.commit()
    except Exception:
        pass  # Never fail the job because of progress logging



async def process_ai_job(job_id: uuid.UUID) -> None:
    """Process a single AI job. Called as a background task via asyncio.create_task."""
    async with async_session() as db:
        job = await db.get(AIJobQueue, job_id)
        if not job or job.status not in (JobStatus.queued, JobStatus.running):
            return

        job.status = JobStatus.running
        job.progress_log = [{"timestamp": datetime.now(timezone.utc).isoformat(), "message": "Job started"}]
        await db.commit()

        repo_path = None
        try:
            project = await db.get(Project, job.project_id) if job.project_id else None

            if job.job_type == JobType.code_review:
                if not project or not project.github_repo_url:
                    raise ValueError("Project has no GitHub repo connected")

                org = await db.get(Organization, project.org_id)
                await _update_job_progress(job.id, "GitHub 레포를 클론하고 있습니다...")
                repo_path = await clone_or_update_repo(
                    project.id, job.id, project.github_repo_url,
                    org.github_installation_id,
                )
                payload = job.payload
                await _update_job_progress(job.id, f"PR #{payload['pr_number']} 코드리뷰를 시작합니다...")
                result = await run_code_review(
                    repo_path,
                    payload["pr_number"],
                    payload["base"],
                    payload["head"],
                )
                await _update_job_progress(job.id, "코드리뷰 완료. 결과를 저장합니다...")

                # Find the associated PR record
                pr_result = await db.execute(
                    select(PullRequest).where(
                        PullRequest.project_id == project.id,
                        PullRequest.number == payload["pr_number"],
                    )
                )
                pr = pr_result.scalar_one_or_none()

                review = AIReview(
                    project_id=project.id,
                    pull_request_id=pr.id if pr else None,
                    type=AIReviewType.code_review,
                    status=AIReviewStatus.completed,
                    summary=result.get("summary", ""),
                    detail=result,
                    suggestions=result.get("overall_issues", []),
                    requested_by=(
                        uuid.UUID(job.payload["requested_by"])
                        if job.payload.get("requested_by")
                        else None
                    ),
                    completed_at=datetime.now(timezone.utc),
                )
                db.add(review)
                await db.flush()
                job.ai_review_id = review.id

                # Post GitHub comment — best-effort, never fail the job
                try:
                    from app.services.github_service import post_github_review_comment

                    parts = project.github_repo_url.rstrip("/").split("/")
                    owner, repo_name = parts[-2], parts[-1]
                    comment_id = await post_github_review_comment(
                        org.github_installation_id,
                        owner,
                        repo_name,
                        payload["pr_number"],
                        result,
                    )
                    review.github_comment_id = comment_id
                except Exception:
                    pass  # Non-critical

                # Slack notification for AI review
                try:
                    from app.services.slack.notifications import send_slack_notification
                    from app.services.slack.formatters import format_ai_review_notification
                    score = result.get("score")
                    await send_slack_notification(
                        db, org_id=project.org_id, channel_type="project", project_id=project.id,
                        blocks=format_ai_review_notification(review.summary or "", payload["pr_number"], score),
                        text=f"AI 리뷰 완료: PR #{payload['pr_number']}",
                    )
                except Exception:
                    pass

            elif job.job_type == JobType.analysis:
                if not project or not project.github_repo_url:
                    raise ValueError("Project has no GitHub repo connected")

                org = await db.get(Organization, project.org_id)
                await _update_job_progress(job.id, "GitHub 레포를 클론하고 있습니다...")
                repo_path = await clone_or_update_repo(
                    project.id, job.id, project.github_repo_url,
                    org.github_installation_id,
                )
                await _update_job_progress(job.id, "프로젝트 컨텍스트를 수집합니다...")
                context = await build_project_context(db, project.id)
                await _update_job_progress(job.id, "AI가 프로젝트를 분석 중입니다. git log, 태스크, PR을 확인합니다...")
                result = await run_project_analysis(repo_path, context)
                await _update_job_progress(job.id, "분석 완료. 결과를 저장합니다...")

                review = AIReview(
                    project_id=project.id,
                    type=AIReviewType.analysis,
                    status=AIReviewStatus.completed,
                    summary=result.get("progress_assessment", ""),
                    detail=result,
                    suggestions=result.get("recommendations", []),
                    requested_by=(
                        uuid.UUID(job.payload["requested_by"])
                        if job.payload.get("requested_by")
                        else None
                    ),
                    completed_at=datetime.now(timezone.utc),
                )
                db.add(review)
                await db.flush()
                job.ai_review_id = review.id

            elif job.job_type == JobType.test_scenario:
                if not project or not project.github_repo_url:
                    raise ValueError("Project has no GitHub repo connected")

                org = await db.get(Organization, project.org_id)
                await _update_job_progress(job.id, "GitHub 레포를 클론하고 있습니다...")
                repo_path = await clone_or_update_repo(
                    project.id, job.id, project.github_repo_url,
                    org.github_installation_id,
                )
                payload = job.payload
                pr = None
                base, head = None, None
                if payload.get("pr_number"):
                    pr_result = await db.execute(
                        select(PullRequest).where(
                            PullRequest.project_id == project.id,
                            PullRequest.number == payload["pr_number"],
                        )
                    )
                    pr = pr_result.scalar_one_or_none()
                    if pr:
                        base, head = pr.base_ref, pr.head_ref

                await _update_job_progress(job.id, "AI가 테스트 시나리오를 생성 중입니다...")
                result = await run_test_generation(
                    repo_path,
                    payload.get("pr_number"),
                    payload.get("file_paths"),
                    base,
                    head,
                )

                review = AIReview(
                    project_id=project.id,
                    pull_request_id=pr.id if pr else None,
                    type=AIReviewType.test_scenario,
                    status=AIReviewStatus.completed,
                    summary=f"{len(result.get('test_scenarios', []))} test scenarios generated",
                    detail=result,
                    suggestions=[],
                    requested_by=(
                        uuid.UUID(job.payload["requested_by"])
                        if job.payload.get("requested_by")
                        else None
                    ),
                    completed_at=datetime.now(timezone.utc),
                )
                db.add(review)
                await db.flush()
                job.ai_review_id = review.id

            elif job.job_type == JobType.briefing:
                org = await db.get(Organization, job.org_id)
                if not org:
                    raise ValueError("Organization not found")

                # All projects in the org that have a GitHub repo
                projects_result = await db.execute(
                    select(Project).where(
                        Project.org_id == org.id,
                        Project.github_repo_url.isnot(None),
                    )
                )
                projects = list(projects_result.scalars().all())

                project_briefings = []
                for proj in projects:
                    proj_repo_path = None
                    try:
                        proj_repo_path = await clone_or_update_repo(
                            proj.id, job.id, proj.github_repo_url,
                            org.github_installation_id,
                        )
                        context = await build_project_context(db, proj.id)
                        brief = await run_weekly_briefing(proj_repo_path, context, on_progress=progress_cb)
                        brief["project_id"] = str(proj.id)
                        brief["project_name"] = proj.name
                        project_briefings.append(brief)
                    except Exception as proj_err:
                        logger.warning(
                            "Briefing failed for project %s: %s", proj.id, proj_err
                        )
                        project_briefings.append(
                            {
                                "project_id": str(proj.id),
                                "project_name": proj.name,
                                "summary": f"Failed to generate briefing: {str(proj_err)[:200]}",
                                "completed_tasks": 0,
                                "merged_prs": 0,
                            }
                        )
                    finally:
                        cleanup_repo(proj.id, job.id)

                # Monday of the current week
                today = date.today()
                monday = today - timedelta(days=today.weekday())

                briefing = WeeklyBriefing(
                    org_id=org.id,
                    week_start=monday,
                    org_summary={
                        "total_projects": len(projects),
                        "briefing_count": len(project_briefings),
                    },
                    project_briefings=project_briefings,
                    status=BriefingStatus.completed,
                    completed_at=datetime.now(timezone.utc),
                )
                db.add(briefing)
                await db.flush()
                job.briefing_id = briefing.id

                # Slack notification for briefing
                try:
                    from app.services.slack.notifications import send_slack_notification
                    from app.services.slack.formatters import format_briefing_notification
                    await send_slack_notification(
                        db, org_id=org.id, channel_type="org",
                        blocks=format_briefing_notification(briefing.org_summary, str(briefing.week_start)),
                        text="주간 브리핑이 생성되었습니다.",
                    )
                except Exception:
                    pass

                # Notion briefing page creation (best-effort)
                try:
                    from app.services.notion.documents import create_briefing_page
                    await create_briefing_page(db, org.id, {
                        "week_start": str(briefing.week_start),
                        "org_summary": briefing.org_summary,
                    })
                except Exception:
                    pass

            job.status = JobStatus.completed
            job.completed_at = datetime.now(timezone.utc)

        except Exception as exc:
            logger.exception("AI job %s failed: %s", job_id, exc)
            job.retry_count += 1
            job.error_message = str(exc)[:500]
            if job.retry_count >= 3:
                job.status = JobStatus.failed
            else:
                job.status = JobStatus.queued
                await db.commit()
                delay = min(30 * job.retry_count, 120)
                await asyncio.sleep(delay)
                asyncio.create_task(process_ai_job(job.id))
                return

        finally:
            # Briefing jobs clean up per-project inside the loop above
            if repo_path and job.job_type != JobType.briefing and job.project_id:
                cleanup_repo(job.project_id, job.id)

        await db.commit()


async def recover_stuck_jobs() -> None:
    """Recover jobs left in queued/running state after a server restart."""
    async with async_session() as db:
        result = await db.execute(
            select(AIJobQueue).where(
                AIJobQueue.status.in_([JobStatus.queued, JobStatus.running])
            )
        )
        jobs = result.scalars().all()
        for job in jobs:
            if job.status == JobStatus.running:
                job.retry_count += 1
            if job.retry_count >= 3:
                job.status = JobStatus.failed
                job.error_message = "Server restarted during execution"
            else:
                job.status = JobStatus.queued
                asyncio.create_task(process_ai_job(job.id))
        await db.commit()
        logger.info("recover_stuck_jobs: processed %d stuck jobs", len(jobs))
