import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.database import async_session
from app.models.organization import Organization
from app.models.ai_job_queue import AIJobQueue, JobType, JobTrigger
from app.services.ai.worker import process_ai_job

scheduler = AsyncIOScheduler()


async def generate_weekly_briefings():
    """Scheduled job: create briefing jobs for all organizations."""
    async with async_session() as db:
        orgs = await db.execute(select(Organization))
        for org in orgs.scalars():
            job = AIJobQueue(
                org_id=org.id,
                job_type=JobType.briefing,
                trigger=JobTrigger.schedule,
                payload={"org_id": str(org.id)},
            )
            db.add(job)
            await db.flush()
            asyncio.create_task(process_ai_job(job.id))
        await db.commit()


scheduler.add_job(generate_weekly_briefings, CronTrigger(day_of_week="mon", hour=9, minute=0))
