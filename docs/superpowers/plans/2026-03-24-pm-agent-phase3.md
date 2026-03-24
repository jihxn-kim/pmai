# PM Agent Phase 3: Slack Bot + Automation Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Slack bot with mention-based natural language interface and automated notifications for GitHub events, deadlines, AI reviews, and weekly briefings.

**Architecture:** Slack events arrive via HTTP POST, Claude API tool_use parses intent, existing services execute the action, results are formatted as Block Kit messages. Notifications are sent to project channels, org channels, and DMs via a shared notification service.

**Tech Stack:** slack-bolt, slack-sdk, Claude API (tool_use), APScheduler (deadline reminders), existing FastAPI + SQLAlchemy stack.

**Spec:** `docs/superpowers/specs/2026-03-24-pm-agent-phase3-design.md`

---

## File Structure

### Backend (new/modified)

```
backend/
├── app/
│   ├── config.py                              # MODIFY: add Slack config
│   ├── main.py                                # MODIFY: register slack router
│   ├── scheduler.py                           # MODIFY: add deadline reminder cron
│   ├── models/
│   │   ├── __init__.py                        # MODIFY: re-export Slack models
│   │   └── slack.py                           # CREATE: SlackWorkspace, SlackChannelMapping, SlackUserMapping
│   ├── schemas/
│   │   └── slack.py                           # CREATE: Slack Pydantic schemas
│   ├── services/
│   │   ├── slack/
│   │   │   ├── __init__.py                    # CREATE
│   │   │   ├── notifications.py               # CREATE: send_slack_notification()
│   │   │   ├── formatters.py                  # CREATE: Block Kit message builders
│   │   │   ├── tools.py                       # CREATE: Claude tool_use definitions + executor
│   │   │   └── bot.py                         # CREATE: mention handler, intent parsing
│   │   ├── github_service.py                  # MODIFY: add Slack notifications after events
│   │   └── ai/worker.py                       # MODIFY: add Slack notifications after AI jobs
│   ├── routers/
│   │   └── slack.py                           # CREATE: all Slack endpoints
│   └── tests/
│       ├── test_slack_notifications.py        # CREATE
│       ├── test_slack_bot.py                  # CREATE
│       └── test_slack_router.py               # CREATE
├── alembic/versions/                          # New migration
├── requirements.txt                           # MODIFY: add slack deps
└── .env.example                               # MODIFY: add Slack vars
```

### Frontend (new/modified)

```
frontend/src/
├── hooks/
│   └── use-slack.ts                                     # CREATE
├── components/
│   └── slack/
│       ├── slack-connect.tsx                             # CREATE
│       ├── channel-mapping.tsx                           # CREATE
│       └── user-mapping.tsx                              # CREATE
└── app/(dashboard)/
    └── org/[slug]/
        └── settings/page.tsx                            # MODIFY: add Slack section
```

---

## Task 1: Dependencies + Configuration

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Modify: `.env.example`

- [ ] **Step 1: Update requirements.txt** — add `slack-bolt>=1.18.0` and `slack-sdk>=3.27.0`

- [ ] **Step 2: Update config.py** — add to Settings:
```python
# Slack
slack_client_id: str = ""
slack_client_secret: str = ""
slack_signing_secret: str = ""
```

- [ ] **Step 3: Update .env.example** — add Slack section

- [ ] **Step 4: Commit**
```bash
git commit -m "feat: add Slack dependencies and configuration"
```

---

## Task 2: Database Models + Migration

**Files:**
- Create: `backend/app/models/slack.py`
- Modify: `backend/app/models/__init__.py`
- Alembic migration

- [ ] **Step 1: Create `backend/app/models/slack.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func

from app.database import Base


class SlackWorkspace(Base):
    __tablename__ = "slack_workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), unique=True)
    slack_team_id: Mapped[str] = mapped_column(String, unique=True)
    slack_bot_token: Mapped[str] = mapped_column(String)
    slack_org_channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SlackChannelMapping(Base):
    __tablename__ = "slack_channel_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    slack_channel_id: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SlackUserMapping(Base):
    __tablename__ = "slack_user_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    slack_user_id: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Update `__init__.py`** — add re-exports

- [ ] **Step 3: Generate and apply migration**

- [ ] **Step 4: Commit**
```bash
git commit -m "feat: add Slack workspace, channel mapping, and user mapping models"
```

---

## Task 3: Notification Service

**Files:**
- Create: `backend/app/services/slack/__init__.py`
- Create: `backend/app/services/slack/notifications.py`
- Create: `backend/app/services/slack/formatters.py`

- [ ] **Step 1: Create `notifications.py`**

Core notification function that all other code calls:

```python
import uuid
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.slack import SlackWorkspace, SlackChannelMapping, SlackUserMapping

