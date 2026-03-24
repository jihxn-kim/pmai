import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.calendar import GoogleCalendarConnection
from app.models.project import Project
from app.models.activity_log import ActivityLog
from app.models.user import User

try:
    from googleapiclient.discovery import build
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False


async def check_upcoming_meetings():
    """Scheduled job: check for meetings in next 30 min, send briefings."""
    if not HAS_GOOGLE:
        return

    async with async_session() as db:
        connections = await db.execute(select(GoogleCalendarConnection))

        for conn in connections.scalars():
            try:
                from app.services.calendar.auth import get_google_credentials
                creds = await get_google_credentials(db, conn.user_id)
                if not creds:
                    continue

                service = build("calendar", "v3", credentials=creds)
                now = datetime.now(timezone.utc)
                time_max = now + timedelta(minutes=30)

                events_result = service.events().list(
                    calendarId=conn.calendar_id,
                    timeMin=now.isoformat(),
                    timeMax=time_max.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                ).execute()

                for event in events_result.get("items", []):
                    event_id = event.get("id")
                    summary = event.get("summary", "")

                    # Check if already briefed for this event
                    existing = await db.execute(
                        select(ActivityLog).where(
                            ActivityLog.action == "meeting_briefing",
                            ActivityLog.detail["event_id"].astext == event_id,
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    # Fuzzy match project name
                    project = await resolve_project_from_event(db, summary, conn.user_id)
                    if not project:
                        continue

                    # Send briefing via Slack
                    await send_meeting_briefing(db, conn.user_id, project, event)

                    # Record that we briefed for this event
                    db.add(ActivityLog(
                        project_id=project.id,
                        user_id=conn.user_id,
                        action="meeting_briefing",
                        detail={"event_id": event_id, "event_summary": summary},
                    ))
                    await db.commit()

            except Exception:
                continue


async def resolve_project_from_event(db: AsyncSession, event_summary: str, user_id: uuid.UUID):
    """Try to match event title to a project name."""
    from app.models.project import Project, ProjectMember
    # Get user's projects
    result = await db.execute(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user_id)
    )
    for project in result.scalars():
        if project.name.lower() in event_summary.lower():
            return project
    return None


async def send_meeting_briefing(db: AsyncSession, user_id: uuid.UUID, project, event: dict):
    """Generate and send a meeting briefing via Slack DM."""
    try:
        from app.services.dashboard_service import get_task_distribution, get_project_issues
        from app.services.slack.notifications import send_slack_notification

        dist = await get_task_distribution(db, project.id)
        issues = await get_project_issues(db, project.id)

        summary_text = f"📋 *{event.get('summary', '')}* 회의 브리핑\n\n"
        summary_text += f"*{project.name}* 프로젝트 현황:\n"
        summary_text += f"• 진척도: {dist.progress:.0f}% ({dist.done}/{dist.total})\n"
        summary_text += f"• 진행 중: {dist.in_progress}개\n"

        if issues.items:
            summary_text += f"• 문제점: {len(issues.items)}건\n"
            for item in issues.items[:3]:
                summary_text += f"  - {item.title}\n"

        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": summary_text}}]

        # Get project org_id
        from app.models.project import Project as ProjectModel
        proj = await db.get(ProjectModel, project.id)
        if proj:
            await send_slack_notification(
                db, org_id=proj.org_id, channel_type="dm",
                user_id=user_id, blocks=blocks, text=summary_text,
            )
    except Exception:
        pass
