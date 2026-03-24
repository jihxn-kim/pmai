"""Claude tool_use definitions and executor for the Slack bot."""

import asyncio
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_job_queue import AIJobQueue, JobStatus, JobTrigger, JobType
from app.models.project import Project
from app.models.pull_request import PRState, PullRequest
from app.models.weekly_briefing import BriefingStatus, WeeklyBriefing
from app.services import dashboard_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

SLACK_TOOLS: list[dict] = [
    {
        "name": "get_project_status",
        "description": (
            "Get the current status and progress of a specific project, "
            "including task counts and open pull requests."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "The name of the project to look up.",
                }
            },
            "required": ["project_name"],
        },
    },
    {
        "name": "get_my_tasks",
        "description": "Get the list of tasks assigned to the current user that are not yet done.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "request_code_review",
        "description": "Request an AI code review for a pull request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pr_number": {
                    "type": "integer",
                    "description": "The pull request number to review.",
                },
                "project_name": {
                    "type": "string",
                    "description": "Optional project name. If omitted the first matching PR is used.",
                },
            },
            "required": ["pr_number"],
        },
    },
    {
        "name": "get_latest_briefing",
        "description": "Get the most recent weekly project briefing for the organisation.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_project_issues",
        "description": (
            "Get current issues for a project such as overdue tasks, "
            "stale PRs, pending reviews, and unassigned tasks."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "The name of the project to check for issues.",
                }
            },
            "required": ["project_name"],
        },
    },
    {
        "name": "run_project_analysis",
        "description": "Run an AI-powered analysis for a project and queue the result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "The name of the project to analyse.",
                }
            },
            "required": ["project_name"],
        },
    },
]


# ---------------------------------------------------------------------------
# Intent parsing
# ---------------------------------------------------------------------------

async def parse_intent(user_message: str) -> dict:
    """Use Claude Agent SDK to parse user intent from natural language.

    Returns::

        {"tool": <name>, "input": <dict>, "text": None}
        or
        {"tool": None, "input": None, "text": <clarification string>}
    """
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
    except ImportError:
        return {"tool": None, "input": None, "text": "AI 서비스를 사용할 수 없습니다."}

    system_prompt = """You are a PM Agent assistant. Parse the user's request and respond with a JSON object indicating which action to take.

Available actions:
- get_project_status: requires project_name
- get_my_tasks: no parameters needed
- request_code_review: requires pr_number, optionally project_name
- get_latest_briefing: no parameters needed
- get_project_issues: requires project_name
- run_project_analysis: requires project_name

Respond ONLY with a JSON object in this format:
{"tool": "action_name", "input": {"param": "value"}}

If you can't determine the action, respond with:
{"tool": null, "text": "clarification message"}"""

    try:
        result = None
        async for message in query(
            prompt=user_message,
            options=ClaudeAgentOptions(
                system_prompt=system_prompt,
                max_turns=1,
            )
        ):
            if isinstance(message, ResultMessage):
                result = message.result

        if not result:
            return {"tool": None, "input": None, "text": "요청을 이해하지 못했습니다."}

        import json
        # Strip markdown code block if present
        text = result.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        parsed = json.loads(text)
        return {
            "tool": parsed.get("tool"),
            "input": parsed.get("input", {}),
            "text": parsed.get("text"),
        }
    except Exception as e:
        return {"tool": None, "input": None, "text": f"요청 처리 중 오류가 발생했습니다: {str(e)[:100]}"}


# ---------------------------------------------------------------------------
# Project resolver
# ---------------------------------------------------------------------------

async def resolve_project(
    db: AsyncSession,
    project_name: str,
    org_id: uuid.UUID,
) -> Project | None:
    """Fuzzy-match a project by name (ILIKE) within an org."""
    result = await db.execute(
        select(Project).where(
            Project.org_id == org_id,
            Project.name.ilike(f"%{project_name}%"),
        )
    )
    return result.scalars().first()


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

