# PM Agent Phase 2: AI Agent Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an AI engine using Claude Agent SDK that performs code review, project analysis, test scenario generation, and weekly briefings — all async via a job queue.

**Architecture:** FastAPI backend gains an AI service layer (Agent Executor + Background Worker + APScheduler). Agent SDK runs subagents (code-reviewer, project-analyst, test-generator) against cloned repos. Results stored in DB, posted to GitHub as PR comments, and displayed in the frontend.

**Tech Stack:** Claude Agent SDK, APScheduler 3.x, existing FastAPI + SQLAlchemy + Next.js stack.

**Spec:** `docs/superpowers/specs/2026-03-24-pm-agent-phase2-design.md`

---

## File Structure

### Backend (new/modified)

```
backend/
├── app/
│   ├── config.py                          # MODIFY: add AI config fields
│   ├── main.py                            # MODIFY: add lifespan, register new routers
│   ├── scheduler.py                       # CREATE: APScheduler setup
│   ├── models/
│   │   ├── __init__.py                    # MODIFY: re-export new models
│   │   ├── pull_request.py                # MODIFY: add base_ref, head_ref
│   │   ├── ai_review.py                   # CREATE: AIReview model
│   │   ├── weekly_briefing.py             # CREATE: WeeklyBriefing model
│   │   └── ai_job_queue.py                # CREATE: AIJobQueue model
│   ├── schemas/
│   │   └── ai.py                          # CREATE: AI Pydantic schemas
│   ├── services/
│   │   ├── ai/
│   │   │   ├── __init__.py                # CREATE
│   │   │   ├── prompts.py                 # CREATE: subagent prompts
│   │   │   ├── schemas.py                 # CREATE: AI output JSON schemas
│   │   │   ├── executor.py                # CREATE: Agent Executor (repo mgmt + SDK calls)
│   │   │   └── worker.py                  # CREATE: Background job worker
│   │   └── github_service.py              # MODIFY: add PR auto-review trigger + comment posting
│   ├── routers/
│   │   ├── ai.py                          # CREATE: AI operation endpoints
│   │   └── briefings.py                   # CREATE: Briefing endpoints
│   └── tests/
│       ├── test_ai_models.py              # CREATE
│       ├── test_ai_worker.py              # CREATE
│       ├── test_ai_router.py              # CREATE
│       └── test_briefings_router.py       # CREATE
├── alembic/versions/                      # New migration file
├── requirements.txt                       # MODIFY: add new deps
└── .env.example                           # MODIFY: add AI config vars
```

### Frontend (new/modified)

```
frontend/src/
├── hooks/
│   └── use-ai.ts                                        # CREATE
├── components/
│   ├── ai/
│   │   ├── ai-review-list.tsx                            # CREATE
│   │   ├── ai-review-detail.tsx                          # CREATE
│   │   ├── review-badge.tsx                              # CREATE
│   │   └── briefing-card.tsx                             # CREATE
│   └── project/
│       ├── ai-tab.tsx                                    # CREATE
│       └── github-tab.tsx                                # MODIFY: add review badge
├── app/(dashboard)/
│   └── org/[slug]/
│       ├── page.tsx                                      # MODIFY: add briefing section
│       ├── briefings/page.tsx                            # CREATE
│       └── project/[projectId]/page.tsx                  # MODIFY: add AI tab
```

---

## Task 1: Dependencies + Configuration

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Modify: `.env.example`

- [ ] **Step 1: Update `backend/requirements.txt`**

Add to existing requirements:
```
claude-agent-sdk
apscheduler>=3.10,<4.0
```

- [ ] **Step 2: Install new dependencies**

Run: `cd backend && pip install claude-agent-sdk "apscheduler>=3.10,<4.0"`

- [ ] **Step 3: Update `backend/app/config.py`**

Add these fields to the `Settings` class:

```python
# AI Engine
anthropic_api_key: str = ""
ai_repo_base_path: str = "/tmp/pmai/repos"
ai_model: str = "claude-opus-4-6"
ai_max_turns: int = 20
```

- [ ] **Step 4: Update `.env.example`**

Add:
```env
# AI Engine (Phase 2)
ANTHROPIC_API_KEY=
AI_REPO_BASE_PATH=/tmp/pmai/repos
AI_MODEL=claude-opus-4-6
```

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/config.py .env.example
git commit -m "feat: add Phase 2 AI dependencies and configuration"
```

---

## Task 2: Database Models + Migration

**Files:**
- Create: `backend/app/models/ai_review.py`
- Create: `backend/app/models/weekly_briefing.py`
- Create: `backend/app/models/ai_job_queue.py`
- Modify: `backend/app/models/pull_request.py` (add base_ref, head_ref)
- Modify: `backend/app/models/__init__.py` (re-export)
- Alembic migration

- [ ] **Step 1: Create `backend/app/models/ai_review.py`**

```python
import uuid
from datetime import datetime
import enum

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func

from app.database import Base


class AIReviewType(str, enum.Enum):
    code_review = "code_review"
    analysis = "analysis"
    test_scenario = "test_scenario"


class AIReviewStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class AIReview(Base):
    __tablename__ = "ai_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    pull_request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pull_requests.id"), nullable=True)
    type: Mapped[AIReviewType] = mapped_column(Enum(AIReviewType))
    status: Mapped[AIReviewStatus] = mapped_column(Enum(AIReviewStatus), default=AIReviewStatus.pending)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)
    suggestions: Mapped[dict] = mapped_column(JSONB, default=list)
    github_comment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 2: Create `backend/app/models/weekly_briefing.py`**

```python
import uuid
from datetime import datetime, date
import enum

from sqlalchemy import Date, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func

from app.database import Base


class BriefingStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class WeeklyBriefing(Base):
    __tablename__ = "weekly_briefings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    week_start: Mapped[date] = mapped_column(Date)
    org_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    project_briefings: Mapped[dict] = mapped_column(JSONB, default=list)
    status: Mapped[BriefingStatus] = mapped_column(Enum(BriefingStatus), default=BriefingStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 3: Create `backend/app/models/ai_job_queue.py`**

```python
import uuid
from datetime import datetime
import enum

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func

