"""Standalone MCP server for PM Agent DB tools.

Runs as a separate process (stdio) — Agent SDK launches this automatically.
Usage: python -m app.services.ai.pm_mcp_server <project_id>
"""
import asyncio
import json
import sys
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# DB connection setup — uses DATABASE_URL from environment
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "")
engine = create_async_engine(DATABASE_URL, pool_size=2, max_overflow=0)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

PROJECT_ID = sys.argv[1] if len(sys.argv) > 1 else ""

server = Server("pm-agent")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_project_tasks",
            description="Get all tasks for the project with status, assignee, priority, and due date.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_project_members",
            description="Get all members of the project with their roles.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_project_issues",
            description="Get detected problems: overdue tasks, stale PRs, unassigned tasks.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_project_progress",
            description="Get task completion stats: total, done, in_progress, todo counts and percentage.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_pull_requests",
            description="Get pull requests for the project with state and review status.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_recent_ai_reviews",
            description="Get recent AI analysis/review results for the project.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_project_activity",
            description="Get recent activity log: commits, PR events, task changes.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    from app.services.ai.db_queries import execute_db_query

    async with async_session() as db:
        query_map = {
            "get_project_tasks": "tasks",
            "get_project_members": "members",
            "get_project_issues": "issues",
            "get_project_progress": "progress",
            "get_pull_requests": "pull_requests",
            "get_recent_ai_reviews": "ai_reviews",
            "get_project_activity": "activity",
        }
        query_name = query_map.get(name)
        if not query_name:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

        result = await execute_db_query(db, query_name, {"project_id": PROJECT_ID})
        return [types.TextContent(type="text", text=json.dumps(result, default=str))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
