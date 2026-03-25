"""Custom tools for the AI Agent — gives Claude direct access to PM Agent DB data."""
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

try:
    from claude_agent_sdk import tool, create_sdk_mcp_server
    HAS_SDK = True
except ImportError:
    tool = None
    create_sdk_mcp_server = None
    HAS_SDK = False


def build_pm_tools_server(project_id: str):
    """Build an in-process MCP server with PM Agent DB tools.

    Each tool call opens its own DB session from the connection pool.
    """
    if not HAS_SDK:
        return None

    @tool(
        "get_project_tasks",
        "Get all tasks for a project with their status, assignee, priority, and due date.",
        {},
    )
    async def get_project_tasks(args):
        from app.database import async_session
        from app.services.ai.db_queries import execute_db_query
        async with async_session() as db:
            result = await execute_db_query(db, "tasks", {"project_id": project_id})
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}

    @tool(
        "get_project_members",
        "Get all members of a project with their roles.",
        {},
    )
    async def get_project_members(args):
        from app.database import async_session
        from app.services.ai.db_queries import execute_db_query
        async with async_session() as db:
            result = await execute_db_query(db, "members", {"project_id": project_id})
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}

    @tool(
        "get_project_issues",
        "Get detected problems: overdue tasks, stale PRs, unassigned tasks.",
        {},
    )
    async def get_project_issues(args):
        from app.database import async_session
        from app.services.ai.db_queries import execute_db_query
        async with async_session() as db:
            result = await execute_db_query(db, "issues", {"project_id": project_id})
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}

    @tool(
        "get_project_progress",
        "Get task completion statistics: total, done, in progress, todo counts and percentage.",
        {},
    )
    async def get_project_progress(args):
        from app.database import async_session
        from app.services.ai.db_queries import execute_db_query
        async with async_session() as db:
            result = await execute_db_query(db, "progress", {"project_id": project_id})
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}

    @tool(
        "get_pull_requests",
        "Get pull requests for a project with their state and review status.",
        {},
    )
    async def get_pull_requests(args):
        from app.database import async_session
        from app.services.ai.db_queries import execute_db_query
        async with async_session() as db:
            result = await execute_db_query(db, "pull_requests", {"project_id": project_id})
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}

    server = create_sdk_mcp_server(
        name="pm_agent",
        version="1.0.0",
        tools=[
            get_project_tasks,
            get_project_members,
            get_project_issues,
            get_project_progress,
            get_pull_requests,
        ],
    )
    return server