from app.database import Base


class JobType(str, enum.Enum):
    code_review = "code_review"
    analysis = "analysis"
    briefing = "briefing"
    test_scenario = "test_scenario"


class JobTrigger(str, enum.Enum):
    webhook = "webhook"
    schedule = "schedule"
    manual = "manual"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class AIJobQueue(Base):
    __tablename__ = "ai_job_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    job_type: Mapped[JobType] = mapped_column(Enum(JobType))
    trigger: Mapped[JobTrigger] = mapped_column(Enum(JobTrigger))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued)
    ai_review_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_reviews.id"), nullable=True)
    briefing_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("weekly_briefings.id"), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: Add `base_ref` and `head_ref` to PullRequest model**

In `backend/app/models/pull_request.py`, add:
```python
base_ref: Mapped[str | None] = mapped_column(String, nullable=True)
head_ref: Mapped[str | None] = mapped_column(String, nullable=True)
```

- [ ] **Step 5: Update `backend/app/models/__init__.py`**

Add re-exports for all new models and enums:
```python
from app.models.ai_review import AIReview, AIReviewType, AIReviewStatus
from app.models.weekly_briefing import WeeklyBriefing, BriefingStatus
from app.models.ai_job_queue import AIJobQueue, JobType, JobTrigger, JobStatus
```

Also add them to `__all__`.

- [ ] **Step 6: Generate and apply Alembic migration**

```bash
cd backend && alembic revision --autogenerate -m "add AI models and PR branch refs"
alembic upgrade head
```

- [ ] **Step 7: Verify tables exist**

Run: `docker compose exec db psql -U pmai -d pmai -c "\dt"`
Expected: `ai_reviews`, `weekly_briefings`, `ai_job_queue` appear alongside existing tables.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/ backend/alembic/
git commit -m "feat: add AI review, weekly briefing, and job queue models"
```

---

## Task 3: AI Prompts + Output Schemas

**Files:**
- Create: `backend/app/services/ai/__init__.py`
- Create: `backend/app/services/ai/prompts.py`
- Create: `backend/app/services/ai/schemas.py`

- [ ] **Step 1: Create `backend/app/services/ai/__init__.py`**

Empty file.

- [ ] **Step 2: Create `backend/app/services/ai/prompts.py`**

```python
CODE_REVIEWER_PROMPT = """You are an expert code reviewer. Review the PR changes for:
1. Security vulnerabilities (injection, auth bypass, data exposure)
2. Performance issues (N+1 queries, unnecessary computation, memory leaks)
3. Code quality (readability, naming, duplication)
4. Maintainability (proper abstractions, test coverage gaps)

For each issue found, provide:
- The exact file path and line number
- A clear description of the issue
- Severity: "critical", "warning", or "info"
- A suggested fix

Output your review as a JSON object with this exact structure:
{
  "summary": "Brief overall assessment",
  "score": <1-10>,
  "file_comments": [{"file": "path", "line": <number>, "comment": "description", "severity": "critical|warning|info"}],
  "overall_issues": [{"type": "security|performance|quality|maintainability", "description": "...", "priority": "high|medium|low"}]
}"""

PROJECT_ANALYST_PROMPT = """You are a project management analyst. Analyze the project's current state by examining:
1. Git history (recent commits, velocity, contributors)
2. Task completion rate and overdue items
3. PR merge rate and review bottlenecks
4. Code health indicators

Provide an honest assessment with actionable recommendations.

Output as JSON:
{
  "progress_assessment": "Overall narrative assessment",
  "progress_score": <0-100>,
  "delays": [{"task": "title", "days_overdue": <number>, "likely_cause": "explanation"}],
  "risks": [{"description": "...", "severity": "high|medium|low", "mitigation": "suggested action"}],
  "recommendations": [{"type": "reassign|reschedule|deprioritize|escalate", "title": "...", "description": "...", "target_task_id": "optional UUID"}]
}"""

TEST_GENERATOR_PROMPT = """You are a test engineering specialist. Generate comprehensive test scenarios for the given code changes.

Cover:
1. Happy path scenarios (expected inputs, normal flow)
2. Edge cases (boundary values, empty inputs, max lengths)
3. Error cases (invalid inputs, network failures, permission errors)

Output as JSON:
{
  "test_scenarios": [{
    "name": "descriptive test name",
    "description": "what this tests and why",
    "category": "happy_path|edge_case|error_case",
    "steps": ["step 1", "step 2"],
    "expected_result": "what should happen",
    "priority": "high|medium|low"
  }]
}"""

WEEKLY_BRIEFING_PROMPT = """You are a project management assistant generating a weekly briefing.
Analyze the project data provided and create a comprehensive summary.

Include:
- What was accomplished this week (completed tasks, merged PRs)
- What's currently in progress
- Any delays or blockers with root cause analysis
- Risk assessment
- Recommendations for the coming week
- Team workload balance analysis

Output as JSON:
{
  "summary": "Overall week narrative",
  "completed_tasks": <count>,
  "merged_prs": <count>,
  "in_progress": ["task titles"],
  "delayed_items": [{"title": "...", "days_overdue": <n>, "cause": "..."}],
  "risk_analysis": "narrative",
  "recommendations": ["actionable items"],
  "workload_per_member": [{"name": "...", "task_count": <n>, "status": "normal|heavy|light"}]
}"""
```

- [ ] **Step 3: Create `backend/app/services/ai/schemas.py`**

```python
CODE_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "score": {"type": "integer", "minimum": 1, "maximum": 10},
        "file_comments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "comment": {"type": "string"},
                    "severity": {"type": "string", "enum": ["critical", "warning", "info"]}
                },
                "required": ["file", "line", "comment", "severity"]
            }
        },
        "overall_issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]}
                },
                "required": ["type", "description", "priority"]
            }
        }
    },
    "required": ["summary", "score", "file_comments", "overall_issues"]
}

