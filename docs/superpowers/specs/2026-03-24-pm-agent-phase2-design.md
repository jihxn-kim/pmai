# PM Agent - Phase 2 Design: AI Agent Engine

## Overview

Phase 1에서 구축한 PM 플랫폼에 AI 엔진을 추가한다. Claude Agent SDK를 활용하여 코드리뷰, 프로젝트 분석, 테스트 시나리오 생성을 자동화하고, 주간 브리핑을 생성한다. AI는 분석과 제안만 수행하며, 실제 실행(태스크 재배정, 일정 변경 등)은 사람이 한다.

### Phase Context

| Phase | 범위 | 상태 |
|-------|------|------|
| 1 | 코어 플랫폼 + GitHub 연동 + 웹 대시보드 | 완료 |
| **2 (이번)** | AI Agent 엔진 (코드리뷰, 진척도 분석, 태스크 계획) | 진행 |
| 3 | Slack 봇 + 자동화 엔진 (알림, 이벤트 트리거) | 대기 |
| 4 | Google Calendar + Notion 연동 | 대기 |

### Phase 2 Scope

**포함:**
- Claude Agent SDK 기반 AI 실행 엔진
- 서브에이전트: code-reviewer, project-analyst, test-generator
- 비동기 AI 작업 큐 (AIJobQueue)
- PR 생성 시 자동 코드리뷰 (GitHub PR 코멘트 + DB 저장)
- 프로젝트 분석 (진척도, 지연 원인, 리스크, 제안)
- 테스트 시나리오 자동 생성
- 매주 월요일 주간 브리핑 (조직 전체 + 프로젝트별)
- 대시보드 수동 분석 요청
- 프론트엔드: AI 탭, PR 코드리뷰 뱃지, 주간 브리핑 페이지

**제외 (이후 Phase):**
- AI 자율 실행 (태스크 재배정, 일정 변경 등은 사람이 수행)
- Slack 알림 연동 (Phase 3)
- Google Calendar / Notion 연동 (Phase 4)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Next.js (Frontend)                   │
│  ┌───────────┐ ┌──────────┐ ┌────────────────────┐  │
│  │ AI 분석탭 │ │ 브리핑   │ │ PR 코드리뷰 뷰    │  │
│  └───────────┘ └──────────┘ └────────────────────┘  │
└──────────────────┬──────────────────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────────────────┐
│              FastAPI (Backend)                       │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐  │
│  │ AI Service   │ │ Scheduler    │ │ 기존 서비스  │  │
│  │ (Agent SDK)  │ │ (APScheduler)│ │             │  │
│  └──────┬───────┘ └──────┬───────┘ └─────────────┘  │
│         │                │                           │
│  ┌──────▼────────────────▼──────────────────────┐   │
│  │         Agent Executor (공통 실행 레이어)       │   │
│  │  ┌────────────┐ ┌──────────┐ ┌─────────────┐ │   │
│  │  │ code-review│ │ analyst  │ │ test-gen    │ │   │
│  │  │ subagent   │ │ subagent │ │ subagent    │ │   │
│  │  └────────────┘ └──────────┘ └─────────────┘ │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────┬──────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
 PostgreSQL    GitHub API     Git Repos
                (코멘트)      (clone)
