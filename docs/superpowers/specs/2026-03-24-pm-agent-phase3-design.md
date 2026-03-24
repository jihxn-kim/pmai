# PM Agent - Phase 3 Design: Slack Bot + Automation Engine

## Overview

Phase 1~2에서 구축한 PM 플랫폼에 Slack 봇을 추가한다. 멘션 대화형 인터페이스로 프로젝트 상태 확인, AI 리뷰 요청, 브리핑 조회 등이 가능하며, GitHub 이벤트와 마감일에 따른 자동 알림을 Slack 채널/DM으로 발송한다.

### Phase Context

| Phase | 범위 | 상태 |
|-------|------|------|
| 1 | 코어 플랫폼 + GitHub 연동 + 웹 대시보드 | 완료 |
| 2 | AI Agent 엔진 (코드리뷰, 진척도 분석, 테스트 계획) | 완료 |
| **3 (이번)** | Slack 봇 + 자동화 엔진 (알림, 이벤트 트리거) | 진행 |
| 4 | Google Calendar + Notion 연동 | 대기 |

### Phase 3 Scope

**포함:**
- Slack 봇 (slack-bolt, HTTP Mode)
- 멘션 대화형 인터페이스 (`@PM Agent ...` → 자연어 해석 → 액션)
- Claude API tool_use로 의도 파싱
- 알림 발송: 프로젝트 채널 + 조직 공통 채널 + 개인 DM
- GitHub 이벤트 → Slack 알림 (PR 생성/머지, 리뷰 완료)
- 마감 리마인더 (D-1 DM, 초과 시 채널+DM)
- AI 작업 완료 → Slack 알림
- 주간 브리핑 → 조직 공통 채널 알림
- Slack OAuth 연결 + 채널/유저 매핑
- 프론트엔드: 설정 페이지에 Slack 연결 UI

**제외 (Phase 4):**
- Google Calendar 연동
- 회의 전 자동 브리핑 (Phase 3에서는 수동 요청)
- Notion 연동

---

## Architecture

```
┌─────────────┐         ┌──────────────────────────────────────┐
│  Slack API   │ ──────▶ │  FastAPI (Backend)                    │
│  (이벤트/멘션) │ ◀────── │  ┌──────────────────────────────────┐ │
└─────────────┘         │  │ Slack Service                     │ │
                        │  │  ├── 이벤트 수신 (멘션)             │ │
                        │  │  ├── Claude API (자연어 해석)       │ │
                        │  │  ├── 알림 발송 (채널/DM)            │ │
                        │  │  └── Notification Queue            │ │
                        │  └──────────────────────────────────┘ │
                        │  ┌────────────┐ ┌──────────────────┐  │
                        │  │ 기존 서비스 │ │ AI 서비스 (Phase2)│  │
                        │  └────────────┘ └──────────────────┘  │
                        └──────────────────────────────────────┘
```

### Tech Stack (추가)

| 레이어 | 기술 | 이유 |
|--------|------|------|
| Slack SDK | slack-bolt + slack-sdk (Python) | 공식 SDK, 이벤트/메시지 처리 |
| 통신 모드 | HTTP Mode | 프로덕션 배포에 적합 |
| 자연어 해석 | Claude API (tool_use) | 기존 anthropic_api_key 재활용, 정확한 의도 파싱 |
| 메시지 포맷 | Slack Block Kit | 리치 메시지 (버튼, 뱃지 등) |

---

## Configuration Changes

기존 `backend/app/config.py`의 `Settings`에 추가:

```python
# Slack
slack_client_id: str = ""
slack_client_secret: str = ""
slack_signing_secret: str = ""
slack_bot_token: str = ""  # 기본값, DB에서 워크스페이스별로 관리
```

`.env.example`에 추가:
```env
# Slack (Phase 3)
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
SLACK_SIGNING_SECRET=
```

---

## Data Model (추가 테이블)

### SlackWorkspace

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| org_id | UUID | FK → Organization (unique — 조직당 하나) |
| slack_team_id | VARCHAR | Slack 워크스페이스 ID (unique) |
| slack_bot_token | VARCHAR | Bot User OAuth Token (암호화 저장) |
| slack_org_channel_id | VARCHAR | 조직 공통 채널 ID (nullable) |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