PROJECT_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "progress_assessment": {"type": "string"},
        "progress_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "delays": {"type": "array", "items": {"type": "object"}},
        "risks": {"type": "array", "items": {"type": "object"}},
        "recommendations": {"type": "array", "items": {"type": "object"}}
    },
    "required": ["progress_assessment", "progress_score", "delays", "risks", "recommendations"]
}

TEST_SCENARIO_SCHEMA = {
    "type": "object",
    "properties": {
        "test_scenarios": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {"type": "string", "enum": ["happy_path", "edge_case", "error_case"]},
                    "steps": {"type": "array", "items": {"type": "string"}},
                    "expected_result": {"type": "string"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]}
                },
                "required": ["name", "description", "category", "steps", "expected_result", "priority"]
            }
        }
    },
    "required": ["test_scenarios"]
}

BRIEFING_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "completed_tasks": {"type": "integer"},
        "merged_prs": {"type": "integer"},
        "in_progress": {"type": "array", "items": {"type": "string"}},
        "delayed_items": {"type": "array", "items": {"type": "object"}},
        "risk_analysis": {"type": "string"},
        "recommendations": {"type": "array", "items": {"type": "string"}},
        "workload_per_member": {"type": "array", "items": {"type": "object"}}
    },
    "required": ["summary", "completed_tasks", "merged_prs"]
}
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/ai/
git commit -m "feat: add AI subagent prompts and output schemas"
```

---

## Task 4: Agent Executor

**Files:**
- Create: `backend/app/services/ai/executor.py`

- [ ] **Step 1: Create `backend/app/services/ai/executor.py`**

```python
import asyncio
import json
import os
import shutil
import uuid
from pathlib import Path

from app.config import settings
from app.services.github_service import get_installation_token
from app.services.ai.prompts import (
    CODE_REVIEWER_PROMPT, PROJECT_ANALYST_PROMPT,
    TEST_GENERATOR_PROMPT, WEEKLY_BRIEFING_PROMPT,
)

try:
    from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
except ImportError:
    query = None  # Allow tests to run without SDK installed


