"""Standalone MCP server for PM Agent DB tools.

Runs as a separate process (stdio) — Agent SDK launches this automatically.
Usage: python -m app.services.ai.pm_mcp_server <org_id> [default_project_id]
"""
import asyncio
import json
import sys
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "")
engine = create_async_engine(DATABASE_URL, pool_size=2, max_overflow=0)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

ORG_ID = sys.argv[1] if len(sys.argv) > 1 else ""
DEFAULT_PROJECT_ID = sys.argv[2] if len(sys.argv) > 2 else ""

server = Server("pm-agent")

PROJECT_NAME_PROP = {
    "project_name": {
        "type": "string",
        "description": "프로젝트 이름 (생략 시 기본 프로젝트 사용)",
    }
}


async def resolve_project_id(db: AsyncSession, arguments: dict) -> str | None:
    """Resolve project_id from project_name argument, fallback to default."""
    project_name = arguments.get("project_name")
    if project_name:
        from app.models.project import Project
        import uuid
        result = await db.execute(
            select(Project).where(
                Project.org_id == uuid.UUID(ORG_ID),
                Project.name.ilike(f"%{project_name}%"),
            )
        )
        project = result.scalars().first()
        if project:
            return str(project.id)
        return None
    return DEFAULT_PROJECT_ID or None


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_org_projects",
            description="Get all projects in the organization with their status and GitHub repo.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_project_tasks",
            description="Get all tasks for a project with status, assignee, priority, and due date.",
            inputSchema={"type": "object", "properties": PROJECT_NAME_PROP, "required": []},
        ),
        types.Tool(
            name="get_project_members",
            description="Get all members of a project with their roles.",
            inputSchema={"type": "object", "properties": PROJECT_NAME_PROP, "required": []},
        ),
        types.Tool(
            name="get_project_issues",
            description="Get detected problems: overdue tasks, stale PRs, unassigned tasks.",
            inputSchema={"type": "object", "properties": PROJECT_NAME_PROP, "required": []},
        ),
        types.Tool(
            name="get_project_progress",
            description="Get task completion stats: total, done, in_progress, todo counts and percentage.",
            inputSchema={"type": "object", "properties": PROJECT_NAME_PROP, "required": []},
        ),
        types.Tool(
            name="get_pull_requests",
            description="Get pull requests for a project with state and review status.",
            inputSchema={"type": "object", "properties": PROJECT_NAME_PROP, "required": []},
        ),
        types.Tool(
            name="get_recent_ai_reviews",
            description="Get recent AI analysis/review results for a project.",
            inputSchema={"type": "object", "properties": PROJECT_NAME_PROP, "required": []},
        ),
        types.Tool(
            name="get_project_activity",
            description="Get recent activity log: commits, PR events, task changes.",
            inputSchema={"type": "object", "properties": PROJECT_NAME_PROP, "required": []},
        ),
        types.Tool(
            name="resolve_slack_user",
            description="Find organization member by Slack user ID. Returns name, github_username, email, role.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slack_user_id": {"type": "string", "description": "Slack user ID (e.g. U12345678)"},
                },
                "required": ["slack_user_id"],
            },
        ),
        types.Tool(
            name="resolve_member_slack",
            description="Find Slack user ID by member name or GitHub username. Useful for sending notifications.",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_name": {"type": "string", "description": "멤버 이름 또는 GitHub username"},
                },
                "required": ["member_name"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    import traceback
    try:
        from app.services.ai.db_queries import execute_db_query

        async with async_session() as db:
            if name == "get_org_projects":
                result = await execute_db_query(db, "org_projects", {"org_id": ORG_ID})
                return [types.TextContent(type="text", text=json.dumps(result, default=str))]

            if name == "resolve_slack_user":
                result = await execute_db_query(db, "resolve_slack_user", {
                    "slack_user_id": arguments.get("slack_user_id", ""),
                    "org_id": ORG_ID,
                })
                return [types.TextContent(type="text", text=json.dumps(result, default=str))]

            if name == "resolve_member_slack":
                result = await execute_db_query(db, "resolve_member_slack", {
                    "member_name": arguments.get("member_name", ""),
                })
                return [types.TextContent(type="text", text=json.dumps(result, default=str))]

            # All other tools need a project_id
            project_id = await resolve_project_id(db, arguments)
            if not project_id:
                project_name = arguments.get("project_name", "")
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": f"프로젝트 '{project_name}'을 찾을 수 없습니다. get_org_projects로 프로젝트 목록을 확인하세요."}),
                )]

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

            result = await execute_db_query(db, query_name, {"project_id": project_id})
            return [types.TextContent(type="text", text=json.dumps(result, default=str))]
    except Exception as e:
        print(f"[MCP ERROR] {name}: {type(e).__name__}: {e}", flush=True)
        print(traceback.format_exc()[-300:], flush=True)
        return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