### SlackChannelMapping

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project (unique — 프로젝트당 하나) |
| slack_channel_id | VARCHAR | Slack 채널 ID |
| created_at | TIMESTAMP | 생성일 |

### SlackUserMapping

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| user_id | UUID | FK → User (unique — 유저당 하나) |
| slack_user_id | VARCHAR | Slack 사용자 ID |
| created_at | TIMESTAMP | 생성일 |

---

## Slack Bot Service

### 이벤트 수신 흐름

```
1. Slack에서 @PM Agent 멘션
2. POST /api/slack/events 로 이벤트 전달
3. signing_secret으로 서명 검증
4. app_mention 이벤트 처리:
   a. 멘션 텍스트 추출
   b. Slack 유저 → PM Agent 유저 매핑
   c. Claude API에 tool_use로 의도 파싱
   d. 파싱된 함수 호출 (기존 서비스)
   e. 결과를 Block Kit 메시지로 포맷팅
   f. Slack API로 응답 전송
```

### 자연어 해석 (Claude API tool_use)

Claude API에 전달하는 도구 정의:

```python
SLACK_TOOLS = [
    {
        "name": "get_project_status",
        "description": "프로젝트 진행상황 조회 (진척도, 태스크 현황, PR 현황)",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "프로젝트 이름 (부분 매칭 가능)"}
            },
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
                "pr_number": {"type": "integer", "description": "PR 번호"},
                "project_name": {"type": "string", "description": "프로젝트 이름"}
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
            "properties": {
                "project_name": {"type": "string"}
            },
            "required": ["project_name"]
        }
    },
    {
        "name": "run_project_analysis",
        "description": "프로젝트 AI 분석 실행 (진척도, 리스크, 제안)",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string"}
            },
            "required": ["project_name"]
        }
    },
]
```

프로젝트 이름 → project_id 매핑:
- DB에서 프로젝트 이름 fuzzy matching (ILIKE '%name%')
- 여러 개 매칭되면 목록 보여주고 선택 요청
- 채널에 매핑된 프로젝트가 있으면 기본값으로 사용

### Slack 메시지 포맷팅

Block Kit을 사용한 리치 메시지:

```python
def format_project_status(progress_data: dict) -> list[dict]:
    """프로젝트 현황을 Slack Block Kit으로 포맷팅"""
    return [
        {"type": "header", "text": {"type": "plain_text", "text": f"📊 {progress_data['name']} 프로젝트 현황"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*진척도:* {progress_data['progress']}%"},
            {"type": "mrkdwn", "text": f"*완료:* {progress_data['done']}/{progress_data['total']}"},
            {"type": "mrkdwn", "text": f"*진행 중:* {progress_data['in_progress']}"},
            {"type": "mrkdwn", "text": f"*오픈 PR:* {progress_data['open_prs']}"},
        ]},
    ]
```

---

## Notification System

### 알림 트리거

| 이벤트 | 대상 | 메시지 |
|--------|------|--------|
| PR 생성 | 프로젝트 채널 | "🔀 PR #{number} opened by {author}: {title}" |
| PR 머지 | 프로젝트 채널 | "✅ PR #{number} merged: {title}" |
| PR 리뷰 완료 | 프로젝트 채널 + 작성자 DM | "👀 PR #{number}에 리뷰가 달렸습니다" |
| AI 코드리뷰 완료 | 프로젝트 채널 | "🤖 AI 리뷰 완료: PR #{number} ({score}/10)" |
| 태스크 마감 D-1 | 담당자 DM | "⏰ '{task_title}' 내일 마감입니다" |
| 태스크 마감 초과 | 담당자 DM + 프로젝트 채널 | "🚨 '{task_title}' 마감 {days}일 초과" |
| 주간 브리핑 완료 | 조직 공통 채널 | 브리핑 요약 + 대시보드 링크 |

### 알림 발송 구현

기존 서비스에 알림 훅을 추가하는 방식:

```python
# 알림 발송 함수 (공통)
async def send_slack_notification(
    org_id: uuid.UUID,
    channel_type: str,  # "project" | "org" | "dm"
    project_id: uuid.UUID | None,
    user_id: uuid.UUID | None,  # DM인 경우
    blocks: list[dict],
    text: str,  # fallback text
):
    # 1. org_id → SlackWorkspace → bot_token
    # 2. channel_type에 따라 채널 결정
    #    - "project": SlackChannelMapping에서 조회
    #    - "org": SlackWorkspace.slack_org_channel_id
    #    - "dm": SlackUserMapping에서 slack_user_id 조회 → conversations.open → DM 발송
    # 3. slack_sdk로 chat.postMessage 호출
```