async def clone_or_update_repo(
    project_id: uuid.UUID, job_id: uuid.UUID,
    repo_url: str, installation_id: int
) -> str:
    """Clone a repo to a job-specific directory. Returns the path."""
    token = await get_installation_token(installation_id)
    # Insert token into URL for auth: https://x-access-token:{token}@github.com/owner/repo.git
    parts = repo_url.rstrip("/").split("//")
    authed_url = f"{parts[0]}//x-access-token:{token}@{parts[1]}.git"

    base_path = Path(settings.ai_repo_base_path) / str(project_id)
    job_path = base_path / str(job_id)

    if job_path.exists():
        shutil.rmtree(job_path)

    os.makedirs(job_path, exist_ok=True)

    proc = await asyncio.create_subprocess_exec(
        "git", "clone", "--depth", "50", authed_url, str(job_path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Git clone failed: {stderr.decode()}")

    return str(job_path)


def cleanup_repo(project_id: uuid.UUID, job_id: uuid.UUID) -> None:
    """Remove the job-specific repo directory."""
    job_path = Path(settings.ai_repo_base_path) / str(project_id) / str(job_id)
    if job_path.exists():
        shutil.rmtree(job_path, ignore_errors=True)


async def run_agent(repo_path: str, system_prompt: str, user_prompt: str) -> dict:
    """Run Claude Agent SDK and return parsed JSON result."""
    if query is None:
        raise RuntimeError("claude-agent-sdk not installed")

    result = None
    async for message in query(
        prompt=user_prompt,
        options=ClaudeAgentOptions(
            cwd=repo_path,
            allowed_tools=["Read", "Grep", "Glob", "Bash"],
            system_prompt=system_prompt,
            model=settings.ai_model,
            max_turns=settings.ai_max_turns,
            permission_mode="bypassPermissions",
        )
    ):
        if isinstance(message, ResultMessage):
            result = message.result

    if result is None:
        raise RuntimeError("Agent returned no result")

    # Try to parse as JSON; agent may wrap in markdown code block
    text = result.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    return json.loads(text)


async def run_code_review(repo_path: str, pr_number: int, base: str, head: str) -> dict:
    prompt = f"""PR #{pr_number}을 리뷰해줘.
base branch: {base}, head branch: {head}

다음 명령어로 변경사항을 확인하고 리뷰해:
git fetch origin {base} {head}
git diff origin/{base}...origin/{head}

변경된 파일을 읽고, 관련 코드도 확인해서 맥락을 파악해."""
    return await run_agent(repo_path, CODE_REVIEWER_PROMPT, prompt)


async def run_project_analysis(repo_path: str, context: str) -> dict:
    prompt = f"""이 프로젝트의 현재 상태를 분석해줘.

프로젝트 컨텍스트:
{context}

다음을 실행해서 추가 정보를 수집해:
- git log --oneline -30 (최근 커밋)
- git shortlog -sn --since="2 weeks ago" (기여도)
- 프로젝트 구조 파악"""
    return await run_agent(repo_path, PROJECT_ANALYST_PROMPT, prompt)


async def run_test_generation(repo_path: str, pr_number: int | None, file_paths: list[str] | None, base: str | None, head: str | None) -> dict:
    if pr_number and base and head:
        prompt = f"""PR #{pr_number}의 변경사항에 대한 테스트 시나리오를 작성해.
git diff origin/{base}...origin/{head} 로 변경사항을 확인하고,
변경된 코드를 읽어서 테스트 시나리오를 생성해."""
    elif file_paths:
        files_str = "\n".join(file_paths)
        prompt = f"""다음 파일들에 대한 테스트 시나리오를 작성해:
{files_str}

각 파일을 읽고 핵심 로직, 엣지 케이스, 에러 케이스를 커버하는 시나리오를 생성해."""
    else:
        raise ValueError("Either pr_number or file_paths must be provided")
    return await run_agent(repo_path, TEST_GENERATOR_PROMPT, prompt)


async def run_weekly_briefing(repo_path: str, context: str) -> dict:
    prompt = f"""이 프로젝트의 주간 브리핑을 생성해줘.

프로젝트 데이터:
{context}

추가로 다음을 확인해:
- git log --oneline --since="1 week ago" (이번 주 커밋)
- git shortlog -sn --since="1 week ago" (이번 주 기여도)"""
    return await run_agent(repo_path, WEEKLY_BRIEFING_PROMPT, prompt)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/ai/executor.py
git commit -m "feat: implement Agent Executor with repo management and SDK calls"
```

---

## Task 5: Background Worker

**Files:**
- Create: `backend/app/services/ai/worker.py`

- [ ] **Step 1: Create `backend/app/services/ai/worker.py`**

```python
import asyncio
import json
import uuid
from datetime import datetime, timezone, date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.ai_job_queue import AIJobQueue, JobType, JobStatus
from app.models.ai_review import AIReview, AIReviewType, AIReviewStatus
from app.models.weekly_briefing import WeeklyBriefing, BriefingStatus
from app.models.project import Project
from app.models.organization import Organization
from app.models.pull_request import PullRequest
from app.models.task import Task, TaskStatus
from app.services.ai.executor import (
    clone_or_update_repo, cleanup_repo,
    run_code_review, run_project_analysis,
    run_test_generation, run_weekly_briefing,
)


async def build_project_context(db: AsyncSession, project_id: uuid.UUID) -> str:
    """Build a text context of project state for the analyst agent."""
    project = await db.get(Project, project_id)
    if not project:
        return ""

    # Get task stats
    tasks_result = await db.execute(select(Task).where(Task.project_id == project_id))
    tasks = list(tasks_result.scalars().all())

    total = len(tasks)
    done = len([t for t in tasks if t.status == TaskStatus.done])
    overdue = [t for t in tasks if t.due_date and t.due_date < date.today() and t.status != TaskStatus.done]

    # Get PR stats
    prs_result = await db.execute(select(PullRequest).where(PullRequest.project_id == project_id))
    prs = list(prs_result.scalars().all())

    context_parts = [
        f"Project: {project.name}",
        f"Status: {project.status.value}",
        f"Tasks: {done}/{total} done",
        f"Overdue tasks: {len(overdue)}",
        f"Open PRs: {len([p for p in prs if p.state.value == 'open'])}",
    ]

    if overdue:
        context_parts.append("Overdue items:")
        for t in overdue[:10]:
            days = (date.today() - t.due_date).days
            context_parts.append(f"  - {t.title} ({days} days overdue)")

    return "\n".join(context_parts)


async def process_ai_job(job_id: uuid.UUID) -> None:
    """Process a single AI job. Called as a background task."""
    async with async_session() as db:
        job = await db.get(AIJobQueue, job_id)
        if not job or job.status not in (JobStatus.queued, JobStatus.running):
            return

        job.status = JobStatus.running
        await db.commit()

        repo_path = None
        try:
            # Get project info for repo access
            project = await db.get(Project, job.project_id) if job.project_id else None

            if job.job_type == JobType.code_review:
                if not project or not project.github_repo_url:
                    raise ValueError("Project has no GitHub repo connected")

                org = await db.get(Organization, project.org_id)
                repo_path = await clone_or_update_repo(
                    project.id, job.id, project.github_repo_url, org.github_installation_id
                )
                payload = job.payload
                result = await run_code_review(
                    repo_path, payload["pr_number"], payload["base"], payload["head"]
                )

                # Find the PR
                pr_result = await db.execute(
                    select(PullRequest).where(
                        PullRequest.project_id == project.id,
                        PullRequest.number == payload["pr_number"],
                    )
                )
                pr = pr_result.scalar_one_or_none()

                review = AIReview(
                    project_id=project.id,
                    pull_request_id=pr.id if pr else None,
                    type=AIReviewType.code_review,
                    status=AIReviewStatus.completed,
                    summary=result.get("summary", ""),
                    detail=result,
                    suggestions=result.get("overall_issues", []),
                    completed_at=datetime.now(timezone.utc),
                )
                db.add(review)
                await db.flush()
                job.ai_review_id = review.id

                # Post GitHub comment (best-effort — don't fail the job if this fails)
                try:
                    from app.services.github_service import post_github_review_comment
                    parts = project.github_repo_url.rstrip("/").split("/")
                    owner, repo_name = parts[-2], parts[-1]
                    comment_id = await post_github_review_comment(
                        org.github_installation_id, owner, repo_name,
                        payload["pr_number"], result,
                    )
                    review.github_comment_id = comment_id
                except Exception:
                    pass  # GitHub comment failure is non-critical

            elif job.job_type == JobType.analysis:
                if not project or not project.github_repo_url:
                    raise ValueError("Project has no GitHub repo connected")

                org = await db.get(Organization, project.org_id)
                repo_path = await clone_or_update_repo(
                    project.id, job.id, project.github_repo_url, org.github_installation_id
                )
                context = await build_project_context(db, project.id)
                result = await run_project_analysis(repo_path, context)

                review = AIReview(
                    project_id=project.id,
                    type=AIReviewType.analysis,
                    status=AIReviewStatus.completed,
                    summary=result.get("progress_assessment", ""),
                    detail=result,
                    suggestions=result.get("recommendations", []),
                    requested_by=uuid.UUID(job.payload.get("requested_by")) if job.payload.get("requested_by") else None,
                    completed_at=datetime.now(timezone.utc),
                )
                db.add(review)
                await db.flush()
                job.ai_review_id = review.id

            elif job.job_type == JobType.test_scenario:
                if not project or not project.github_repo_url:
                    raise ValueError("Project has no GitHub repo connected")

                org = await db.get(Organization, project.org_id)
                repo_path = await clone_or_update_repo(
                    project.id, job.id, project.github_repo_url, org.github_installation_id
                )
                payload = job.payload
                pr = None
                base, head = None, None
                if payload.get("pr_number"):
                    pr_result = await db.execute(
                        select(PullRequest).where(
                            PullRequest.project_id == project.id,
                            PullRequest.number == payload["pr_number"],
                        )
                    )
                    pr = pr_result.scalar_one_or_none()
                    if pr:
                        base, head = pr.base_ref, pr.head_ref

                result = await run_test_generation(
                    repo_path, payload.get("pr_number"), payload.get("file_paths"),
                    base, head,
                )

                review = AIReview(
                    project_id=project.id,
                    pull_request_id=pr.id if pr else None,
                    type=AIReviewType.test_scenario,
                    status=AIReviewStatus.completed,
                    summary=f"{len(result.get('test_scenarios', []))} test scenarios generated",
                    detail=result,
                    suggestions=[],
                    completed_at=datetime.now(timezone.utc),
                )
                db.add(review)
                await db.flush()
                job.ai_review_id = review.id

            elif job.job_type == JobType.briefing:
                org = await db.get(Organization, job.org_id)
                if not org:
                    raise ValueError("Organization not found")

                # Get all projects with GitHub repos
                projects_result = await db.execute(
                    select(Project).where(Project.org_id == org.id, Project.github_repo_url.isnot(None))
                )
                projects = list(projects_result.scalars().all())

                project_briefings = []
                for proj in projects:
                    try:
                        repo_path = await clone_or_update_repo(
                            proj.id, job.id, proj.github_repo_url, org.github_installation_id
                        )
                        context = await build_project_context(db, proj.id)
                        result = await run_weekly_briefing(repo_path, context)
                        result["project_id"] = str(proj.id)
                        result["project_name"] = proj.name
                        project_briefings.append(result)
                    except Exception:
                        project_briefings.append({
                            "project_id": str(proj.id),
                            "project_name": proj.name,
                            "summary": "Failed to generate briefing",
                            "completed_tasks": 0, "merged_prs": 0,
                        })
                    finally:
                        cleanup_repo(proj.id, job.id)

                # Calculate Monday of this week
                today = date.today()
                monday = today - timedelta(days=today.weekday())

                briefing = WeeklyBriefing(
                    org_id=org.id,
                    week_start=monday,
                    org_summary={"total_projects": len(projects), "briefing_count": len(project_briefings)},
                    project_briefings=project_briefings,
                    status=BriefingStatus.completed,
                    completed_at=datetime.now(timezone.utc),
                )
                db.add(briefing)
                await db.flush()
                job.briefing_id = briefing.id

            job.status = JobStatus.completed
            job.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            job.retry_count += 1
            if job.retry_count >= 3:
                job.status = JobStatus.failed
                job.error_message = str(e)[:500]
            else:
                job.status = JobStatus.queued
                await db.commit()
                await asyncio.sleep(min(30 * job.retry_count, 120))
                asyncio.create_task(process_ai_job(job.id))
                return

        finally:
            # Cleanup repo (except briefing which cleans per-project above)
            if repo_path and job.job_type != JobType.briefing and job.project_id:
                cleanup_repo(job.project_id, job.id)

        await db.commit()


async def recover_stuck_jobs() -> None:
    """Recover jobs that were running when the server crashed."""
    async with async_session() as db:
        stuck = await db.execute(
            select(AIJobQueue).where(AIJobQueue.status.in_([JobStatus.queued, JobStatus.running]))
        )
        for job in stuck.scalars():
            if job.status == JobStatus.running:
                job.retry_count += 1
            if job.retry_count >= 3:
                job.status = JobStatus.failed
                job.error_message = "Server restarted during execution"
            else:
                job.status = JobStatus.queued
                asyncio.create_task(process_ai_job(job.id))
        await db.commit()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/ai/worker.py
git commit -m "feat: implement background AI job worker with retry and recovery"
```

---

## Task 6: GitHub Service Extensions

**Files:**
- Modify: `backend/app/services/github_service.py`

- [ ] **Step 1: Add `post_github_review_comment` function**

Add to `github_service.py`:

```python
def format_review_as_markdown(review_result: dict) -> str:
    """Format AI review result as GitHub-compatible markdown."""
    score = review_result.get("score", "N/A")
    summary = review_result.get("summary", "No summary")
    issues = review_result.get("overall_issues", [])

    parts = [f"## AI Code Review (Score: {score}/10)\n", summary, ""]

    if issues:
        parts.append("### Issues Found\n")
        for issue in issues:
            emoji = {"high": "🔴", "medium": "🟡", "low": "🔵"}.get(issue.get("priority"), "⚪")
            parts.append(f"- {emoji} **{issue.get('type', 'general')}**: {issue.get('description', '')}")

    parts.append("\n---\n*Generated by PM Agent AI*")
    return "\n".join(parts)


async def post_github_review_comment(
    installation_id: int, owner: str, repo: str,
    pr_number: int, review_result: dict
) -> int | None:
    """Post AI review as a GitHub PR comment. Returns comment ID."""
    token = await get_installation_token(installation_id)
    body = format_review_as_markdown(review_result)

    async with httpx.AsyncClient() as client:
        # Post as issue comment (simpler than PR review for now)
        resp = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"body": body},
        )
        if resp.status_code == 201:
            return resp.json().get("id")
        return None
