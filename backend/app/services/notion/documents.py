import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notion import NotionConnection, NotionDatabaseMapping

try:
    from notion_client import AsyncClient as NotionClient
    HAS_NOTION = True
except ImportError:
    HAS_NOTION = False


async def read_project_documents(db: AsyncSession, project_id: uuid.UUID) -> str:
    """Read Notion pages linked to a project, return as plain text."""
    if not HAS_NOTION:
        return ""

    from app.models.project import Project
    project = await db.get(Project, project_id)
    if not project:
        return ""

    from app.services.notion.auth import get_notion_token
    token = await get_notion_token(db, project.org_id)
    if not token:
        return ""

    db_mapping = await db.execute(
        select(NotionDatabaseMapping).where(NotionDatabaseMapping.project_id == project_id)
    )
    mapping = db_mapping.scalar_one_or_none()
    if not mapping:
        return ""

    notion = NotionClient(auth=token)

    try:
        results = await notion.databases.query(database_id=mapping.notion_database_id, page_size=10)
        texts = []
        for page in results.get("results", []):
            title_prop = page.get("properties", {}).get("Name", {}).get("title", [])
            title = title_prop[0].get("text", {}).get("content", "") if title_prop else "Untitled"
            texts.append(f"## {title}")

            # Read page content blocks
            blocks = await notion.blocks.children.list(block_id=page["id"])
            for block in blocks.get("results", []):
                block_type = block.get("type", "")
                block_data = block.get(block_type, {})
                if "rich_text" in block_data:
                    text = "".join(rt.get("text", {}).get("content", "") for rt in block_data["rich_text"])
                    texts.append(text)

        return "\n\n".join(texts)
    except Exception:
        return ""


async def create_briefing_page(db: AsyncSession, org_id: uuid.UUID, briefing_data: dict) -> str | None:
    """Create a Notion page with weekly briefing content. Returns page_id."""
    if not HAS_NOTION:
        return None

    from app.services.notion.auth import get_notion_token
    token = await get_notion_token(db, org_id)
    if not token:
        return None

    notion = NotionClient(auth=token)

    # Find any Notion DB for this org (use first project's DB)
    from app.models.project import Project
    projects = await db.execute(
        select(Project).where(Project.org_id == org_id).limit(1)
    )
    project = projects.scalar_one_or_none()
    if not project:
        return None

    db_mapping = await db.execute(
        select(NotionDatabaseMapping).where(NotionDatabaseMapping.project_id == project.id)
    )
    mapping = db_mapping.scalar_one_or_none()
    if not mapping:
        return None

    try:
        # Create page as child of the database's parent
        week_start = briefing_data.get("week_start", "")
        page = await notion.pages.create(
            parent={"database_id": mapping.notion_database_id},
            properties={
                "Name": {"title": [{"text": {"content": f"Weekly Briefing - {week_start}"}}]},
                "Status": {"select": {"name": "Done"}},
            },
            children=[
                {"type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": "Weekly Briefing"}}]}},
                {"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": str(briefing_data.get("org_summary", ""))}}]}},
            ]
        )
        return page["id"]
    except Exception:
        return None