### 기존 코드 확장 포인트

**GitHub webhook 핸들러 (github_service.py):**
```python
# handle_pull_request 끝에:
if payload["action"] in ("opened", "closed"):
    await send_slack_notification(
        org_id=project.org_id,
        channel_type="project",
        project_id=project.id,
        blocks=format_pr_notification(pr_data, payload["action"]),
        text=f"PR #{pr_data['number']} {payload['action']}: {pr_data['title']}",
    )

# handle_pull_request_review 끝에:
await send_slack_notification(...)  # 프로젝트 채널 + 작성자 DM
```

**AI Worker (ai/worker.py):**
```python
# code_review 완료 후:
await send_slack_notification(
    channel_type="project",
    blocks=format_ai_review_notification(review),
    ...
)

# briefing 완료 후:
await send_slack_notification(
    channel_type="org",
    blocks=format_briefing_notification(briefing),
    ...
)
```

### 마감 리마인더 스케줄

기존 APScheduler에 추가:

```python
# 매시간 체크
scheduler.add_job(check_deadline_reminders, CronTrigger(minute=0))

async def check_deadline_reminders():
    """마감 임박/초과 태스크 확인 → Slack DM/채널 알림"""
    async with async_session() as db:
        tomorrow = date.today() + timedelta(days=1)

        # D-1 태스크
        tasks_d1 = await db.execute(
            select(Task).where(
                Task.due_date == tomorrow,
                Task.status != TaskStatus.done,
                Task.assignee_id.isnot(None),
            )
        )
        for task in tasks_d1.scalars():
            await send_slack_notification(
                channel_type="dm",
                user_id=task.assignee_id,
                text=f"⏰ '{task.title}' 내일 마감입니다",
                ...
            )

        # 마감 초과 태스크
        overdue_tasks = await db.execute(
            select(Task).where(
                Task.due_date < date.today(),
                Task.status != TaskStatus.done,
                Task.assignee_id.isnot(None),
            )
        )
        for task in overdue_tasks.scalars():
            days = (date.today() - task.due_date).days
            await send_slack_notification(
                channel_type="dm",
                user_id=task.assignee_id,
                text=f"🚨 '{task.title}' 마감 {days}일 초과",
                ...
            )
            # 프로젝트 채널에도 알림
            await send_slack_notification(
                channel_type="project",
                project_id=task.project_id,
                text=f"🚨 '{task.title}' 마감 {days}일 초과",
                ...
            )
```

중복 알림 방지: 이미 알림을 보낸 태스크는 ActivityLog에 기록하고, 같은 날 같은 태스크에 대해 재발송하지 않음.

---

## Slack OAuth Flow

### 연결 흐름

```
1. 대시보드 설정 → "Slack 연결" 클릭
2. GET /api/orgs/{org_id}/slack/auth → Slack OAuth URL로 리다이렉트
   (scope: chat:write, app_mentions:read, users:read, channels:read)
3. 사용자가 Slack에서 워크스페이스 선택 + 권한 승인
4. Slack → GET /api/slack/oauth/callback?code=...
5. code → access_token 교환
6. SlackWorkspace 레코드 생성 (bot_token, team_id 저장)
7. 대시보드로 리다이렉트 (성공/실패 표시)
```

### Slack Event URL 등록

Slack App 설정에서:
- Event Subscriptions URL: `https://{domain}/api/slack/events`
- Subscribe to bot events: `app_mention`
- Signing Secret: 환경변수로 관리

---

## API Endpoints (추가)

### Slack Events

```
POST /api/slack/events              — Slack Event API 수신 (서명 검증 + 이벤트 처리)
POST /api/slack/interactions        — Slack 인터랙션 수신 (버튼 클릭 등)
```

### Slack OAuth

```
GET  /api/orgs/{org_id}/slack/auth          — Slack OAuth 시작 (리다이렉트)
GET  /api/slack/oauth/callback              — OAuth 콜백 (토큰 교환)
```

### Slack 설정