```

- [ ] **Step 2: Extend `handle_pull_request` to save branch refs and trigger AI review**

In the existing `handle_pull_request` function, add branch ref saving to PR upsert and AI job creation for opened PRs:

```python
# Inside the PR upsert section, add:
pr.base_ref = pr_data["base"]["ref"]
pr.head_ref = pr_data["head"]["ref"]

# After the existing db.commit(), add for opened PRs:
if payload["action"] == "opened" and project.github_repo_url:
    from app.models.ai_job_queue import AIJobQueue, JobType, JobTrigger
    job = AIJobQueue(
        project_id=project.id,
        job_type=JobType.code_review,
        trigger=JobTrigger.webhook,
        payload={
            "pr_number": pr_data["number"],
            "base": pr_data["base"]["ref"],
            "head": pr_data["head"]["ref"],
        },
    )
    db.add(job)
    await db.flush()
    import asyncio
    from app.services.ai.worker import process_ai_job
    asyncio.create_task(process_ai_job(job.id))
    await db.commit()
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/github_service.py
git commit -m "feat: add GitHub PR comment posting and auto-review trigger"
```

---

## Task 7: Pydantic Schemas for AI

**Files:**
- Create: `backend/app/schemas/ai.py`

- [ ] **Step 1: Create `backend/app/schemas/ai.py`**

```python
import uuid
from datetime import datetime, date
from pydantic import BaseModel