```

### Tech Stack (추가)

| 레이어 | 기술 | 이유 |
|--------|------|------|
| AI Engine | Claude Agent SDK (Python) | 파일 탐색, 명령 실행 내장, 서브에이전트 지원 |
| Scheduler | APScheduler | FastAPI와 통합 용이, 크론 스케줄 지원 |
| Background Worker | asyncio.create_task | Phase 2에서는 단순하게, Phase 3에서 Celery 등 도입 가능 |

---

## Configuration Changes

기존 `backend/app/config.py`의 `Settings`에 추가:

```python
# AI Engine
anthropic_api_key: str = ""              # Claude Agent SDK 인증
ai_repo_base_path: str = "/tmp/pmai/repos"  # 레포 clone 경로
ai_model: str = "claude-opus-4-6"        # Agent SDK 모델
ai_max_turns: int = 20                   # Agent 최대 턴 수
```

`.env.example`에도 추가:
```env
# AI Engine (Phase 2)
ANTHROPIC_API_KEY=
AI_REPO_BASE_PATH=/tmp/pmai/repos
AI_MODEL=claude-opus-4-6
```

---

## Phase 1 Model Changes

### PullRequest에 branch 정보 추가

수동 코드리뷰 요청 시 GitHub API 호출 없이 branch 정보를 사용하기 위해:

| 필드 | 타입 | 설명 |
|------|------|------|
| base_ref | VARCHAR | PR의 base branch (nullable) |
| head_ref | VARCHAR | PR의 head branch (nullable) |

기존 `handle_pull_request` webhook 핸들러에서 이 필드를 함께 저장하도록 수정.

---

## Data Model (추가 테이블)

### AIReview

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project |
| pull_request_id | UUID | FK → PullRequest (nullable) |
| type | ENUM | code_review / analysis / test_scenario |
| status | ENUM | pending / running / completed / failed |
| summary | TEXT | AI 분석 요약 |
| detail | JSONB | 상세 결과 (파일별 코멘트, 점수 등) |
| suggestions | JSONB | 제안 목록 [{type, title, description, priority}] |
| github_comment_id | INTEGER | GitHub에 작성된 코멘트 ID (nullable) |
| requested_by | UUID | FK → User (nullable, 수동 요청 시) |
| created_at | TIMESTAMP | 생성일 |
| completed_at | TIMESTAMP | 완료 시각 (nullable) |

### WeeklyBriefing

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| org_id | UUID | FK → Organization |
| week_start | DATE | 해당 주 월요일 날짜 |
| org_summary | JSONB | 조직 전체 요약 |
| project_briefings | JSONB | 프로젝트별 상세 브리핑 배열 |
| status | ENUM | pending / running / completed / failed |
| created_at | TIMESTAMP | 생성일 |
| completed_at | TIMESTAMP | 완료 시각 (nullable) |

Note: `project_briefings`의 `project_name`은 브리핑 생성 시점의 이름. 프로젝트 이름이 변경되어도 과거 브리핑은 생성 시점 이름을 유지.

`project_briefings` JSONB 구조:
```json
[{
  "project_id": "uuid",
  "project_name": "string",
  "completed_tasks": 5,
  "merged_prs": 3,
  "in_progress": ["태스크 제목1", "태스크 제목2"],
  "delayed_items": [{"title": "...", "days_overdue": 3, "cause": "..."}],
  "risk_analysis": "string",
  "recommendations": ["제안1", "제안2"],
  "workload_per_member": [{"name": "...", "task_count": 5, "status": "과부하"}]
}]
```

### AIJobQueue

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project (nullable, 브리핑은 org 레벨) |
| org_id | UUID | FK → Organization (nullable) |
| job_type | ENUM | code_review / analysis / briefing / test_scenario |
| trigger | ENUM | webhook / schedule / manual |
| payload | JSONB | 작업에 필요한 데이터 (PR 번호, branch 등) |
| status | ENUM | queued / running / completed / failed |
| ai_review_id | UUID | FK → AIReview (nullable) |
| briefing_id | UUID | FK → WeeklyBriefing (nullable) |
| error_message | TEXT | 실패 시 에러 메시지 (nullable) |
| retry_count | INTEGER | 재시도 횟수 (default 0) |
| created_at | TIMESTAMP | 생성일 |
| completed_at | TIMESTAMP | 완료 시각 (nullable) |

재시도 정책: 최대 3회, 실패 후 status를 failed로 설정.

---

## AI Service Layer

### Agent Executor (공통 실행 모듈)

`backend/app/services/ai/executor.py`

책임:
1. 프로젝트의 GitHub 레포를 로컬에 clone 또는 업데이트
2. Agent SDK 호출 (prompt, tools, subagents 설정)
3. 결과를 구조화된 형태로 파싱
4. 클린업

레포 관리:
- 경로: `{ai_repo_base_path}/{project_id}/{job_id}/` (job별 격리)
- 이미 존재하면 `git fetch origin && git reset --hard origin/main`
- clone 시 GitHub App installation token 사용 (기존 `get_installation_token` 재활용)
- 작업 완료 후 job별 디렉토리 삭제 (디스크 관리)
- 프로젝트별 base clone을 캐시하고, job마다 `git worktree add`로 격리하는 것도 가능 (성능 최적화)

### 서브에이전트 정의

**code-reviewer**
```
시스템 프롬프트:
  "이 PR의 변경사항을 리뷰해. 보안 취약점, 성능 이슈, 코드 품질,
  유지보수성 관점에서 분석하고, 파일별로 구체적 코멘트를 작성해.
  결과를 JSON으로 출력해."