async def execute_tool(
    db: AsyncSession,
    tool_name: str,
    tool_input: dict,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
) -> dict:
    """Dispatch a parsed tool call to the appropriate service."""
    try:
        if tool_name == "get_project_status":
            return await _tool_get_project_status(db, tool_input, org_id)

        if tool_name == "get_my_tasks":
            return await _tool_get_my_tasks(db, user_id)

        if tool_name == "request_code_review":
            return await _tool_request_code_review(db, tool_input, user_id, org_id)

        if tool_name == "get_latest_briefing":
            return await _tool_get_latest_briefing(db, org_id)

        if tool_name == "get_project_issues":
            return await _tool_get_project_issues(db, tool_input, org_id)

        if tool_name == "run_project_analysis":
            return await _tool_run_project_analysis(db, tool_input, user_id, org_id)

        return {"error": f"Unknown tool: {tool_name}"}

    except Exception as exc:
        logger.exception("execute_tool '%s' failed: %s", tool_name, exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Individual tool implementations
# ---------------------------------------------------------------------------

async def _tool_get_project_status(
    db: AsyncSession,
    tool_input: dict,
    org_id: uuid.UUID,
) -> dict:
    project = await resolve_project(db, tool_input["project_name"], org_id)
    if not project:
        return {"error": f"프로젝트 '{tool_input['project_name']}'을 찾을 수 없습니다."}

    distribution = await dashboard_service.get_task_distribution(db, project.id)

    open_pr_result = await db.execute(
        select(func.count(PullRequest.id)).where(
            PullRequest.project_id == project.id,
            PullRequest.state == PRState.open,
        )
    )
    open_prs = open_pr_result.scalar_one()

    return {
        "type": "project_status",
        "project_name": project.name,
        "progress": distribution.progress,
        "done": distribution.done,
        "total": distribution.total,
        "in_progress": distribution.in_progress,
        "open_prs": open_prs,
    }


async def _tool_get_my_tasks(db: AsyncSession, user_id: uuid.UUID) -> dict:
    result = await dashboard_service.get_my_tasks(db, user_id)
    tasks = [
        {
            "title": t.title,
            "status": t.status.value,
            "due_date": str(t.due_date) if t.due_date else None,
        }
        for t in result["data"]
    ]
    return {"type": "my_tasks", "tasks": tasks, "total": result["meta"]["total"]}


async def _tool_request_code_review(
    db: AsyncSession,
    tool_input: dict,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
) -> dict:
    pr_number = tool_input["pr_number"]
    project_name = tool_input.get("project_name")

    # Build base query for the PR
    pr_query = select(PullRequest).where(PullRequest.number == pr_number)

    if project_name:
        project = await resolve_project(db, project_name, org_id)
        if not project:
            return {"error": f"프로젝트 '{project_name}'을 찾을 수 없습니다."}
        pr_query = pr_query.where(PullRequest.project_id == project.id)
    else:
        # Restrict to projects in this org
        org_project_ids = (
            select(Project.id).where(Project.org_id == org_id).scalar_subquery()
        )
        pr_query = pr_query.where(PullRequest.project_id.in_(org_project_ids))

    pr_result = await db.execute(pr_query)
    pr = pr_result.scalars().first()
    if not pr:
        return {"error": f"PR #{pr_number}을 찾을 수 없습니다."}

    job = AIJobQueue(
        project_id=pr.project_id,
        org_id=org_id,
        job_type=JobType.code_review,
        trigger=JobTrigger.manual,
        status=JobStatus.queued,
        payload={
            "pr_number": pr_number,
            "base": pr.base_ref,
            "head": pr.head_ref,
            "requested_by": str(user_id),
        },
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from app.services.ai.worker import process_ai_job  # noqa: PLC0415

    asyncio.create_task(process_ai_job(job.id))

    return {
        "type": "code_review_queued",
        "job_id": str(job.id),
        "pr_number": pr_number,
        "message": f"PR #{pr_number} 코드리뷰가 요청되었습니다.",
    }


async def _tool_get_latest_briefing(db: AsyncSession, org_id: uuid.UUID) -> dict:
    result = await db.execute(
        select(WeeklyBriefing)
        .where(
            WeeklyBriefing.org_id == org_id,
            WeeklyBriefing.status == BriefingStatus.completed,
        )
        .order_by(WeeklyBriefing.week_start.desc())
        .limit(1)
    )
    briefing = result.scalar_one_or_none()
    if not briefing:
        return {"error": "아직 생성된 주간 브리핑이 없습니다."}

    return {
        "type": "latest_briefing",
        "week_start": str(briefing.week_start),
        "org_summary": briefing.org_summary,
        "project_briefings": briefing.project_briefings,
    }


async def _tool_get_project_issues(
    db: AsyncSession,
    tool_input: dict,
    org_id: uuid.UUID,
) -> dict:
    project = await resolve_project(db, tool_input["project_name"], org_id)
    if not project:
        return {"error": f"프로젝트 '{tool_input['project_name']}'을 찾을 수 없습니다."}

    issues_response = await dashboard_service.get_project_issues(db, project.id)
    issues = [
        {"type": item.type, "title": item.title, "detail": item.detail}
        for item in issues_response.items
    ]
    return {
        "type": "project_issues",
        "project_name": project.name,
        "issues": issues,
        "total": issues_response.total,
    }


async def _tool_run_project_analysis(
    db: AsyncSession,
    tool_input: dict,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
) -> dict:
    project = await resolve_project(db, tool_input["project_name"], org_id)
    if not project:
        return {"error": f"프로젝트 '{tool_input['project_name']}'을 찾을 수 없습니다."}

    job = AIJobQueue(
        project_id=project.id,
        org_id=org_id,
        job_type=JobType.analysis,
        trigger=JobTrigger.manual,
        status=JobStatus.queued,
        payload={"requested_by": str(user_id)},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from app.services.ai.worker import process_ai_job  # noqa: PLC0415

    asyncio.create_task(process_ai_job(job.id))

    return {
        "type": "analysis_queued",
        "job_id": str(job.id),
        "project_name": project.name,
        "message": f"'{project.name}' 프로젝트 AI 분석이 요청되었습니다.",
    }
