# PM Agent - Phase 4 Design: Google Calendar + Notion Integration

## Overview

Phase 1~3에서 구축한 PM 플랫폼에 Google Calendar과 Notion을 양방향 연동한다. 태스크 마감일이 캘린더 이벤트와 자동 sync되고, 캘린더 회의 30분 전에 프로젝트 브리핑이 Slack DM으로 발송된다. Notion 데이터베이스와 PM Agent 태스크가 양방향 sync되며, AI 분석 시 Notion 문서를 컨텍스트로 활용한다.

### Phase Context

| Phase | 범위 | 상태 |
|-------|------|------|
| 1 | 코어 플랫폼 + GitHub 연동 + 웹 대시보드 | 완료 |
| 2 | AI Agent 엔진 (코드리뷰, 진척도 분석, 테스트 계획) | 완료 |
| 3 | Slack 봇 + 자동화 엔진 (알림, 이벤트 트리거) | 완료 |
| **4 (이번)** | Google Calendar + Notion 연동 | 진행 |

### Phase 4 Scope

**포함:**
- Google Calendar 양방향 sync (태스크 마감일 ↔ 캘린더 이벤트)
- Google Calendar OAuth (유저별, 개인 캘린더)
- Google Push Notification으로 캘린더 변경 감지
- 회의 전 자동 브리핑 (30분 전 → Slack DM)
- Notion 양방향 태스크 sync (어디서든 생성/수정 → 반대쪽 반영)
- Notion OAuth (조직별)
- Notion 5분 폴링 (webhook 미지원)
- 충돌 해결: last-write-wins (last_modified_at 비교)
- Notion 문서 읽기 (AI 분석 컨텍스트)
- 주간 브리핑 Notion 페이지 자동 생성
- 프론트엔드: 설정에 Calendar/Notion 연결 UI

**제외:**
- Google Calendar 외 캘린더 서비스 (Outlook 등)
- Notion 외 문서 도구 (Confluence 등)
- 실시간 Notion sync (webhook이 없어 폴링만 가능)

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  FastAPI (Backend)                     │
│  ┌─────────────────┐  ┌─────────────────┐             │
│  │ Calendar Service │  │ Notion Service  │             │
│  │  ├── OAuth       │  │  ├── OAuth      │             │
│  │  ├── Event Sync  │  │  ├── Task Sync  │             │
│  │  └── Briefing    │  │  ├── Doc Read   │             │
│  │     Trigger      │  │  └── Page Write │             │
│  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                       │
│  ┌────────▼────────────────────▼────────┐             │
│  │          Sync Engine                  │             │
│  │  ├── 충돌 해결 (last-write-wins)      │             │
│  │  ├── Webhook 수신 (Calendar)          │             │
│  │  └── 주기적 폴링 (Notion, 5분)        │             │
│  └──────────────────────────────────────┘             │
└───────────┬──────────────────┬───────────────────────┘
            │                  │
     Google Calendar      Notion API
      API (양방향)         (양방향)
```

### Tech Stack (추가)

| 레이어 | 기술 | 이유 |
|--------|------|------|
| Google API | google-api-python-client + google-auth | 공식 SDK |
| Notion API | notion-client (Python) | 공식 SDK |
| 변경 감지 | Google Push Notification + APScheduler polling | Calendar webhook + Notion 폴링 |

---

## Configuration Changes

기존 `backend/app/config.py`의 `Settings`에 추가:

```python
# Google Calendar
google_client_id: str = ""
google_client_secret: str = ""
google_redirect_uri: str = "http://localhost:8000/api/calendar/oauth/callback"

# Notion
notion_client_id: str = ""
notion_client_secret: str = ""
notion_redirect_uri: str = "http://localhost:8000/api/notion/oauth/callback"
```

`.env.example`에 추가:
```env
# Google Calendar (Phase 4)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/calendar/oauth/callback