tools: Read, Grep, Glob, Bash
입력: PR 번호, base branch, head branch
출력 스키마:
  {
    summary: string,
    score: number (1-10),
    file_comments: [{file, line, comment, severity: "critical"|"warning"|"info"}],
    overall_issues: [{type, description, priority}]
  }
```

**project-analyst**
```
시스템 프롬프트:
  "이 프로젝트의 현재 상태를 분석해. git log, 태스크 상태, PR 현황을
  종합해서 진척도 평가, 지연 원인, 리스크를 파악해.
  결과를 JSON으로 출력해."

tools: Read, Bash (git log, git shortlog), Grep
입력: 프로젝트 정보 + 태스크 목록 + PR 목록 (컨텍스트로 전달)
출력 스키마:
  {
    progress_assessment: string,
    progress_score: number (0-100),
    delays: [{task, days_overdue, likely_cause}],
    risks: [{description, severity, mitigation}],
    recommendations: [{type: "reassign"|"reschedule"|"deprioritize"|"escalate",
                       title, description, target_task_id?}]
  }
```

**test-generator**
```
시스템 프롬프트:
  "이 코드 변경사항에 대한 테스트 시나리오를 작성해.
  핵심 로직, 엣지 케이스, 에러 케이스를 포함해.
  결과를 JSON으로 출력해."

tools: Read, Grep, Glob
입력: 변경된 파일 목록, diff
출력 스키마:
  {
    test_scenarios: [{
      name: string,
      description: string,
      category: "happy_path"|"edge_case"|"error_case",
      steps: [string],
      expected_result: string,
      priority: "high"|"medium"|"low"
    }]
  }
```

### Agent SDK 호출 패턴

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, ResultMessage

async def run_code_review(repo_path: str, pr_number: int, base: str, head: str) -> dict:
    result = None
    async for message in query(
        prompt=f"""PR #{pr_number}을 리뷰해줘.
        base branch: {base}, head branch: {head}
        git diff {base}...{head} 를 실행해서 변경사항을 확인하고 리뷰해.""",
        options=ClaudeAgentOptions(
            cwd=repo_path,
            allowed_tools=["Read", "Grep", "Glob", "Bash"],
            system_prompt=CODE_REVIEWER_PROMPT,
            output_format={"type": "json", "schema": CODE_REVIEW_SCHEMA},
            max_turns=20,
        )
    ):
        if isinstance(message, ResultMessage):
            result = json.loads(message.result)
    return result
```

---

## Trigger Mechanisms

### 1. 이벤트 기반: PR 생성 시 자동 코드리뷰

기존 `github_service.handle_pull_request` 확장:

```python
async def handle_pull_request(db, payload):
    # 기존 로직: PullRequest upsert + ActivityLog
    ...

    # Phase 2 추가: PR opened 이벤트 시 코드리뷰 job 생성
    if payload["action"] == "opened":
        job = AIJobQueue(
            project_id=project.id,
            job_type="code_review",
            trigger="webhook",
            payload={"pr_number": pr_data["number"], "base": pr_data["base"]["ref"], "head": pr_data["head"]["ref"]},
            status="queued",
        )
        db.add(job)
        await db.commit()

        # Background worker에게 알림 (또는 asyncio.create_task)
        asyncio.create_task(process_ai_job(job.id))
```