from app.models.ai_review import AIReviewType, AIReviewStatus
from app.models.ai_job_queue import JobType, JobTrigger, JobStatus
from app.models.weekly_briefing import BriefingStatus


# Job responses
class JobCreatedResponse(BaseModel):
    job_id: uuid.UUID
    status: str = "queued"
    message: str

class JobStatusResponse(BaseModel):
    id: uuid.UUID
    job_type: JobType
    status: JobStatus
    ai_review_id: uuid.UUID | None
    briefing_id: uuid.UUID | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    model_config = {"from_attributes": True}


# AI Review
class AIReviewResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    pull_request_id: uuid.UUID | None
    type: AIReviewType
    status: AIReviewStatus
    summary: str | None
    detail: dict
    suggestions: list
    github_comment_id: int | None
    created_at: datetime
    completed_at: datetime | None
    model_config = {"from_attributes": True}


# Briefing
class BriefingResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    week_start: date
    org_summary: dict
    project_briefings: list
    status: BriefingStatus
    created_at: datetime
    completed_at: datetime | None
    model_config = {"from_attributes": True}


# Request bodies
class TestScenarioRequest(BaseModel):
    pr_number: int | None = None
    file_paths: list[str] | None = None
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/ai.py
git commit -m "feat: add AI Pydantic schemas"
```

---

## Task 8: AI Router

**Files:**
- Create: `backend/app/routers/ai.py`
- Create: `backend/tests/test_ai_router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create `backend/app/routers/ai.py`**

```python
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.pull_request import PullRequest
from app.models.ai_job_queue import AIJobQueue, JobType, JobTrigger
from app.models.ai_review import AIReview
from app.schemas.ai import (
    JobCreatedResponse, JobStatusResponse,
    AIReviewResponse, TestScenarioRequest,
)
from app.services.ai.worker import process_ai_job

router = APIRouter(tags=["ai"])


@router.post("/api/projects/{project_id}/ai/analyze", response_model=JobCreatedResponse, status_code=202)
async def request_analysis(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job = AIJobQueue(
        project_id=project_id,
        job_type=JobType.analysis,
        trigger=JobTrigger.manual,
        payload={"requested_by": str(user.id)},
    )
    db.add(job)
    await db.flush()
    await db.commit()
    asyncio.create_task(process_ai_job(job.id))
    return JobCreatedResponse(job_id=job.id, message="프로젝트 분석이 요청되었습니다.")


@router.post("/api/projects/{project_id}/ai/review/{pr_number}", response_model=JobCreatedResponse, status_code=202)
async def request_review(
    project_id: uuid.UUID,
    pr_number: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pr_result = await db.execute(
        select(PullRequest).where(PullRequest.project_id == project_id, PullRequest.number == pr_number)
    )
    pr = pr_result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=404, detail="PR not found")

    job = AIJobQueue(
        project_id=project_id,
        job_type=JobType.code_review,
        trigger=JobTrigger.manual,
        payload={"pr_number": pr_number, "base": pr.base_ref or "main", "head": pr.head_ref or "main"},
    )
    db.add(job)
    await db.flush()
    await db.commit()
    asyncio.create_task(process_ai_job(job.id))
    return JobCreatedResponse(job_id=job.id, message=f"PR #{pr_number} 코드리뷰가 요청되었습니다.")


@router.post("/api/projects/{project_id}/ai/test-scenarios", response_model=JobCreatedResponse, status_code=202)
async def request_test_scenarios(
    project_id: uuid.UUID,
    body: TestScenarioRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.pr_number and not body.file_paths:
        raise HTTPException(status_code=400, detail="pr_number or file_paths required")

    payload = {}
    if body.pr_number:
        payload["pr_number"] = body.pr_number
    if body.file_paths:
        payload["file_paths"] = body.file_paths

    job = AIJobQueue(
        project_id=project_id,
        job_type=JobType.test_scenario,
        trigger=JobTrigger.manual,
        payload=payload,
    )
    db.add(job)
    await db.flush()
    await db.commit()
    asyncio.create_task(process_ai_job(job.id))
    return JobCreatedResponse(job_id=job.id, message="테스트 시나리오 생성이 요청되었습니다.")


@router.get("/api/ai/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(AIJobQueue, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/api/projects/{project_id}/ai/reviews", response_model=list[AIReviewResponse])
async def list_reviews(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIReview)
        .where(AIReview.project_id == project_id)
        .order_by(AIReview.created_at.desc())
        .limit(20)
    )
    return list(result.scalars().all())


@router.get("/api/projects/{project_id}/ai/reviews/{review_id}", response_model=AIReviewResponse)
async def get_review(
    project_id: uuid.UUID,
    review_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    review = await db.get(AIReview, review_id)
    if not review or review.project_id != project_id:
        raise HTTPException(status_code=404, detail="Review not found")
    return review
```

