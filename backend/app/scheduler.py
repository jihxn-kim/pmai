import asyncio
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.database import async_session
from app.models.organization import Organization
from app.models.ai_job_queue import AIJobQueue, JobType, JobTrigger
from app.models.task import Task, TaskStatus
from app.models.project import Project
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


async def check_deadline_reminders():
    """Hourly check for deadline reminders."""
    try:
        from app.services.slack.notifications import send_slack_notification
        from app.services.slack.formatters import format_deadline_reminder
    except ImportError:
        return

    async with async_session() as db:
        tomorrow = date.today() + timedelta(days=1)

        # D-1 tasks
        d1_result = await db.execute(
            select(Task).where(
                Task.due_date == tomorrow,
                Task.status != TaskStatus.done,
                Task.assignee_id.isnot(None),
            )
        )
        for task in d1_result.scalars():
            project = await db.get(Project, task.project_id)
            if project:
                await send_slack_notification(
                    db, org_id=project.org_id, channel_type="dm",
                    user_id=task.assignee_id,
                    blocks=format_deadline_reminder(task.title, 1, False),
                    text=f"⏰ '{task.title}' 내일 마감입니다",
                )

        # Overdue tasks
        overdue_result = await db.execute(
            select(Task).where(
                Task.due_date < date.today(),
                Task.status != TaskStatus.done,
                Task.assignee_id.isnot(None),
            )
        )
        for task in overdue_result.scalars():
            project = await db.get(Project, task.project_id)
            if not project:
                continue
            days = (date.today() - task.due_date).days
            await send_slack_notification(
                db, org_id=project.org_id, channel_type="dm",
                user_id=task.assignee_id,
                blocks=format_deadline_reminder(task.title, days, True),
                text=f"🚨 '{task.title}' 마감 {days}일 초과",
            )
            await send_slack_notification(
                db, org_id=project.org_id, channel_type="project",
                project_id=project.id,
                blocks=format_deadline_reminder(task.title, days, True),
                text=f"🚨 '{task.title}' 마감 {days}일 초과",
            )


# Register: every hour at :00
scheduler.add_job(check_deadline_reminders, CronTrigger(minute=0))