# Notion (Phase 4)
NOTION_CLIENT_ID=
NOTION_CLIENT_SECRET=
NOTION_REDIRECT_URI=http://localhost:8000/api/notion/oauth/callback
```

---

## Data Model (추가 테이블)

### GoogleCalendarConnection

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| user_id | UUID | FK → User (unique — 유저별 연결) |
| google_email | VARCHAR | Google 계정 이메일 |
| access_token | VARCHAR | OAuth access token |
| refresh_token | VARCHAR | OAuth refresh token |
| token_expires_at | TIMESTAMP | 토큰 만료 시각 |
| calendar_id | VARCHAR | 캘린더 ID (default "primary") |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

### CalendarEventMapping

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| task_id | UUID | FK → Task (unique) |
| google_event_id | VARCHAR | Google Calendar 이벤트 ID |
| last_synced_at | TIMESTAMP | 마지막 sync 시각 |
| created_at | TIMESTAMP | 생성일 |

### NotionConnection

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| org_id | UUID | FK → Organization (unique) |
| notion_access_token | VARCHAR | Notion OAuth access token |
| notion_workspace_id | VARCHAR | Notion 워크스페이스 ID |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

### NotionDatabaseMapping

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project (unique) |
| notion_database_id | VARCHAR | Notion 데이터베이스 ID |
| last_synced_at | TIMESTAMP | 마지막 sync 시각 |
| created_at | TIMESTAMP | 생성일 |

### NotionTaskMapping

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| task_id | UUID | FK → Task (nullable, unique) |
| notion_page_id | VARCHAR | Notion 페이지 ID (unique) |
| last_modified_at | TIMESTAMP | 마지막 변경 시각 (충돌 해결용) |
| created_at | TIMESTAMP | 생성일 |

---

## Google Calendar Service

### OAuth 흐름

```
1. 대시보드 설정 → "Google Calendar 연결" 클릭
2. GET /api/calendar/auth → Google OAuth URL로 리다이렉트
   (scope: calendar.events)
3. Google 인증 + 동의
4. GET /api/calendar/oauth/callback → 토큰 교환
5. GoogleCalendarConnection 저장 (access_token, refresh_token)
6. 대시보드로 리다이렉트
```

유저별 연결 (조직이 아닌 개인 캘린더).

### 양방향 Sync

**PM Agent → Calendar:**

태스크에 마감일이 설정/변경될 때:
```python
async def sync_task_to_calendar(db, task):
    # 1. 태스크 담당자의 CalendarConnection 조회
    # 2. CalendarEventMapping 확인
    # 3. 매핑 없으면 → 이벤트 생성 (events.insert)
    #    - summary: 태스크 제목
    #    - date: 마감일 (종일 이벤트)
    #    - description: 태스크 설명 + PM Agent 링크
    # 4. 매핑 있으면 → 이벤트 업데이트 (events.update)
    # 5. 태스크 done → 이벤트 삭제 또는 description에 [완료] 추가
    # 6. last_synced_at 업데이트
```

**Calendar → PM Agent:**

Google Push Notification webhook:
```python
# Google Calendar Watch API로 변경 알림 구독
# POST /api/calendar/webhook 으로 변경 알림 수신
# → events.list(syncToken)으로 변경된 이벤트 조회
# → CalendarEventMapping으로 태스크 매핑
# → 마감일 변경됐으면 태스크 업데이트
# → 이벤트 삭제됐으면 태스크 due_date = null
```

Google Push Notification은 일정 기간 후 만료. APScheduler로 주기적 갱신 (매 6시간).

### 회의 전 자동 브리핑

```python
# APScheduler: 매 15분마다 실행
async def check_upcoming_meetings():
    for user in users_with_calendar:
        # 1. 30분 이내 시작하는 회의 조회
        events = await calendar_api.events_list(
            timeMin=now, timeMax=now+30min, singleEvents=True
        )
        for event in events:
            # 2. 회의 제목에서 프로젝트 이름 fuzzy matching
            project = resolve_project_from_event_title(event.summary)
            if not project:
                continue
            # 3. 이미 이 회의에 대해 브리핑 보냈는지 확인 (중복 방지)
            # 4. AI 분석 실행 (Phase 2 project-analyst)
            # 5. Slack DM으로 브리핑 발송
```

---

## Notion Service

### OAuth 흐름

```
1. 대시보드 설정 → "Notion 연결" 클릭
2. GET /api/notion/auth → Notion OAuth URL로 리다이렉트
3. 사용자가 워크스페이스 + 페이지 접근 승인
4. GET /api/notion/oauth/callback → 토큰 교환
5. NotionConnection 저장
6. 대시보드로 리다이렉트
```

조직별 연결 (Notion 워크스페이스 = PM Agent 조직).

### 양방향 태스크 Sync

**PM Agent → Notion:**

태스크 생성/수정 시:
```python
async def sync_task_to_notion(db, task, project_id):
    # 1. NotionDatabaseMapping으로 대상 DB 확인
    # 2. NotionTaskMapping으로 기존 페이지 확인
    # 3. 매핑 없으면 → 페이지 생성 (pages.create)
    # 4. 매핑 있으면 → 페이지 업데이트 (pages.update)
    # 5. last_modified_at 업데이트