- [ ] **Step 2: Register router in `main.py`**

Add:
```python
from app.routers import ai
app.include_router(ai.router)
```

- [ ] **Step 3: Write tests and run**

Create `backend/tests/test_ai_router.py` with tests for:
- request_analysis → 202
- get_job_status → 200
- list_reviews → 200 empty list
- request_test_scenarios without params → 400

Run: `cd backend && python -m pytest tests/test_ai_router.py -v`

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/ai.py backend/app/main.py backend/tests/test_ai_router.py
git commit -m "feat: implement AI operation endpoints"
```

---

## Task 9: Briefings Router

**Files:**
- Create: `backend/app/routers/briefings.py`
- Create: `backend/tests/test_briefings_router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create `backend/app/routers/briefings.py`**

```python
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_org_role
from app.models.user import User
from app.models.organization import OrgRole
from app.models.weekly_briefing import WeeklyBriefing
from app.models.ai_job_queue import AIJobQueue, JobType, JobTrigger
from app.schemas.ai import JobCreatedResponse, BriefingResponse
from app.services.ai.worker import process_ai_job

router = APIRouter(tags=["briefings"])


@router.get("/api/orgs/{org_id}/briefings", response_model=list[BriefingResponse])
async def list_briefings(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member)),
):
    result = await db.execute(
        select(WeeklyBriefing)
        .where(WeeklyBriefing.org_id == org_id)
        .order_by(WeeklyBriefing.week_start.desc())
        .limit(10)
    )
    return list(result.scalars().all())


@router.get("/api/orgs/{org_id}/briefings/latest", response_model=BriefingResponse)
async def latest_briefing(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member)),
):
    result = await db.execute(
        select(WeeklyBriefing)
        .where(WeeklyBriefing.org_id == org_id)
        .order_by(WeeklyBriefing.week_start.desc())
        .limit(1)
    )
    briefing = result.scalar_one_or_none()
    if not briefing:
        raise HTTPException(status_code=404, detail="No briefings found")
    return briefing


@router.get("/api/orgs/{org_id}/briefings/{briefing_id}", response_model=BriefingResponse)
async def get_briefing(
    org_id: uuid.UUID,
    briefing_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member)),
):
    briefing = await db.get(WeeklyBriefing, briefing_id)
    if not briefing or briefing.org_id != org_id:
        raise HTTPException(status_code=404, detail="Briefing not found")
    return briefing


@router.post("/api/orgs/{org_id}/briefings/generate", response_model=JobCreatedResponse, status_code=202)
async def generate_briefing(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_org_role(OrgRole.owner, OrgRole.admin)),
):
    job = AIJobQueue(
        org_id=org_id,
        job_type=JobType.briefing,
        trigger=JobTrigger.manual,
        payload={"org_id": str(org_id), "requested_by": str(user.id)},
    )
    db.add(job)
    await db.flush()
    await db.commit()
    asyncio.create_task(process_ai_job(job.id))
    return JobCreatedResponse(job_id=job.id, message="주간 브리핑 생성이 요청되었습니다.")
```

- [ ] **Step 2: Register router in `main.py`**

```python
from app.routers import briefings
app.include_router(briefings.router)
```

- [ ] **Step 3: Write tests and run**

Tests: list_briefings → 200, latest → 404 (no briefings), generate → 202.

Run: `cd backend && python -m pytest -v`

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/briefings.py backend/app/main.py backend/tests/test_briefings_router.py
git commit -m "feat: implement briefing endpoints"
```

---

## Task 10: Scheduler + Lifespan Migration

**Files:**
- Create: `backend/app/scheduler.py`
- Modify: `backend/app/main.py` (add lifespan)

- [ ] **Step 1: Create `backend/app/scheduler.py`**

```python
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.database import async_session
from app.models.organization import Organization
from app.models.ai_job_queue import AIJobQueue, JobType, JobTrigger
from app.services.ai.worker import process_ai_job

scheduler = AsyncIOScheduler()


async def generate_weekly_briefings():
    """Scheduled job: create briefing jobs for all organizations."""
    async with async_session() as db:
        orgs = await db.execute(select(Organization))
        for org in orgs.scalars():
            job = AIJobQueue(
                org_id=org.id,
                job_type=JobType.briefing,
                trigger=JobTrigger.schedule,
                payload={"org_id": str(org.id)},
            )
            db.add(job)
            await db.flush()
            asyncio.create_task(process_ai_job(job.id))
        await db.commit()


# Schedule: Every Monday at 9:00 AM
scheduler.add_job(generate_weekly_briefings, CronTrigger(day_of_week="mon", hour=9, minute=0))
```

- [ ] **Step 2: Migrate `main.py` to lifespan pattern**

Replace the current `main.py` app creation with lifespan:

```python
from contextlib import asynccontextmanager
from app.scheduler import scheduler
from app.services.ai.worker import recover_stuck_jobs
from app.models.ai_job_queue import AIJobQueue, JobStatus

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler.start()
    await recover_stuck_jobs()
    yield
    # Shutdown: mark running jobs as queued for recovery
    async with async_session() as db:
        from sqlalchemy import select
        running = await db.execute(
            select(AIJobQueue).where(AIJobQueue.status == JobStatus.running)
        )
        for job in running.scalars():
            job.status = JobStatus.queued
        await db.commit()
    scheduler.shutdown()