### 2. 스케줄 기반: 매주 월요일 주간 브리핑

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job(CronTrigger(day_of_week='mon', hour=9, minute=0))
async def generate_weekly_briefings():
    async with async_session() as db:
        # 모든 조직 조회
        orgs = await db.execute(select(Organization))
        for org in orgs.scalars():
            job = AIJobQueue(
                org_id=org.id,
                job_type="briefing",
                trigger="schedule",
                payload={"org_id": str(org.id)},
                status="queued",
            )
            db.add(job)
            await db.flush()
            asyncio.create_task(process_ai_job(job.id))
        await db.commit()
```

스케줄러는 `main.py`의 `lifespan`에서 시작/종료:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()
```

### 3. 수동 요청: 대시보드에서 API 호출

요청 → AIJobQueue 생성 → 202 Accepted 반환 → Background worker 처리.

---

## Background Worker

`backend/app/services/ai/worker.py`

```python
async def process_ai_job(job_id: uuid.UUID):
    async with async_session() as db:
        job = await db.get(AIJobQueue, job_id)
        job.status = "running"
        await db.commit()

        try:
            if job.job_type == "code_review":
                result = await run_code_review(...)
                review = AIReview(type="code_review", status="completed", ...)
                db.add(review)
                await db.flush()
                job.ai_review_id = review.id
                await post_github_review_comment(...)

            elif job.job_type == "analysis":
                result = await run_project_analysis(...)
                review = AIReview(type="analysis", status="completed", ...)
                db.add(review)
                await db.flush()
                job.ai_review_id = review.id

            elif job.job_type == "briefing":
                result = await run_weekly_briefing(...)
                briefing = WeeklyBriefing(status="completed", ...)
                db.add(briefing)
                await db.flush()
                job.briefing_id = briefing.id

            elif job.job_type == "test_scenario":
                result = await run_test_generation(...)
                review = AIReview(type="test_scenario", status="completed", ...)
                db.add(review)
                await db.flush()
                job.ai_review_id = review.id

            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            job.retry_count += 1
            if job.retry_count >= 3:
                job.status = "failed"
                job.error_message = str(e)
            else:
                job.status = "queued"
                # 지연 후 재시도 디스패치
                await asyncio.sleep(min(30 * job.retry_count, 120))
                asyncio.create_task(process_ai_job(job.id))

        await db.commit()
```

서버 재시작 시 복구:

```python
# lifespan에서 실행
async def recover_stuck_jobs():
    async with async_session() as db:
        stuck = await db.execute(
            select(AIJobQueue).where(AIJobQueue.status.in_(["queued", "running"]))
        )
        for job in stuck.scalars():
            if job.status == "running":
                job.retry_count += 1  # running이었던 job은 재시도 카운트 증가
            if job.retry_count >= 3:
                job.status = "failed"
                job.error_message = "Server restarted during execution"
            else:
                job.status = "queued"
                asyncio.create_task(process_ai_job(job.id))
        await db.commit()
```

Graceful shutdown 시 running job 처리:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    await recover_stuck_jobs()
    yield
    # Shutdown: running 상태의 job을 queued로 복원
    async with async_session() as db:
        running = await db.execute(
            select(AIJobQueue).where(AIJobQueue.status == "running")
        )
        for job in running.scalars():
            job.status = "queued"
        await db.commit()
    scheduler.shutdown()