logger = logging.getLogger(__name__)


async def get_bot_token(db: AsyncSession, org_id: uuid.UUID) -> str | None:
    result = await db.execute(select(SlackWorkspace).where(SlackWorkspace.org_id == org_id))
    workspace = result.scalar_one_or_none()
    return workspace.slack_bot_token if workspace else None


async def get_channel_id(db: AsyncSession, channel_type: str, org_id: uuid.UUID,
                         project_id: uuid.UUID | None = None) -> str | None:
    if channel_type == "project" and project_id:
        result = await db.execute(
            select(SlackChannelMapping).where(SlackChannelMapping.project_id == project_id)
        )
        mapping = result.scalar_one_or_none()
        return mapping.slack_channel_id if mapping else None
    elif channel_type == "org":
        result = await db.execute(select(SlackWorkspace).where(SlackWorkspace.org_id == org_id))
        workspace = result.scalar_one_or_none()
        return workspace.slack_org_channel_id if workspace else None
    return None


async def get_slack_user_id(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    result = await db.execute(select(SlackUserMapping).where(SlackUserMapping.user_id == user_id))
    mapping = result.scalar_one_or_none()
    return mapping.slack_user_id if mapping else None


async def send_slack_notification(
    db: AsyncSession,
    org_id: uuid.UUID,
    channel_type: str,  # "project" | "org" | "dm"
    project_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    blocks: list[dict] | None = None,
    text: str = "",
) -> bool:
    """Send a Slack notification. Returns True if sent, False if skipped."""
    try:
        from slack_sdk.web.async_client import AsyncWebClient

        bot_token = await get_bot_token(db, org_id)
        if not bot_token:
            return False

        client = AsyncWebClient(token=bot_token)

        if channel_type == "dm" and user_id:
            slack_user_id = await get_slack_user_id(db, user_id)
            if not slack_user_id:
                return False
            # Open DM channel
            dm = await client.conversations_open(users=[slack_user_id])
            channel = dm["channel"]["id"]
        else:
            channel = await get_channel_id(db, channel_type, org_id, project_id)
            if not channel:
                return False

        await client.chat_postMessage(channel=channel, text=text, blocks=blocks)
        return True

    except Exception as e:
        logger.warning(f"Slack notification failed: {e}")
        return False
```

- [ ] **Step 2: Create `formatters.py`**

Block Kit message builders for each notification type:

```python
def format_pr_notification(pr_data: dict, action: str) -> list[dict]:
    emoji = {"opened": "🔀", "closed": "❌", "merged": "✅"}.get(action, "📌")
    title = pr_data.get("title", "")
    number = pr_data.get("number", "")
    author = pr_data.get("user", {}).get("login", "unknown")

    return [
        {"type": "section", "text": {
            "type": "mrkdwn",
            "text": f"{emoji} *PR #{number}* {action} by {author}\n{title}"
        }}
    ]


def format_ai_review_notification(summary: str, pr_number: int, score: int | None) -> list[dict]:
    score_text = f" ({score}/10)" if score else ""
    return [
        {"type": "section", "text": {
            "type": "mrkdwn",
            "text": f"🤖 *AI 코드리뷰 완료*: PR #{pr_number}{score_text}\n{summary}"
        }}
    ]


def format_deadline_reminder(task_title: str, days: int, is_overdue: bool) -> list[dict]:
    if is_overdue:
        return [{"type": "section", "text": {
            "type": "mrkdwn",
            "text": f"🚨 *'{task_title}'* 마감 {days}일 초과"
        }}]
    return [{"type": "section", "text": {
        "type": "mrkdwn",
        "text": f"⏰ *'{task_title}'* 내일 마감입니다"
    }}]


def format_briefing_notification(org_summary: dict, week_label: str) -> list[dict]:
    return [
        {"type": "header", "text": {"type": "plain_text", "text": f"📋 주간 브리핑 — {week_label}"}},
        {"type": "section", "text": {
            "type": "mrkdwn",
            "text": org_summary.get("summary", "브리핑이 생성되었습니다.")
        }},
        {"type": "section", "text": {
            "type": "mrkdwn",
            "text": "대시보드에서 상세 내용을 확인하세요."
        }},
    ]


def format_project_status(name: str, progress: float, done: int, total: int, in_progress: int, open_prs: int) -> list[dict]:
    return [
        {"type": "header", "text": {"type": "plain_text", "text": f"📊 {name} 프로젝트 현황"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*진척도:* {progress:.0f}%"},
            {"type": "mrkdwn", "text": f"*완료:* {done}/{total}"},
            {"type": "mrkdwn", "text": f"*진행 중:* {in_progress}"},
            {"type": "mrkdwn", "text": f"*오픈 PR:* {open_prs}"},
        ]},
    ]


def format_my_tasks(tasks: list[dict]) -> list[dict]:
    if not tasks:
        return [{"type": "section", "text": {"type": "mrkdwn", "text": "✨ 할당된 태스크가 없습니다!"}}]
    lines = []
    for t in tasks[:10]:
        status_emoji = {"todo": "⬜", "in_progress": "🔵", "review": "🟡", "done": "✅"}.get(t.get("status", ""), "⬜")
        due = f" (마감: {t['due_date']})" if t.get("due_date") else ""
        lines.append(f"{status_emoji} {t['title']}{due}")
    return [{"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}]


def format_error_message(error: str) -> list[dict]:
    return [{"type": "section", "text": {
        "type": "mrkdwn",
        "text": f"죄송합니다. {error}\n\n다음과 같은 작업을 도와드릴 수 있어요:\n• 프로젝트 진행상황 조회\n• 내 태스크 확인\n• PR 코드리뷰 요청\n• 주간 브리핑 조회\n• 프로젝트 문제점 확인\n• AI 분석 실행"
    }}]
```

- [ ] **Step 3: Commit**
```bash
git commit -m "feat: implement Slack notification service and message formatters"
```

---

## Task 4: Slack Bot — Claude tool_use Integration

**Files:**
- Create: `backend/app/services/slack/tools.py`
- Create: `backend/app/services/slack/bot.py`

- [ ] **Step 1: Create `tools.py`**

Claude API tool definitions and executor:

```python
import uuid

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.project import Project
from app.models.pull_request import PullRequest

SLACK_TOOLS = [
    {
        "name": "get_project_status",
        "description": "프로젝트 진행상황 조회 (진척도, 태스크 현황, PR 현황)",
        "input_schema": {
            "type": "object",
            "properties": {"project_name": {"type": "string", "description": "프로젝트 이름"}},
            "required": ["project_name"]
        }
    },
    {
        "name": "get_my_tasks",
        "description": "나에게 할당된 태스크 목록 조회",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "request_code_review",
        "description": "PR에 대한 AI 코드리뷰 요청",
        "input_schema": {
            "type": "object",
            "properties": {
                "pr_number": {"type": "integer"},
                "project_name": {"type": "string"}
            },
            "required": ["pr_number"]
        }
    },
    {
        "name": "get_latest_briefing",
        "description": "최신 주간 브리핑 조회",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_project_issues",
        "description": "프로젝트 문제점 조회 (지연 태스크, 오래된 PR 등)",
        "input_schema": {
            "type": "object",
            "properties": {"project_name": {"type": "string"}},
            "required": ["project_name"]
        }
    },
    {
        "name": "run_project_analysis",
        "description": "프로젝트 AI 분석 실행",
        "input_schema": {
            "type": "object",
            "properties": {"project_name": {"type": "string"}},
            "required": ["project_name"]
        }
    },
]


async def parse_intent(user_message: str) -> dict:
    """Use Claude API tool_use to parse user intent from natural language."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model="claude-haiku-4-5",  # Fast + cheap for intent parsing
        max_tokens=1024,
        system="You are a PM Agent assistant. Parse the user's request and call the appropriate tool. If the user's intent is unclear, respond with text asking for clarification.",
        tools=SLACK_TOOLS,
        tool_choice={"type": "auto"},
        messages=[{"role": "user", "content": user_message}],
    )

    # Extract tool call if present
    for block in response.content:
        if block.type == "tool_use":
            return {"tool": block.name, "input": block.input, "text": None}
        elif block.type == "text":
            return {"tool": None, "input": None, "text": block.text}

    return {"tool": None, "input": None, "text": "요청을 이해하지 못했습니다."}


async def resolve_project(db: AsyncSession, project_name: str, org_id: uuid.UUID) -> Project | None:
    """Fuzzy match project name within an organization."""
    result = await db.execute(
        select(Project).where(
            Project.org_id == org_id,
            Project.name.ilike(f"%{project_name}%")
        )
    )
    projects = list(result.scalars().all())
    if len(projects) == 1:
        return projects[0]
    return None  # Ambiguous or not found


async def execute_tool(db: AsyncSession, tool_name: str, tool_input: dict,
                       user_id: uuid.UUID, org_id: uuid.UUID) -> dict:
    """Execute a parsed tool and return the result data."""
    from app.services.dashboard_service import get_task_distribution, get_my_tasks, get_project_issues
    from app.models.pull_request import PullRequest, PRState

    if tool_name == "get_project_status":
        project = await resolve_project(db, tool_input["project_name"], org_id)
        if not project:
            return {"error": f"'{tool_input['project_name']}' 프로젝트를 찾을 수 없습니다."}
        dist = await get_task_distribution(db, project.id)
        prs = await db.execute(
            select(PullRequest).where(PullRequest.project_id == project.id, PullRequest.state == PRState.open)
        )
        open_prs = len(list(prs.scalars().all()))
        return {"type": "project_status", "name": project.name, **dist, "open_prs": open_prs}

    elif tool_name == "get_my_tasks":
        result = await get_my_tasks(db, user_id)
        tasks = [{"title": t.title, "status": t.status.value, "due_date": str(t.due_date) if t.due_date else None}
                 for t in result["data"]]
        return {"type": "my_tasks", "tasks": tasks}

    elif tool_name == "request_code_review":
        project_name = tool_input.get("project_name")
        if project_name:
            project = await resolve_project(db, project_name, org_id)
        else:
            project = None  # Will need channel-based resolution
        if not project:
            return {"error": "프로젝트를 특정할 수 없습니다. 프로젝트 이름을 함께 말씀해주세요."}
        # Create AI job
        from app.models.ai_job_queue import AIJobQueue, JobType, JobTrigger
        pr_result = await db.execute(
            select(PullRequest).where(
                PullRequest.project_id == project.id,
                PullRequest.number == tool_input["pr_number"]
            )
        )
        pr = pr_result.scalar_one_or_none()
        if not pr:
            return {"error": f"PR #{tool_input['pr_number']}를 찾을 수 없습니다."}
        job = AIJobQueue(
            project_id=project.id,
            job_type=JobType.code_review,
            trigger=JobTrigger.manual,
            payload={"pr_number": pr.number, "base": pr.base_ref or "main", "head": pr.head_ref or "main"},
        )
        db.add(job)
        await db.flush()
        import asyncio
        from app.services.ai.worker import process_ai_job
        asyncio.create_task(process_ai_job(job.id))
        await db.commit()
        return {"type": "review_requested", "pr_number": tool_input["pr_number"]}

    elif tool_name == "get_latest_briefing":
        from app.models.weekly_briefing import WeeklyBriefing
        result = await db.execute(
            select(WeeklyBriefing).where(WeeklyBriefing.org_id == org_id)
            .order_by(WeeklyBriefing.week_start.desc()).limit(1)
        )
        briefing = result.scalar_one_or_none()
        if not briefing:
            return {"error": "아직 생성된 브리핑이 없습니다."}
        return {"type": "briefing", "week_start": str(briefing.week_start), "org_summary": briefing.org_summary, "project_briefings": briefing.project_briefings}

    elif tool_name == "get_project_issues":
        project = await resolve_project(db, tool_input["project_name"], org_id)
        if not project:
            return {"error": f"'{tool_input['project_name']}' 프로젝트를 찾을 수 없습니다."}
        issues = await get_project_issues(db, project.id)
        return {"type": "project_issues", "name": project.name, **issues}

    elif tool_name == "run_project_analysis":
        project = await resolve_project(db, tool_input["project_name"], org_id)
        if not project:
            return {"error": f"'{tool_input['project_name']}' 프로젝트를 찾을 수 없습니다."}
        from app.models.ai_job_queue import AIJobQueue, JobType, JobTrigger
        job = AIJobQueue(
            project_id=project.id, job_type=JobType.analysis,
            trigger=JobTrigger.manual, payload={},
        )
        db.add(job)
        await db.flush()
        import asyncio
        from app.services.ai.worker import process_ai_job
        asyncio.create_task(process_ai_job(job.id))
        await db.commit()
        return {"type": "analysis_requested", "project_name": project.name}

    return {"error": "지원하지 않는 명령입니다."}
```

- [ ] **Step 2: Create `bot.py`**

Mention handler that ties together parsing and execution:

```python
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.slack.tools import parse_intent, execute_tool
from app.services.slack.formatters import (
    format_project_status, format_my_tasks, format_error_message,
)
from app.services.slack.notifications import send_slack_notification
from app.models.slack import SlackUserMapping, SlackChannelMapping
from sqlalchemy import select


async def resolve_user_from_slack(db: AsyncSession, slack_user_id: str) -> uuid.UUID | None:
    result = await db.execute(
        select(SlackUserMapping).where(SlackUserMapping.slack_user_id == slack_user_id)
    )
    mapping = result.scalar_one_or_none()
    return mapping.user_id if mapping else None


async def resolve_org_from_channel(db: AsyncSession, slack_channel_id: str) -> uuid.UUID | None:
    """Try to find org_id from channel mapping or workspace."""
    from app.models.slack import SlackWorkspace
    # Check project channel mapping
    result = await db.execute(
        select(SlackChannelMapping).where(SlackChannelMapping.slack_channel_id == slack_channel_id)
    )
    mapping = result.scalar_one_or_none()
    if mapping:
        from app.models.project import Project
        project = await db.get(Project, mapping.project_id)
        if project:
            return project.org_id
    # Check org channel
    result = await db.execute(
        select(SlackWorkspace).where(SlackWorkspace.slack_org_channel_id == slack_channel_id)
    )
    workspace = result.scalar_one_or_none()
    return workspace.org_id if workspace else None


async def handle_mention(db: AsyncSession, slack_event: dict, bot_token: str) -> None:
    """Handle an @PM Agent mention event."""
    from slack_sdk.web.async_client import AsyncWebClient

    text = slack_event.get("text", "")
    slack_user_id = slack_event.get("user", "")
    channel_id = slack_event.get("channel", "")

    # Remove bot mention from text
    # Slack mentions look like <@BOTID> so strip those
    import re
    clean_text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

    if not clean_text:
        clean_text = "도움말"

    # Resolve user and org
    user_id = await resolve_user_from_slack(db, slack_user_id)
    org_id = await resolve_org_from_channel(db, channel_id)

    if not org_id:
        client = AsyncWebClient(token=bot_token)
        await client.chat_postMessage(
            channel=channel_id,
            text="이 채널은 PM Agent에 연결되어 있지 않습니다.",
            blocks=format_error_message("이 채널은 PM Agent에 연결되어 있지 않습니다.")
        )
        return

    # Parse intent with Claude
    intent = await parse_intent(clean_text)

    client = AsyncWebClient(token=bot_token)

    if intent["tool"] is None:
        # Claude responded with text (clarification or help)
        await client.chat_postMessage(
            channel=channel_id,
            text=intent["text"] or "요청을 이해하지 못했습니다.",
        )
        return

    # Execute the tool
    result = await execute_tool(
        db, intent["tool"], intent["input"],
        user_id=user_id or uuid.uuid4(),  # fallback for unmapped users
        org_id=org_id,
    )

    # Format response
    if "error" in result:
        blocks = format_error_message(result["error"])
        text = result["error"]
    elif result["type"] == "project_status":
        blocks = format_project_status(
            result["name"], result["progress"], result["done"],
            result["total"], result["in_progress"], result["open_prs"]
        )
        text = f"{result['name']} 프로젝트 현황"
    elif result["type"] == "my_tasks":
        blocks = format_my_tasks(result["tasks"])
        text = "내 태스크 목록"
    elif result["type"] == "review_requested":
        blocks = [{"type": "section", "text": {"type": "mrkdwn",
            "text": f"✅ PR #{result['pr_number']}에 AI 코드리뷰를 요청했습니다.\n결과는 GitHub PR과 대시보드에서 확인하실 수 있습니다."}}]
        text = f"PR #{result['pr_number']} 리뷰 요청됨"
    elif result["type"] == "analysis_requested":
        blocks = [{"type": "section", "text": {"type": "mrkdwn",
            "text": f"✅ *{result['project_name']}* 프로젝트 AI 분석을 요청했습니다.\n완료되면 알려드리겠습니다."}}]
        text = f"{result['project_name']} 분석 요청됨"
    elif result["type"] == "briefing":
        blocks = format_briefing_notification(result["org_summary"], result["week_start"])
        text = "주간 브리핑"
    elif result["type"] == "project_issues":
        items = result.get("items", [])
        if not items:
            blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": f"✨ *{result['name']}*에 발견된 문제가 없습니다!"}}]
        else:
            lines = [f"⚠️ *{result['name']}* 프로젝트 문제점 ({len(items)}건)"]
            for item in items[:10]:
                emoji = {"overdue_task": "🚨", "stale_pr": "📌", "pending_review": "👀", "unassigned_task": "❓"}.get(item["type"], "•")
                lines.append(f"{emoji} {item['title']}")
            blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}]
        text = f"{result['name']} 문제점"
    else:
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "작업이 완료되었습니다."}}]
        text = "완료"

    await client.chat_postMessage(channel=channel_id, text=text, blocks=blocks)
```

- [ ] **Step 3: Commit**
```bash
git commit -m "feat: implement Slack bot with Claude tool_use intent parsing"
```

---

## Task 5: Slack Pydantic Schemas + Router

**Files:**
- Create: `backend/app/schemas/slack.py`
- Create: `backend/app/routers/slack.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create `backend/app/schemas/slack.py`**

```python
import uuid
from datetime import datetime
from pydantic import BaseModel


class SlackStatusResponse(BaseModel):
    connected: bool
    slack_team_id: str | None = None
    org_channel_id: str | None = None

class ChannelMappingRequest(BaseModel):
    slack_channel_id: str

class OrgChannelRequest(BaseModel):
    slack_channel_id: str

class UserMappingRequest(BaseModel):
    user_id: uuid.UUID
    slack_user_id: str

class UserMappingResponse(BaseModel):
    user_id: uuid.UUID
    slack_user_id: str
    created_at: datetime
    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create `backend/app/routers/slack.py`**

All Slack endpoints:

```python
import hashlib
import hmac
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_org_role
from app.models.user import User
from app.models.organization import OrgRole
from app.models.slack import SlackWorkspace, SlackChannelMapping, SlackUserMapping
from app.schemas.slack import (
    SlackStatusResponse, ChannelMappingRequest, OrgChannelRequest,
    UserMappingRequest, UserMappingResponse,
)

router = APIRouter(tags=["slack"])


# --- Slack Event API ---

async def verify_slack_signature(request: Request) -> bytes:
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if abs(time.time() - float(timestamp or 0)) > 300:
        raise HTTPException(status_code=401, detail="Request too old")

    sig_basestring = f"v0:{timestamp}:{body.decode()}"
    expected = "v0=" + hmac.new(
        settings.slack_signing_secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid signature")
    return body


@router.post("/api/slack/events")
async def slack_events(request: Request, db: AsyncSession = Depends(get_db)):
    body = await verify_slack_signature(request)
    import json
    payload = json.loads(body)

    # URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload["challenge"]}

    # Event callback
    if payload.get("type") == "event_callback":
        event = payload.get("event", {})
        if event.get("type") == "app_mention":
            # Get bot token for this team
            team_id = payload.get("team_id")
            result = await db.execute(
                select(SlackWorkspace).where(SlackWorkspace.slack_team_id == team_id)
            )
            workspace = result.scalar_one_or_none()
            if workspace:
                import asyncio
                from app.services.slack.bot import handle_mention
                asyncio.create_task(handle_mention(db, event, workspace.slack_bot_token))

    return {"ok": True}


@router.post("/api/slack/interactions")
async def slack_interactions(request: Request):
    await verify_slack_signature(request)
    # Placeholder for future button/interaction handling
    return {"ok": True}


# --- Slack OAuth ---

@router.get("/api/orgs/{org_id}/slack/auth")
async def slack_auth(org_id: uuid.UUID, user: User = Depends(get_current_user)):
    scope = "chat:write,app_mentions:read,users:read,channels:read"
    redirect_uri = f"{settings.frontend_url}/api/slack/oauth/callback"
    url = f"https://slack.com/oauth/v2/authorize?client_id={settings.slack_client_id}&scope={scope}&redirect_uri={redirect_uri}&state={org_id}"
    return RedirectResponse(url=url)


@router.get("/api/slack/oauth/callback")
async def slack_oauth_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    org_id = uuid.UUID(state)

    async with httpx.AsyncClient() as client:
        resp = await client.post("https://slack.com/api/oauth.v2.access", data={
            "client_id": settings.slack_client_id,
            "client_secret": settings.slack_client_secret,
            "code": code,
        })
        data = resp.json()

    if not data.get("ok"):
        raise HTTPException(status_code=400, detail="Slack OAuth failed")

    bot_token = data["access_token"]
    team_id = data["team"]["id"]

    # Upsert workspace
    result = await db.execute(select(SlackWorkspace).where(SlackWorkspace.org_id == org_id))
    workspace = result.scalar_one_or_none()
    if workspace:
        workspace.slack_bot_token = bot_token
        workspace.slack_team_id = team_id
    else:
        workspace = SlackWorkspace(org_id=org_id, slack_team_id=team_id, slack_bot_token=bot_token)
        db.add(workspace)
    await db.commit()

    return RedirectResponse(url=f"{settings.frontend_url}/org/{state}/settings?slack=connected")


# --- Slack Settings ---

@router.get("/api/orgs/{org_id}/slack/status", response_model=SlackStatusResponse)
async def slack_status(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member)),
):
    result = await db.execute(select(SlackWorkspace).where(SlackWorkspace.org_id == org_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        return SlackStatusResponse(connected=False)
    return SlackStatusResponse(
        connected=True, slack_team_id=workspace.slack_team_id,
        org_channel_id=workspace.slack_org_channel_id,
    )


@router.delete("/api/orgs/{org_id}/slack/disconnect", status_code=204)
async def slack_disconnect(
    org_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    _=Depends(require_org_role(OrgRole.owner)),
):
    await db.execute(delete(SlackWorkspace).where(SlackWorkspace.org_id == org_id))
    await db.commit()


@router.patch("/api/orgs/{org_id}/slack/org-channel")
async def set_org_channel(
    org_id: uuid.UUID, body: OrgChannelRequest, db: AsyncSession = Depends(get_db),
    _=Depends(require_org_role(OrgRole.owner, OrgRole.admin)),
):
    result = await db.execute(select(SlackWorkspace).where(SlackWorkspace.org_id == org_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Slack not connected")
    workspace.slack_org_channel_id = body.slack_channel_id
    await db.commit()
    return {"ok": True}


@router.post("/api/projects/{project_id}/slack/channel", status_code=201)
async def set_project_channel(
    project_id: uuid.UUID, body: ChannelMappingRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(SlackChannelMapping).where(SlackChannelMapping.project_id == project_id)
    )
    mapping = existing.scalar_one_or_none()
    if mapping:
        mapping.slack_channel_id = body.slack_channel_id
    else:
        db.add(SlackChannelMapping(project_id=project_id, slack_channel_id=body.slack_channel_id))
    await db.commit()
    return {"ok": True}


@router.delete("/api/projects/{project_id}/slack/channel", status_code=204)
async def remove_project_channel(
    project_id: uuid.UUID, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(SlackChannelMapping).where(SlackChannelMapping.project_id == project_id))
    await db.commit()


@router.get("/api/orgs/{org_id}/slack/user-mappings", response_model=list[UserMappingResponse])
async def list_user_mappings(
    org_id: uuid.UUID, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member)),
):
    result = await db.execute(select(SlackUserMapping))
    return list(result.scalars().all())


@router.post("/api/orgs/{org_id}/slack/user-mappings", status_code=201)
async def add_user_mapping(
    org_id: uuid.UUID, body: UserMappingRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_org_role(OrgRole.owner, OrgRole.admin)),
):
    existing = await db.execute(
        select(SlackUserMapping).where(SlackUserMapping.user_id == body.user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already mapped")
    db.add(SlackUserMapping(user_id=body.user_id, slack_user_id=body.slack_user_id))
    await db.commit()
    return {"ok": True}
```

- [ ] **Step 3: Register router in main.py**

```python
from app.routers import slack
app.include_router(slack.router)
```

- [ ] **Step 4: Write tests**

Create `backend/tests/test_slack_router.py`:
- test_slack_status_not_connected → 200, connected=false
- test_slack_events_url_verification → returns challenge
- test_slack_events_invalid_signature → 401
- test_set_project_channel → 201
- test_add_user_mapping → 201

- [ ] **Step 5: Run all tests, commit**
```bash
git commit -m "feat: implement Slack router with OAuth, events, and settings endpoints"
```

---

## Task 6: Notification Hooks in Existing Services

**Files:**
- Modify: `backend/app/services/github_service.py`
- Modify: `backend/app/services/ai/worker.py`

- [ ] **Step 1: Add Slack notifications to github_service.py**

In `handle_pull_request`, after the existing commit, add:
```python
# Slack notification (best-effort)
try:
    from app.services.slack.notifications import send_slack_notification
    from app.services.slack.formatters import format_pr_notification
    if payload["action"] in ("opened", "closed") or (payload["action"] == "closed" and pr_data.get("merged")):
        action_label = "merged" if pr_data.get("merged") else payload["action"]
        await send_slack_notification(
            db, org_id=project.org_id, channel_type="project", project_id=project.id,
            blocks=format_pr_notification(pr_data, action_label),
            text=f"PR #{pr_data['number']} {action_label}: {pr_data['title']}",
        )
except Exception:
    pass
```

In `handle_pull_request_review`, add similar notification.

- [ ] **Step 2: Add Slack notifications to ai/worker.py**

After code_review completion:
```python
try:
    from app.services.slack.notifications import send_slack_notification
    from app.services.slack.formatters import format_ai_review_notification
    score = result.get("score")
    await send_slack_notification(
        db, org_id=project.org_id, channel_type="project", project_id=project.id,
        blocks=format_ai_review_notification(review.summary or "", payload["pr_number"], score),
        text=f"AI 리뷰 완료: PR #{payload['pr_number']}",
    )
except Exception:
    pass
```

After briefing completion:
```python
try:
    from app.services.slack.notifications import send_slack_notification
    from app.services.slack.formatters import format_briefing_notification
    await send_slack_notification(
        db, org_id=org.id, channel_type="org",
        blocks=format_briefing_notification(briefing.org_summary, str(briefing.week_start)),
        text="주간 브리핑이 생성되었습니다.",
    )
except Exception:
    pass
```

- [ ] **Step 3: Commit**
```bash
git commit -m "feat: add Slack notification hooks to GitHub and AI services"
```

---

## Task 7: Deadline Reminder Scheduler

**Files:**
- Modify: `backend/app/scheduler.py`

- [ ] **Step 1: Add deadline reminder job**

Add to `scheduler.py`:

```python
from datetime import date, timedelta
from sqlalchemy import select

from app.models.task import Task, TaskStatus
from app.models.project import Project
from app.services.slack.notifications import send_slack_notification
from app.services.slack.formatters import format_deadline_reminder


async def check_deadline_reminders():
    """Hourly job: check for deadline reminders and send Slack notifications."""
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
            # DM to assignee
            await send_slack_notification(
                db, org_id=project.org_id, channel_type="dm",
                user_id=task.assignee_id,
                blocks=format_deadline_reminder(task.title, days, True),
                text=f"🚨 '{task.title}' 마감 {days}일 초과",
            )
            # Project channel
            await send_slack_notification(
                db, org_id=project.org_id, channel_type="project",
                project_id=project.id,
                blocks=format_deadline_reminder(task.title, days, True),
                text=f"🚨 '{task.title}' 마감 {days}일 초과",
            )


# Register: every hour at :00
scheduler.add_job(check_deadline_reminders, CronTrigger(minute=0))
```

NOTE: Import guard — if slack_sdk is not installed, wrap in try/except.

- [ ] **Step 2: Run all tests, commit**
```bash
git commit -m "feat: add deadline reminder scheduler with Slack notifications"
```

---

## Task 8: Frontend — Slack Hooks + Settings UI

**Files:**
- Create: `frontend/src/hooks/use-slack.ts`
- Create: `frontend/src/components/slack/slack-connect.tsx`
- Create: `frontend/src/components/slack/channel-mapping.tsx`
- Create: `frontend/src/components/slack/user-mapping.tsx`
- Modify: `frontend/src/app/(dashboard)/org/[slug]/settings/page.tsx`

- [ ] **Step 1: Create `use-slack.ts`**

```typescript
"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export function useSlackStatus(orgId: string) {
  return useQuery({
    queryKey: ["slack-status", orgId],
    queryFn: () => api.get(`/api/orgs/${orgId}/slack/status`).then(r => r.data),
    enabled: !!orgId,
  });
}

export function useSlackDisconnect(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.delete(`/api/orgs/${orgId}/slack/disconnect`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["slack-status", orgId] }),
  });
}

export function useSetOrgChannel(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (channelId: string) => api.patch(`/api/orgs/${orgId}/slack/org-channel`, { slack_channel_id: channelId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["slack-status", orgId] }),
  });
}

export function useSetProjectChannel(projectId: string) {
  return useMutation({
    mutationFn: (channelId: string) => api.post(`/api/projects/${projectId}/slack/channel`, { slack_channel_id: channelId }),
  });
}

export function useSlackUserMappings(orgId: string) {
  return useQuery({
    queryKey: ["slack-user-mappings", orgId],
    queryFn: () => api.get(`/api/orgs/${orgId}/slack/user-mappings`).then(r => r.data),
    enabled: !!orgId,
  });
}

export function useAddUserMapping(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { user_id: string; slack_user_id: string }) =>
      api.post(`/api/orgs/${orgId}/slack/user-mappings`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["slack-user-mappings", orgId] }),
  });
}
```

- [ ] **Step 2: Create Slack components**

`slack-connect.tsx` — Shows connection status, connect/disconnect buttons, org channel input.
`channel-mapping.tsx` — For project settings: channel ID input + connect button.
`user-mapping.tsx` — Table of user ↔ Slack mappings with add form.

- [ ] **Step 3: Modify settings page**

Add "Slack 연동" section to the org settings page after the existing member management section.

- [ ] **Step 4: Build check**
```bash
cd /Users/kimjihun/Desktop/pmai/frontend && npm run build
```

- [ ] **Step 5: Commit**
```bash
git commit -m "feat: implement Slack settings UI in dashboard"
```

---

## Task 9: End-to-End Verification

- [ ] **Step 1: Run all backend tests**
```bash
cd /Users/kimjihun/Desktop/pmai/backend && .venv/bin/python -m pytest -v
```

- [ ] **Step 2: Build frontend**
```bash
cd /Users/kimjihun/Desktop/pmai/frontend && npm run build
```

- [ ] **Step 3: Final commit**
```bash
git commit -m "feat: complete Phase 3 — Slack Bot + Automation Engine"
```