app = FastAPI(title="PM Agent API", lifespan=lifespan)
```

Keep all existing middleware and router registrations unchanged.

- [ ] **Step 3: Run all tests**

Run: `cd backend && python -m pytest -v`

- [ ] **Step 4: Commit**

```bash
git add backend/app/scheduler.py backend/app/main.py
git commit -m "feat: add APScheduler for weekly briefings and lifespan migration"
```

---

## Task 11: Frontend — AI Hooks

**Files:**
- Create: `frontend/src/hooks/use-ai.ts`

- [ ] **Step 1: Create `frontend/src/hooks/use-ai.ts`**

```typescript
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export function useAIReviews(projectId: string) {
  return useQuery({
    queryKey: ["ai-reviews", projectId],
    queryFn: () => api.get(`/api/projects/${projectId}/ai/reviews`).then(r => r.data),
    enabled: !!projectId,
  });
}

export function useAIReview(projectId: string, reviewId: string) {
  return useQuery({
    queryKey: ["ai-review", projectId, reviewId],
    queryFn: () => api.get(`/api/projects/${projectId}/ai/reviews/${reviewId}`).then(r => r.data),
    enabled: !!projectId && !!reviewId,
  });
}

export function useAIJobStatus(jobId: string | null) {
  return useQuery({
    queryKey: ["ai-job", jobId],
    queryFn: () => api.get(`/api/ai/jobs/${jobId}`).then(r => r.data),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 3000; // Poll every 3s while running
    },
  });
}

export function useRequestAnalysis(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post(`/api/projects/${projectId}/ai/analyze`).then(r => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ai-reviews", projectId] }),
  });
}

export function useRequestReview(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (prNumber: number) =>
      api.post(`/api/projects/${projectId}/ai/review/${prNumber}`).then(r => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ai-reviews", projectId] }),
  });
}

export function useRequestTestScenarios(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { pr_number?: number; file_paths?: string[] }) =>
      api.post(`/api/projects/${projectId}/ai/test-scenarios`, body).then(r => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ai-reviews", projectId] }),
  });
}

export function useBriefings(orgId: string) {
  return useQuery({
    queryKey: ["briefings", orgId],
    queryFn: () => api.get(`/api/orgs/${orgId}/briefings`).then(r => r.data),
    enabled: !!orgId,
  });
}

export function useLatestBriefing(orgId: string) {
  return useQuery({
    queryKey: ["briefing-latest", orgId],
    queryFn: () => api.get(`/api/orgs/${orgId}/briefings/latest`).then(r => r.data),
    enabled: !!orgId,
  });
}

export function useGenerateBriefing(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post(`/api/orgs/${orgId}/briefings/generate`).then(r => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["briefings", orgId] }),
  });
}
```

- [ ] **Step 2: Build check**

Run: `cd /Users/kimjihun/Desktop/pmai/frontend && npm run build`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/use-ai.ts
git commit -m "feat: add AI React Query hooks"
```

---

## Task 12: Frontend — AI Tab + Review Components

**Files:**
- Create: `frontend/src/components/ai/ai-review-list.tsx`
- Create: `frontend/src/components/ai/ai-review-detail.tsx`
- Create: `frontend/src/components/project/ai-tab.tsx`
- Modify: `frontend/src/app/(dashboard)/org/[slug]/project/[projectId]/page.tsx` (add AI tab)

- [ ] **Step 1: Create `ai-review-list.tsx`**

List component showing AI reviews with type badge, summary, timestamp. Loading state for running jobs.

- [ ] **Step 2: Create `ai-review-detail.tsx`**

Detail view: summary, suggestions with priority badges (critical=red, warning=yellow, info=blue), file comments section for code reviews.

- [ ] **Step 3: Create `ai-tab.tsx`**

Combines: action buttons (Analyze, Test Scenarios), running job indicator, review list, and detail view (dialog on click).

- [ ] **Step 4: Add AI tab to project detail page**

Add a 6th tab "AI" using the existing Tabs component pattern.

- [ ] **Step 5: Build check**

Run: `cd /Users/kimjihun/Desktop/pmai/frontend && npm run build`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ai/ frontend/src/components/project/ai-tab.tsx frontend/src/app/
git commit -m "feat: implement AI tab with review list and detail views"
```

---

## Task 13: Frontend — PR Review Badge

**Files:**
- Create: `frontend/src/components/ai/review-badge.tsx`
- Modify: `frontend/src/components/project/github-tab.tsx`

- [ ] **Step 1: Create `review-badge.tsx`**

Small badge showing: AI review score (e.g., "8/10"), spinner if running, "Review" button if none.

- [ ] **Step 2: Modify github-tab.tsx**

Add review badge next to each PR in the list. Query AI reviews for the project to match by PR id.

- [ ] **Step 3: Build check and commit**

```bash
git commit -m "feat: add AI review badges to PR list"
```

---

## Task 14: Frontend — Weekly Briefing

**Files:**
- Create: `frontend/src/components/ai/briefing-card.tsx`
- Create: `frontend/src/app/(dashboard)/org/[slug]/briefings/page.tsx`
- Modify: `frontend/src/app/(dashboard)/org/[slug]/page.tsx` (add briefing section)

- [ ] **Step 1: Create `briefing-card.tsx`**

Card component: week display, org summary, expandable project briefings (accordion), generate button.

- [ ] **Step 2: Create briefings page**

Full briefing view: latest briefing + archive list. Each briefing expandable with per-project details.

- [ ] **Step 3: Add briefing section to org dashboard**

Add a "Weekly Briefing" card at the top of the org dashboard page showing the latest briefing summary.

- [ ] **Step 4: Build check and commit**

```bash
git commit -m "feat: implement weekly briefing page and dashboard section"
```

---

## Task 15: End-to-End Verification

- [ ] **Step 1: Run all backend tests**

```bash
cd /Users/kimjihun/Desktop/pmai/backend && python -m pytest -v
```

- [ ] **Step 2: Build frontend**

```bash
cd /Users/kimjihun/Desktop/pmai/frontend && npm run build
```

- [ ] **Step 3: Final commit**

```bash
git commit -m "feat: complete Phase 2 — AI Agent Engine"
```