```

**Note:** Phase 2에서는 `main.py`를 `app = FastAPI(lifespan=lifespan, ...)`로 마이그레이션해야 함. 기존 라우터/미들웨어는 변경 없음.

---

## API Endpoints (추가)

### AI Operations

모든 AI 엔드포인트는 `get_current_user` 인증 필수. 프로젝트 레벨 엔드포인트는 프로젝트 멤버 확인.

```
POST   /api/projects/{project_id}/ai/analyze           # 프로젝트 분석 요청 → 202 (프로젝트 멤버)
POST   /api/projects/{project_id}/ai/review/{pr_number} # PR 코드리뷰 요청 → 202 (프로젝트 멤버)
POST   /api/projects/{project_id}/ai/test-scenarios     # 테스트 시나리오 요청 → 202 (프로젝트 멤버)
GET    /api/ai/jobs/{job_id}                            # 작업 상태 확인 (인증된 사용자)
GET    /api/projects/{project_id}/ai/reviews            # AI 리뷰 목록 (프로젝트 멤버)
GET    /api/projects/{project_id}/ai/reviews/{review_id} # AI 리뷰 상세 (프로젝트 멤버)
```

테스트 시나리오 요청 body:
```json
{
  "pr_number": 123,          // PR 기반 (optional)
  "file_paths": ["src/..."]  // 특정 파일 기반 (optional)
  // 둘 중 하나 필수. pr_number 우선.
}
```

### Weekly Briefings

```
GET    /api/orgs/{org_id}/briefings                     # 주간 브리핑 목록 (org 멤버)
GET    /api/orgs/{org_id}/briefings/latest              # 최신 브리핑 (org 멤버)
GET    /api/orgs/{org_id}/briefings/{briefing_id}       # 특정 브리핑 상세 (org 멤버)
POST   /api/orgs/{org_id}/briefings/generate            # 수동 브리핑 생성 → 202 (org owner/admin)
```

### 응답 형식

비동기 작업 요청 시:
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "AI 분석이 요청되었습니다."
}
```

작업 상태 확인 시:
```json
{
  "id": "uuid",
  "job_type": "code_review",
  "status": "completed",
  "result_id": "uuid",
  "created_at": "2026-03-24T09:00:00Z",
  "completed_at": "2026-03-24T09:02:30Z"
}
```

---

## Web Dashboard (추가)

### 프로젝트 상세 — AI 탭 (새 탭)

기존 5개 탭에 "AI" 탭 추가:

```
AI 탭 구성:
├── 분석 요청 버튼 그룹
│   ├── "프로젝트 분석" 버튼
│   └── "테스트 시나리오 생성" 버튼
├── 진행 중 작업 (status: running → 로딩 스피너)
├── 최근 AI 리뷰 목록
│   ├── 타입 뱃지 (코드리뷰/분석/테스트)
│   ├── 요약 텍스트
│   ├── 생성 시각
│   └── 클릭 시 상세 보기
└── 리뷰 상세 뷰
    ├── 요약
    ├── 제안 목록 (priority 뱃지: critical=red, warning=yellow, info=blue)
    └── 파일별 코멘트 (코드리뷰인 경우)
```

### GitHub 탭 — PR 코드리뷰 뱃지

PR 목록의 각 항목에:
- AI 리뷰 완료 → 점수 뱃지 (예: "8/10") + 요약 한 줄
- AI 리뷰 진행 중 → 스피너 아이콘
- AI 리뷰 없음 → "리뷰 요청" 버튼

### 조직 대시보드 — 주간 브리핑 섹션

```
Weekly Briefing 섹션:
├── 최신 브리핑 카드
│   ├── 주차 표시 (예: "2026년 3월 4주차")
│   ├── 조직 전체 요약
│   └── "상세 보기" 버튼
├── 프로젝트별 브리핑 (아코디언)
│   ├── 프로젝트명 + 진척도 바
│   ├── 완료된 태스크 / 머지된 PR
│   ├── 지연 항목 + 원인
│   ├── 리스크 분석
│   ├── 이번 주 추천 사항
│   └── 팀원별 작업량
└── 과거 브리핑 아카이브 (주차 선택)
```

---

## GitHub Integration 변경

### 권한 업그레이드

Phase 1에서 Issues: read → **Phase 2에서 Issues: read & write** + **Pull requests: write**

