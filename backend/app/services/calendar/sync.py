import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import GoogleCalendarConnection, CalendarEventMapping
from app.models.task import Task, TaskStatus

try:
    from googleapiclient.discovery import build
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False


async def sync_task_to_calendar(db: AsyncSession, task: Task) -> None:
    """Sync a task's due_date to Google Calendar as an event."""
    if not HAS_GOOGLE or not task.assignee_id or not task.due_date:
        return

    from app.services.calendar.auth import get_google_credentials

    creds = await get_google_credentials(db, task.assignee_id)
    if not creds:
        return

    # Get calendar connection for calendar_id
    result = await db.execute(
        select(GoogleCalendarConnection).where(GoogleCalendarConnection.user_id == task.assignee_id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        return

    service = build("calendar", "v3", credentials=creds)

    # Check existing mapping
    mapping_result = await db.execute(
        select(CalendarEventMapping).where(CalendarEventMapping.task_id == task.id)
    )
    mapping = mapping_result.scalar_one_or_none()

    event_body = {
        "summary": f"[PM Agent] {task.title}",
        "description": task.description or "",
        "start": {"date": str(task.due_date)},
        "end": {"date": str(task.due_date)},
    }

    if task.status == TaskStatus.done:
        # Delete event if task is done
        if mapping:
            try:
                service.events().delete(calendarId=conn.calendar_id, eventId=mapping.google_event_id).execute()
            except Exception:
                pass
            await db.delete(mapping)
            await db.commit()
        return

    if mapping:
        # Update existing event
        try:
            service.events().update(
                calendarId=conn.calendar_id, eventId=mapping.google_event_id, body=event_body
            ).execute()
            mapping.last_synced_at = datetime.now(timezone.utc)
        except Exception:
            pass
    else:
        # Create new event
        try:
            event = service.events().insert(calendarId=conn.calendar_id, body=event_body).execute()
            db.add(CalendarEventMapping(
                task_id=task.id, google_event_id=event["id"],
            ))
        except Exception:
            pass

    await db.commit()


async def sync_calendar_to_tasks(db: AsyncSession, user_id: uuid.UUID, changed_events: list[dict]) -> None:
    """Process changed calendar events and update task due_dates."""
    for event_data in changed_events:
        event_id = event_data.get("id")
        if not event_id:
            continue

        result = await db.execute(
            select(CalendarEventMapping).where(CalendarEventMapping.google_event_id == event_id)
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            continue

        task = await db.get(Task, mapping.task_id)
        if not task:
            continue

        # Event deleted
        if event_data.get("status") == "cancelled":
            task.due_date = None
            await db.delete(mapping)
        else:
            # Date changed
            start = event_data.get("start", {})
            new_date = start.get("date") or (start.get("dateTime", "")[:10] if start.get("dateTime") else None)
            if new_date:
                from datetime import date as date_type
                task.due_date = date_type.fromisoformat(new_date)
                mapping.last_synced_at = datetime.now(timezone.utc)

    await db.commit()
