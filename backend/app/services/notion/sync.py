import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.notion import NotionConnection, NotionDatabaseMapping, NotionTaskMapping
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.project import Project
from app.models.activity_log import ActivityLog

try:
    from notion_client import AsyncClient as NotionClient
    HAS_NOTION = True
except ImportError:
    HAS_NOTION = False

# Status mapping
STATUS_TO_NOTION = {"todo": "To Do", "in_progress": "In Progress", "review": "Review", "done": "Done"}
NOTION_TO_STATUS = {v: k for k, v in STATUS_TO_NOTION.items()}
PRIORITY_TO_NOTION = {"low": "Low", "medium": "Medium", "high": "High", "critical": "Critical"}
NOTION_TO_PRIORITY = {v: k for k, v in PRIORITY_TO_NOTION.items()}


def task_to_notion_properties(task: Task) -> dict:
    """Convert task fields to Notion page properties."""
    props = {
        "Name": {"title": [{"text": {"content": task.title or ""}}]},
    }
    if task.status:
        props["Status"] = {"select": {"name": STATUS_TO_NOTION.get(task.status.value, "To Do")}}
    if task.priority:
        props["Priority"] = {"select": {"name": PRIORITY_TO_NOTION.get(task.priority.value, "Medium")}}
    if task.due_date:
        props["Due Date"] = {"date": {"start": str(task.due_date)}}
    if task.description:
        props["Description"] = {"rich_text": [{"text": {"content": task.description[:2000]}}]}
    return props


def notion_page_to_task_data(page: dict) -> dict:
    """Extract task fields from Notion page properties."""
    props = page.get("properties", {})
    data = {}

    # Title
    title_prop = props.get("Name", {}).get("title", [])
    if title_prop:
        data["title"] = title_prop[0].get("text", {}).get("content", "")

    # Status
    status_prop = props.get("Status", {}).get("select")
    if status_prop:
        status_name = status_prop.get("name", "")
        data["status"] = NOTION_TO_STATUS.get(status_name)

    # Priority
    priority_prop = props.get("Priority", {}).get("select")
    if priority_prop:
        priority_name = priority_prop.get("name", "")
        data["priority"] = NOTION_TO_PRIORITY.get(priority_name)

    # Due Date
    date_prop = props.get("Due Date", {}).get("date")
    if date_prop and date_prop.get("start"):
        data["due_date"] = date_prop["start"]

    # Description
    desc_prop = props.get("Description", {}).get("rich_text", [])
    if desc_prop:
        data["description"] = "".join(rt.get("text", {}).get("content", "") for rt in desc_prop)

    return data


async def sync_task_to_notion(db: AsyncSession, task: Task, project_id: uuid.UUID) -> None:
    """Sync a PM Agent task to Notion."""
    if not HAS_NOTION:
        return

    # Check if project has Notion DB mapped
    db_mapping = await db.execute(
        select(NotionDatabaseMapping).where(NotionDatabaseMapping.project_id == project_id)
    )
    mapping = db_mapping.scalar_one_or_none()
    if not mapping:
        return

    # Get Notion token
    project = await db.get(Project, project_id)
    if not project:
        return
    from app.services.notion.auth import get_notion_token
    token = await get_notion_token(db, project.org_id)
    if not token:
        return

    notion = NotionClient(auth=token)

    # Check existing task mapping
    task_mapping_result = await db.execute(
        select(NotionTaskMapping).where(NotionTaskMapping.task_id == task.id)
    )
    task_mapping = task_mapping_result.scalar_one_or_none()

    properties = task_to_notion_properties(task)

    if task_mapping:
        # Update existing page
        await notion.pages.update(page_id=task_mapping.notion_page_id, properties=properties)
        task_mapping.last_modified_at = datetime.now(timezone.utc)
    else:
        # Create new page
        page = await notion.pages.create(
            parent={"database_id": mapping.notion_database_id},
            properties=properties,
        )
        db.add(NotionTaskMapping(
            task_id=task.id, notion_page_id=page["id"],
            last_modified_at=datetime.now(timezone.utc),
        ))

    await db.commit()


async def poll_notion_changes():
    """Scheduled job: poll Notion for changes and sync to PM Agent."""
    if not HAS_NOTION:
        return

    async with async_session() as db:
        db_mappings = await db.execute(select(NotionDatabaseMapping))

        for mapping in db_mappings.scalars():
            try:
                project = await db.get(Project, mapping.project_id)
                if not project:
                    continue

                from app.services.notion.auth import get_notion_token
                token = await get_notion_token(db, project.org_id)
                if not token:
                    continue

                notion = NotionClient(auth=token)

                # Query pages modified since last sync
                filter_params = {}
                if mapping.last_synced_at:
                    filter_params = {
                        "filter": {
                            "timestamp": "last_edited_time",
                            "last_edited_time": {"after": mapping.last_synced_at.isoformat()}
                        }
                    }

                results = await notion.databases.query(
                    database_id=mapping.notion_database_id, **filter_params
                )

                for page in results.get("results", []):
                    page_id = page["id"]
                    notion_edited = datetime.fromisoformat(
                        page["last_edited_time"].replace("Z", "+00:00")
                    )

                    # Check existing mapping
                    task_map_result = await db.execute(
                        select(NotionTaskMapping).where(NotionTaskMapping.notion_page_id == page_id)
                    )
                    task_map = task_map_result.scalar_one_or_none()

                    task_data = notion_page_to_task_data(page)

                    if task_map and task_map.task_id:
                        # Existing task — check last-write-wins
                        if notion_edited > task_map.last_modified_at:
                            task = await db.get(Task, task_map.task_id)
                            if task:
                                if task_data.get("title"):
                                    task.title = task_data["title"]
                                if task_data.get("status"):
                                    task.status = TaskStatus(task_data["status"])
                                if task_data.get("priority"):
                                    task.priority = TaskPriority(task_data["priority"])
                                if "due_date" in task_data:
                                    from datetime import date
                                    task.due_date = date.fromisoformat(task_data["due_date"]) if task_data["due_date"] else None
                                if "description" in task_data:
                                    task.description = task_data["description"]
                                task_map.last_modified_at = notion_edited

                                # Log conflict
                                db.add(ActivityLog(
                                    project_id=mapping.project_id,
                                    action="notion_sync",
                                    detail={"page_id": page_id, "direction": "notion_to_pm"},
                                ))
                    else:
                        # New task from Notion
                        if not task_data.get("title"):
                            continue
                        new_task = Task(
                            project_id=mapping.project_id,
                            title=task_data["title"],
                            description=task_data.get("description"),
                            status=TaskStatus(task_data["status"]) if task_data.get("status") else TaskStatus.todo,
                            priority=TaskPriority(task_data["priority"]) if task_data.get("priority") else TaskPriority.medium,
                        )
                        if task_data.get("due_date"):
                            from datetime import date
                            new_task.due_date = date.fromisoformat(task_data["due_date"])
                        db.add(new_task)
                        await db.flush()
                        db.add(NotionTaskMapping(
                            task_id=new_task.id, notion_page_id=page_id,
                            last_modified_at=notion_edited,
                        ))

                mapping.last_synced_at = datetime.now(timezone.utc)
                await db.commit()

            except Exception:
                continue
