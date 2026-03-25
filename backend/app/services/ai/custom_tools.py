"""Custom tools for the AI Agent — gives Claude direct access to PM Agent DB data."""
from __future__ import annotations

import json
import logging
from datetime import date

logger = logging.getLogger(__name__)

try:
    from claude_agent_sdk import tool, create_sdk_mcp_server
    HAS_SDK = True
except ImportError:
    tool = None
    create_sdk_mcp_server = None
    HAS_SDK = False


def build_pm_tools_server(db_query_fn):
    """Build an in-process MCP server with PM Agent DB tools.

    Args:
        db_query_fn: async function(query_name, params) -> dict
            Executes a named query against the DB and returns results.
    """
    if not HAS_SDK:
        return None

    @tool(
        "get_project_tasks",
        "Get all tasks for a project with their status, assignee, priority, and due date. "
        "Use this to understand what work is planned, in progress, or completed.",
        {"project_id": str},
    )
    async def get_project_tasks(args):
        result = await db_query_fn("tasks", {"project_id": args["project_id"]})
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}

    @tool(
        "get_project_members",
        "Get all members of a project with their roles. "
        "Use this to understand who is working on the project and their responsibilities.",
        {"project_id": str},
    )
    async def get_project_members(args):
        result = await db_query_fn("members", {"project_id": args["project_id"]})
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}

    @tool(
        "get_project_issues",
        "Get detected problems: overdue tasks, stale PRs, pending reviews, unassigned tasks. "
        "Use this to identify blockers and risks.",
        {"project_id": str},
    )
    async def get_project_issues(args):
        result = await db_query_fn("issues", {"project_id": args["project_id"]})
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}

    @tool(
        "get_project_progress",
        "Get task completion statistics: total, done, in progress, todo counts and percentage. "
        "Use this for progress assessment.",
        {"project_id": str},
    )
    async def get_project_progress(args):
        result = await db_query_fn("progress", {"project_id": args["project_id"]})
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}

    @tool(
        "get_pull_requests",
        "Get pull requests for a project with their state, author, and review status. "
        "Use this to understand code review bottlenecks and merge activity.",
        {"project_id": str},
    )
    async def get_pull_requests(args):
        result = await db_query_fn("pull_requests", {"project_id": args["project_id"]})
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