필요한 이유:
- PR에 코드리뷰 코멘트 작성 (`POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews`)

### GitHub 코멘트 작성

```python
async def post_github_review_comment(
    installation_id: int, owner: str, repo: str,
    pr_number: int, review_result: dict
) -> int:
    token = await get_installation_token(installation_id)

    # PR review 코멘트 작성
    body = format_review_as_markdown(review_result)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={
                "body": body,
                "event": "COMMENT",  # COMMENT (not APPROVE or REQUEST_CHANGES — AI는 제안만)
                "comments": [
                    {"path": c["file"], "line": c["line"], "body": c["comment"]}
                    for c in review_result.get("file_comments", [])
                ]
            }
        )
        return resp.json().get("id")
```

---

## Project Structure (추가 파일)

```
backend/app/
├── services/
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── executor.py          # Agent Executor (레포 관리, Agent SDK 호출)
│   │   ├── worker.py            # Background worker (job 처리, 재시도)
│   │   ├── prompts.py           # 서브에이전트 프롬프트 상수
│   │   └── schemas.py           # AI 출력 스키마 정의
│   └── (기존 서비스들)
├── models/
│   ├── ai_review.py             # AIReview, AIReviewType, AIReviewStatus
│   ├── weekly_briefing.py       # WeeklyBriefing
│   ├── ai_job_queue.py          # AIJobQueue, JobType, JobTrigger, JobStatus
│   └── (기존 모델들)
├── schemas/
│   ├── ai.py                    # AI 관련 Pydantic 스키마
│   └── (기존 스키마들)
├── routers/
│   ├── ai.py                    # /api/projects/{id}/ai/*, /api/ai/jobs/*
│   ├── briefings.py             # /api/orgs/{id}/briefings/*
│   └── (기존 라우터들)
└── scheduler.py                 # APScheduler 설정

frontend/src/
├── components/
│   ├── ai/
│   │   ├── ai-review-list.tsx   # AI 리뷰 목록
│   │   ├── ai-review-detail.tsx # AI 리뷰 상세
│   │   ├── review-badge.tsx     # PR 코드리뷰 뱃지
│   │   └── briefing-card.tsx    # 주간 브리핑 카드
│   └── (기존 컴포넌트들)
├── hooks/
│   ├── use-ai.ts                # AI 관련 React Query hooks
│   └── (기존 hooks)
└── app/(dashboard)/
    └── org/[slug]/
        ├── briefings/page.tsx   # 주간 브리핑 페이지
        └── (기존 페이지들)
```

---

## main.py Changes

Phase 2에서 `main.py` 변경 사항:
1. `app = FastAPI(...)` → `app = FastAPI(lifespan=lifespan, ...)` 마이그레이션
2. 새 라우터 등록:
```python
from app.routers import ai, briefings
app.include_router(ai.router)
app.include_router(briefings.router)
```
3. 기존 라우터/미들웨어는 변경 없음

---

## Error Handling

- AI 작업 실패 시 최대 3회 재시도 후 failed 처리
- 서버 재시작 시 stuck job (status: queued/running) 복구
- Agent SDK 타임아웃: max_turns=20으로 무한 루프 방지
- GitHub API 실패 시 리뷰 결과는 DB에 저장 (코멘트만 실패)
- 레포 clone 실패 시 명확한 에러 메시지 (권한/네트워크 등)

---

## Testing Strategy

- **Backend**: pytest + httpx (기존 패턴)
  - AI 서비스: Agent SDK 호출을 mock하고, 결과 파싱/저장 로직 테스트
  - Worker: job 상태 전이, 재시도 로직 테스트
  - Scheduler: 브리핑 생성 트리거 테스트
- **Frontend**: 기존 패턴 (빌드 검증)
- Agent SDK 자체는 통합 테스트에서 실제 호출 (별도 E2E)

---

## Dependencies (추가)

```
claude-agent-sdk
apscheduler>=3.10,<4.0
```