```

**Notion → PM Agent:**

주기적 폴링 (5분마다):
```python
async def poll_notion_changes():
    for mapping in notion_db_mappings:
        # 1. databases.query(filter: last_edited_time > last_synced_at)
        # 2. 각 변경된 페이지:
        #    a. NotionTaskMapping 확인
        #    b. 매핑 있으면: last_modified_at 비교 → 최신이면 PM Agent 업데이트
        #    c. 매핑 없으면: 새 태스크 생성 + 매핑
        # 3. last_synced_at 업데이트
```

### Notion ↔ PM Agent 필드 매핑

| Notion Property | PM Agent 필드 | 매핑 방식 |
|----------------|--------------|----------|
| Name (title) | title | 직접 매핑 |
| Status (select) | status | enum 매핑 (설정 가능) |
| Priority (select) | priority | enum 매핑 (설정 가능) |
| Assignee (people) | assignee_id | Notion user → PM Agent user (이메일 기반) |
| Due Date (date) | due_date | 직접 매핑 |
| Description (rich_text) | description | rich text → plain text 변환 |

프로젝트별 Notion DB 연결 시 프로퍼티 이름 매핑을 설정 가능.

### 충돌 해결: last-write-wins

```
양쪽에서 동시 변경 시:
  PM Agent last_modified_at vs Notion last_edited_time
  → 더 최근 변경이 우선
  → 패배한 쪽을 우승한 값으로 덮어씀
  → 충돌 발생 시 ActivityLog에 기록
```

### Notion 문서 활용

- AI 분석 시 프로젝트에 연결된 Notion 페이지를 컨텍스트로 전달
- Agent Executor에서 Notion API로 관련 문서 읽기 → 프롬프트에 포함

### 주간 브리핑 Notion 페이지 생성

- Phase 2 주간 브리핑 완료 후 → Notion에도 페이지 자동 생성
- 프로젝트의 Notion DB 옆에 "Weekly Briefings" 섹션으로

---

## API Endpoints (추가)

### Google Calendar

```
GET    /api/calendar/auth                              — Google OAuth 시작
GET    /api/calendar/oauth/callback                    — OAuth 콜백
GET    /api/users/me/calendar/status                   — 연결 상태 (유저별)
DELETE /api/users/me/calendar/disconnect                — 연결 해제
POST   /api/calendar/webhook                           — Google Push Notification 수신
```

### Notion

```
GET    /api/orgs/{org_id}/notion/auth                  — Notion OAuth 시작
GET    /api/notion/oauth/callback                      — OAuth 콜백
GET    /api/orgs/{org_id}/notion/status                — 연결 상태 (org 멤버)
DELETE /api/orgs/{org_id}/notion/disconnect             — 연결 해제 (org owner)
POST   /api/projects/{project_id}/notion/database      — Notion DB 매핑 설정
DELETE /api/projects/{project_id}/notion/database       — DB 매핑 해제
GET    /api/projects/{project_id}/notion/sync-status    — Sync 상태 확인
POST   /api/projects/{project_id}/notion/sync           — 수동 sync 트리거
```

---

## Scheduler 추가 Jobs

기존 APScheduler에 추가:

```python
# 회의 브리핑: 매 15분
scheduler.add_job(check_upcoming_meetings, CronTrigger(minute="*/15"))

# Notion 폴링: 매 5분
scheduler.add_job(poll_notion_changes, CronTrigger(minute="*/5"))

# Calendar Watch 갱신: 매 6시간
scheduler.add_job(renew_calendar_watches, CronTrigger(hour="*/6"))
```

---

## Sync Hooks (기존 코드 확장)

태스크 CRUD 시 Calendar/Notion sync 트리거:

```python
# task_service.py의 create_task, update_task에 추가:
async def after_task_change(db, task):
    # Calendar sync (마감일 변경 시)
    if task.due_date and task.assignee_id:
        try:
            await sync_task_to_calendar(db, task)
        except Exception:
            pass  # best-effort

    # Notion sync
    try:
        await sync_task_to_notion(db, task, task.project_id)
    except Exception:
        pass  # best-effort