```
GET    /api/orgs/{org_id}/slack/status                  — Slack 연결 상태 (org 멤버)
DELETE /api/orgs/{org_id}/slack/disconnect               — Slack 연결 해제 (org owner)
PATCH  /api/orgs/{org_id}/slack/org-channel             — 조직 공통 채널 설정 (org owner/admin)
POST   /api/projects/{project_id}/slack/channel          — 프로젝트 채널 매핑 (project lead)
DELETE /api/projects/{project_id}/slack/channel           — 채널 매핑 해제 (project lead)
GET    /api/orgs/{org_id}/slack/user-mappings            — 유저 매핑 목록 (org 멤버)
POST   /api/orgs/{org_id}/slack/user-mappings            — 유저 매핑 추가 (org admin)
```

---

## Web Dashboard (추가)

### 조직 설정 — Slack 섹션

기존 설정 페이지에 "Slack 연동" 섹션 추가:

```
Slack 연동 섹션:
├── 연결 상태 (연결됨/미연결)
├── "Slack 연결" 버튼 (미연결 시) / "연결 해제" 버튼 (연결 시)
├── 워크스페이스 이름 표시 (연결 시)
├── 조직 공통 채널 설정 (채널 ID 입력 또는 드롭다운)
└── 유저 매핑 테이블
    ├── PM Agent 유저 ↔ Slack 유저 매핑
    └── 자동 매칭 버튼 (이메일 기반)
```

### 프로젝트 설정 — Slack 채널

프로젝트 설정 또는 프로젝트 상세 페이지에:
- Slack 채널 연결/해제 UI
- 연결된 채널 이름 표시

---

## Project Structure (추가 파일)

```
backend/app/
├── services/
│   ├── slack/
│   │   ├── __init__.py
│   │   ├── bot.py                  # 멘션 처리, 자연어 해석
│   │   ├── notifications.py        # 알림 발송 공통 함수
│   │   ├── formatters.py           # Block Kit 메시지 포맷팅
│   │   └── tools.py                # Claude tool_use 도구 정의 + 실행
│   └── (기존 서비스들)
├── models/
│   ├── slack.py                    # SlackWorkspace, SlackChannelMapping, SlackUserMapping
│   └── (기존 모델들)
├── schemas/
│   ├── slack.py                    # Slack 관련 Pydantic 스키마
│   └── (기존 스키마들)
├── routers/
│   ├── slack.py                    # /api/slack/*, /api/orgs/{id}/slack/*
│   └── (기존 라우터들)
└── scheduler.py                    # MODIFY: 마감 리마인더 추가

frontend/src/
├── components/
│   ├── slack/
│   │   ├── slack-connect.tsx       # Slack 연결/해제 UI
│   │   ├── channel-mapping.tsx     # 채널 매핑 UI
│   │   └── user-mapping.tsx        # 유저 매핑 테이블
│   └── (기존 컴포넌트들)
├── hooks/
│   ├── use-slack.ts                # Slack 관련 hooks
│   └── (기존 hooks)
└── app/(dashboard)/
    └── org/[slug]/
        └── settings/page.tsx       # MODIFY: Slack 섹션 추가
```

---

## main.py Changes

```python
from app.routers import slack
app.include_router(slack.router)
```

기존 라우터/미들웨어 변경 없음.

---

## Error Handling

- Slack API 호출 실패 시 로그만 남기고 서비스 계속 (알림은 best-effort)
- Slack 서명 검증 실패 → 401
- Slack 봇 토큰 만료/무효 → 재연결 필요 안내
- Claude API 의도 파싱 실패 → "죄송합니다, 다음과 같은 작업을 도와드릴 수 있어요:" + 가능한 명령 목록
- 프로젝트 이름 매칭 실패 → "여러 프로젝트가 검색됐습니다:" + 목록
- DM 발송 실패 (유저 매핑 없음) → 프로젝트 채널로 fallback

---

## Testing Strategy

- **Backend**: pytest + httpx (기존 패턴)
  - Slack 서비스: slack API 호출을 mock
  - 봇 서비스: Claude API 호출을 mock, 의도 파싱 로직 테스트
  - 알림: 발송 함수를 mock하고, 트리거 조건 테스트
  - 리마인더: 날짜 조건별 알림 대상 테스트
- **Frontend**: 빌드 검증

---

## Dependencies (추가)

```
slack-bolt>=1.18.0
slack-sdk>=3.27.0
```