```

---

## Web Dashboard (추가)

### 설정 — Google Calendar 섹션

```
Google Calendar 연동:
├── 연결 상태 (연결됨 + 이메일 / 미연결)
├── "Google Calendar 연결" 버튼 (개인별)
├── 연결된 캘린더 표시
└── "연결 해제" 버튼
```

### 설정 — Notion 섹션

```
Notion 연동:
├── 연결 상태 (연결됨 + 워크스페이스명 / 미연결)
├── "Notion 연결" 버튼 (조직별)
└── "연결 해제" 버튼
```

### 프로젝트 설정 — Notion DB 매핑

```
프로젝트별:
├── Notion Database ID 입력 + "연결" 버튼
├── 연결 시: 마지막 sync 시각 표시
├── "수동 Sync" 버튼
└── 필드 매핑 설정 (Notion property → PM Agent field)
```

---

## Project Structure (추가 파일)

```
backend/app/
├── services/
│   ├── calendar/
│   │   ├── __init__.py
│   │   ├── auth.py                 # Google OAuth 토큰 관리
│   │   ├── sync.py                 # 양방향 event sync
│   │   └── briefing.py             # 회의 전 브리핑 체크
│   ├── notion/
│   │   ├── __init__.py
│   │   ├── auth.py                 # Notion OAuth
│   │   ├── sync.py                 # 양방향 task sync
│   │   └── documents.py            # 문서 읽기/쓰기
│   └── (기존 서비스들)
├── models/
│   ├── calendar.py                 # GoogleCalendarConnection, CalendarEventMapping
│   ├── notion.py                   # NotionConnection, NotionDatabaseMapping, NotionTaskMapping
│   └── (기존 모델들)
├── schemas/
│   ├── calendar.py                 # Calendar 관련 Pydantic 스키마
│   ├── notion.py                   # Notion 관련 Pydantic 스키마
│   └── (기존 스키마들)
├── routers/
│   ├── calendar.py                 # /api/calendar/*
│   ├── notion.py                   # /api/notion/*, /api/orgs/{id}/notion/*
│   └── (기존 라우터들)
└── scheduler.py                    # MODIFY: 회의 브리핑 + Notion 폴링 + Watch 갱신

frontend/src/
├── components/
│   ├── calendar/
│   │   └── calendar-connect.tsx    # Google Calendar 연결 UI
│   ├── notion/
│   │   ├── notion-connect.tsx      # Notion 연결 UI
│   │   └── database-mapping.tsx    # DB 매핑 UI
│   └── (기존 컴포넌트들)
├── hooks/
│   ├── use-calendar.ts             # Calendar hooks
│   ├── use-notion.ts               # Notion hooks
│   └── (기존 hooks)
└── app/(dashboard)/
    └── org/[slug]/
        └── settings/page.tsx       # MODIFY: Calendar + Notion 섹션 추가
```

---

## main.py Changes

```python
from app.routers import calendar, notion
app.include_router(calendar.router)
app.include_router(notion.router)
```

---

## Error Handling

- Google/Notion API 호출 실패 시 best-effort (서비스 중단 없음)
- OAuth 토큰 만료 시 refresh_token으로 자동 갱신
- refresh_token도 만료 시 → 대시보드에서 재연결 필요 표시
- Notion 폴링 실패 시 다음 주기에 재시도 (last_synced_at 유지)
- Calendar webhook 만료 시 자동 재등록 (6시간마다)
- Sync 충돌 시 ActivityLog에 기록 + 대시보드에서 확인 가능

---

## Testing Strategy

- **Backend**: pytest + httpx (기존 패턴)
  - Calendar/Notion API 호출을 mock
  - Sync 로직: 생성/업데이트/삭제/충돌 시나리오 테스트
  - 폴링: 변경 감지 → 태스크 업데이트 로직 테스트
  - 회의 브리핑: 시간 조건 + 프로젝트 매칭 테스트
- **Frontend**: 빌드 검증

---

## Dependencies (추가)

```
google-api-python-client>=2.100.0
google-auth>=2.25.0
google-auth-oauthlib>=1.2.0
notion-client>=2.2.0
```
